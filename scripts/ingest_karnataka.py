import requests
import json
from sqlalchemy import create_engine
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.geospatial import GeoFeature
from config.database import SessionLocal

# Load environment variables
load_dotenv()

# Database connection string
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/geospatial_db')

def download_geojson(url):
    """Download GeoJSON data from the specified URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error downloading GeoJSON: {e}")
        return None

def process_and_store_data(data):
    """Process GeoJSON data and store it in PostgreSQL"""
    try:
        db = SessionLocal()
        
        # Clear existing Karnataka features
        db.query(GeoFeature).filter(GeoFeature.feature_type == 'karnataka_tile').delete()
        
        # Process and store each feature
        for feature in data['features']:
            db_feature = GeoFeature(
                feature_type='karnataka_tile',
                properties=feature['properties'],
                geometry=feature['geometry']
            )
            db.add(db_feature)
        
        db.commit()
        print("Data successfully stored in PostgreSQL")
        return True
    except Exception as e:
        print(f"Error processing and storing data: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    # URL for Karnataka GeoJSON data
    url = "https://file.notion.so/f/f/9301458a-f465-42d3-80eb-7c09bae15034/282d7ed4-5168-4e77-91be-59906c19f9f3/Map_(10).geojson?table=block&id=655f6883-c12c-4503-bd82-157ea8ee1571&spaceId=9301458a-f465-42d3-80eb-7c09bae15034&expirationTimestamp=1733421600000&signature=4qTCnXi1MTKFdJmOqu_mccFQt0orO7BAk0HVczS4kao&downloadName=karnataka.geojson"
    
    # Download data
    print("Downloading GeoJSON data...")
    data = download_geojson(url)
    
    if data:
        print("Processing and storing data...")
        success = process_and_store_data(data)
        if success:
            print("Data pipeline completed successfully")
        else:
            print("Failed to process and store data")
    else:
        print("Failed to download data")

if __name__ == "__main__":
    main()
