import requests
import json
import geopandas as gpd
from shapely.geometry import shape
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config.database import SessionLocal, engine
from models.geospatial import GeoFeature, Base
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from pyproj import CRS, Transformer
from config.logging_config import setup_logging
from utils.progress_monitor import ProgressMonitor

# Initialize logging
logger = setup_logging()
progress_monitor = ProgressMonitor()

def download_geojson(url):
    """Download GeoJSON data with progress tracking"""
    try:
        logger.info(f"Downloading GeoJSON from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get total file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        # Download and save the file
        chunks = []
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
        
        data = b''.join(chunks)
        logger.info(f"Successfully downloaded {len(data)} bytes")
        return json.loads(data)
    except Exception as e:
        logger.error(f"Error downloading GeoJSON: {str(e)}")
        return None

def init_db():
    """Initialize database and create tables if they don't exist"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

def transform_coordinates(geojson_geometry, source_crs="EPSG:4326", target_crs="EPSG:4326"):
    """Transform coordinates to target CRS if needed"""
    if source_crs == target_crs:
        return geojson_geometry
    
    try:
        # Create GeoDataFrame from geometry
        gdf = gpd.GeoDataFrame(geometry=[shape(geojson_geometry)], crs=source_crs)
        
        # Reproject to target CRS
        gdf_transformed = gdf.to_crs(target_crs)
        
        # Convert back to GeoJSON
        transformed_geojson = json.loads(gdf_transformed.geometry.iloc[0].to_json())
        return transformed_geojson
    except Exception as e:
        logger.error(f"Error transforming coordinates: {str(e)}")
        return geojson_geometry

def process_feature(feature):
    """Process and validate individual GeoJSON feature"""
    try:
        if not feature.get('geometry'):
            logger.warning("Feature missing geometry")
            return None
            
        # Transform coordinates to EPSG:4326 if needed
        transformed_geometry = transform_coordinates(
            feature['geometry'],
            source_crs="EPSG:4326",
            target_crs="EPSG:4326"
        )
        
        properties = feature.get('properties', {})
        # Add processing timestamp to properties
        properties['processed_at'] = datetime.utcnow().isoformat()
        
        return {
            'feature_type': feature['geometry']['type'],
            'properties': properties,
            'geometry': transformed_geometry
        }
    except Exception as e:
        logger.error(f"Error processing feature: {str(e)}")
        return None

def ingest_feature(db: Session, feature_data: dict):
    """Ingest processed feature into database"""
    try:
        geo_feature = GeoFeature(
            feature_type=feature_data['feature_type'],
            properties=json.dumps(feature_data['properties']),
            geometry=f"SRID=4326;{json.dumps(feature_data['geometry'])}"
        )
        db.add(geo_feature)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error ingesting feature: {str(e)}")
        db.rollback()
        return False

def main():
    # Get GeoJSON URL from environment variable
    geojson_url = os.getenv("GEOJSON_URL")
    if not geojson_url:
        logger.error("GEOJSON_URL environment variable not set")
        return

    # Initialize database
    init_db()
    
    # Download and process GeoJSON data
    data = download_geojson(geojson_url)
    if not data:
        logger.error("Failed to download GeoJSON data")
        return

    # Extract features
    features = data.get('features', [])
    if not features:
        logger.error("No features found in GeoJSON data")
        return

    # Initialize progress monitoring
    progress_monitor.start_process(len(features))
    logger.info(f"Starting to process {len(features)} features")

    db = SessionLocal()
    try:
        for idx, feature in enumerate(features, 1):
            logger.info(f"Processing feature {idx}/{len(features)}")
            
            processed_feature = process_feature(feature)
            if processed_feature:
                success = ingest_feature(db, processed_feature)
                progress_monitor.update_progress(success)
                
                if success:
                    logger.info(f"Successfully ingested feature {idx}")
                else:
                    logger.error(f"Failed to ingest feature {idx}")
            else:
                progress_monitor.update_progress(False)
                logger.error(f"Failed to process feature {idx}")
                    
        progress_monitor.complete_process()
        logger.info("Data ingestion completed")
    except Exception as e:
        logger.error(f"Error during ingestion process: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
