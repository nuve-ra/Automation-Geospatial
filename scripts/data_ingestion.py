import requests
import geopandas as gpd
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session
from sqlalchemy.orm.session import sessionmaker
from config.database import DATABASE_URL
from models.geospatial_model import GeoFeature, Session
from shapely.geometry import shape
import logging
import os
from datetime import datetime
import uuid
from shapely import wkb, wkt
import backoff
import tempfile
from typing import Dict, List, Optional, Tuple
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import multiprocessing
import queue
from utils.metrics import (
    metrics_collector, 
    performance_monitor, 
    with_metrics, 
    PROCESSING_TIME, 
    CHUNK_PROCESSING_TIME
)
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
BACKUP_DIR = "data_backups"
CHUNK_SIZE = 100
MAX_WORKERS = max(1, multiprocessing.cpu_count() - 1)  # Leave one CPU free
PROGRESS_QUEUE = queue.Queue()

class DataIngestionError(Exception):
    """Custom exception for data ingestion errors"""
    pass

@with_metrics("fetch_geojson")
def fetch_geojson_data(url: str) -> Dict:
    """Fetch GeoJSON data from the provided URL with retry logic"""
    start_time = time.time()
    total_bytes = 0
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create backup directory if it doesn't exist
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        # Save a backup of the raw data with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"geojson_backup_{timestamp}.json")
        
        # Stream the response to a temporary file first
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
            with tqdm(desc="Downloading data", unit='B', unit_scale=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        chunk_size = len(chunk)
                        total_bytes += chunk_size
                        temp_file.write(chunk)
                        pbar.update(chunk_size)
                        
                        # Update download speed metric
                        elapsed = time.time() - start_time
                        metrics_collector.update_download_speed(total_bytes, elapsed)
        
        # Verify the downloaded file
        with open(temp_file.name, 'rb') as f:
            content = f.read()
            checksum = hashlib.md5(content).hexdigest()
            
        # Move to backup location if verification successful
        os.rename(temp_file.name, backup_path)
        logger.info(f"Backup created at {backup_path} with checksum {checksum}")
        
        # Parse and return the JSON data
        with open(backup_path, 'r') as f:
            return json.load(f)
            
    except requests.exceptions.RequestException as e:
        metrics_collector.track_db_operation("download_failed")
        logger.error(f"Failed to fetch data after {MAX_RETRIES} retries: {str(e)}")
        raise DataIngestionError(f"Failed to fetch data: {str(e)}")
    except json.JSONDecodeError as e:
        metrics_collector.track_db_operation("json_decode_failed")
        logger.error(f"Invalid JSON data: {str(e)}")
        raise DataIngestionError(f"Invalid JSON data: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while fetching data: {str(e)}")
        raise DataIngestionError(f"Unexpected error: {str(e)}")

@with_metrics("process_feature")
def process_feature(feature: Dict, session) -> Tuple[bool, str]:
    """Process a single feature with error handling"""
    try:
        # Validate feature structure
        if not all(k in feature for k in ['geometry', 'properties']):
            metrics_collector.track_feature_processing(success=False)
            return False, "Missing required fields"

        # Generate a unique feature ID if not present
        feature_id = feature.get('id', str(uuid.uuid4()))

        # Validate and transform geometry
        geom = shape(feature['geometry'])
        if not geom.is_valid:
            geom = geom.buffer(0)

        # Convert to EPSG:4326 if needed
        if geom.has_z:
            geom = wkt.loads(wkb.dumps(geom, output_dimension=2))
            geom = shape(geom)

        # Check if feature already exists
        existing_feature = session.query(GeoFeature).filter_by(feature_id=feature_id).first()
        if existing_feature:
            # Update existing feature
            metrics_collector.track_db_operation("update")
            existing_feature.geometry = f'SRID=4326;{geom.wkt}'
            existing_feature.properties = json.dumps(feature.get('properties', {}))
            existing_feature.last_updated = datetime.utcnow()
        else:
            # Create new feature
            metrics_collector.track_db_operation("insert")
            db_feature = GeoFeature(
                feature_id=feature_id,
                geometry=f'SRID=4326;{geom.wkt}',
                properties=json.dumps(feature.get('properties', {})),
                last_updated=datetime.utcnow()
            )
            session.add(db_feature)

        metrics_collector.track_feature_processing(success=True)
        return True, feature_id

    except Exception as e:
        metrics_collector.track_feature_processing(success=False)
        return False, str(e)

@with_metrics("process_chunk")
def process_chunk_parallel(chunk: List[Dict], engine) -> int:
    """Process a chunk of features in parallel"""
    successful_features = 0
    session = Session(engine)
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            metrics_collector.update_worker_count(MAX_WORKERS)
            
            # Submit all features for processing
            future_to_feature = {
                executor.submit(process_feature, feature, session): feature 
                for feature in chunk
            }
            
            # Process completed features
            for future in as_completed(future_to_feature):
                success, result = future.result()
                if success:
                    successful_features += 1
                else:
                    logger.warning(f"Failed to process feature: {result}")
        
        # Commit all successful features
        metrics_collector.track_db_operation("commit")
        session.commit()
        PROGRESS_QUEUE.put(len(chunk))
        return successful_features
        
    except Exception as e:
        metrics_collector.track_db_operation("rollback")
        session.rollback()
        logger.error(f"Error processing chunk: {str(e)}")
        return 0
    finally:
        metrics_collector.update_worker_count(0)
        session.close()

def process_and_store_data(geojson_data: Dict) -> None:
    """Process GeoJSON data and store it in PostgreSQL with parallel processing"""
    try:
        engine = create_engine(DATABASE_URL)
        
        # Start performance monitoring
        performance_monitor.start_monitoring()
        
        # Validate GeoJSON structure
        if not isinstance(geojson_data, dict) or 'features' not in geojson_data:
            raise DataIngestionError("Invalid GeoJSON format: missing 'features' array")

        total_features = len(geojson_data['features'])
        successful_features = 0
        
        # Create chunks for parallel processing
        chunks = [
            geojson_data['features'][i:i + CHUNK_SIZE]
            for i in range(0, total_features, CHUNK_SIZE)
        ]
        
        # Process chunks in parallel with progress bar
        with tqdm(total=total_features, desc="Processing features") as pbar:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit all chunks for processing
                future_to_chunk = {
                    executor.submit(process_chunk_parallel, chunk, engine): chunk 
                    for chunk in chunks
                }
                
                # Process completed chunks
                for future in as_completed(future_to_chunk):
                    successful_features += future.result()
                    future.add_done_callback(lambda f: update_progress(f, pbar, PROGRESS_QUEUE))

        # Log final statistics
        logger.info(f"Data ingestion completed: {successful_features}/{total_features} features processed successfully")
        
        if successful_features < total_features:
            logger.warning(f"Some features were not processed: {total_features - successful_features} failures")

    except Exception as e:
        logger.error(f"Error in process_and_store_data: {str(e)}")
        raise DataIngestionError(f"Data processing failed: {str(e)}")
    finally:
        # Stop performance monitoring
        performance_monitor.stop_monitoring()

def update_progress(future, pbar, progress_queue):
    """Callback function to update progress bar"""
    while True:
        try:
            progress = progress_queue.get_nowait()
            pbar.update(progress)
        except queue.Empty:
            break

def main():
    """Main function to run the data ingestion pipeline with parallel processing"""
    try:
        # URL for Karnataka GeoJSON data
        geojson_url = "https://prod-files-secure.s3.us-west-2.amazonaws.com/9301458a-f465-42d3-80eb-7c09bae15034/282d7ed4-5168-4e77-91be-59906c19f9f3/Map_(10).geojson"
        
        logger.info(f"Starting data ingestion from {geojson_url} with {MAX_WORKERS} workers")
        
        # Start metrics collection
        metrics_collector.collect_system_metrics()
        
        # Fetch data with retry logic
        geojson_data = fetch_geojson_data(geojson_url)
        logger.info("Successfully fetched GeoJSON data")
        
        # Process and store data with parallel processing
        process_and_store_data(geojson_data)
        logger.info("Data ingestion completed successfully")
        
    except DataIngestionError as e:
        logger.error(f"Data ingestion failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
