import hashlib
import json
from datetime import datetime
from pathlib import Path
import requests
from sqlalchemy.orm import Session
from models.district import District
from database import get_db
from utils.logger import setup_logger

sync_logger = setup_logger('sync', 'sync.log')

class DataSyncManager:
    def __init__(self):
        self.source_url = "https://raw.githubusercontent.com/datameet/maps/master/Districts/Karnataka.geojson"
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "last_sync.json"

    def calculate_hash(self, data: str) -> str:
        """Calculate SHA-256 hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()

    def get_last_sync_info(self) -> dict:
        """Get information about last synchronization"""
        if not self.cache_file.exists():
            return {"last_sync": None, "data_hash": None}
        
        with open(self.cache_file, 'r') as f:
            return json.load(f)

    def save_sync_info(self, data_hash: str):
        """Save synchronization information"""
        sync_info = {
            "last_sync": datetime.utcnow().isoformat(),
            "data_hash": data_hash
        }
        with open(self.cache_file, 'w') as f:
            json.dump(sync_info, f)

    def fetch_source_data(self) -> dict:
        """Fetch data from source"""
        try:
            response = requests.get(self.source_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            sync_logger.error(f"Error fetching source data: {str(e)}")
            raise

    def sync_required(self, source_data: dict) -> bool:
        """Check if sync is required by comparing hashes"""
        current_hash = self.calculate_hash(json.dumps(source_data))
        last_sync = self.get_last_sync_info()
        return last_sync["data_hash"] != current_hash

    def update_database(self, source_data: dict, db: Session):
        """Update database with new data"""
        try:
            # Clear existing data
            db.query(District).delete()
            
            # Insert new data
            for feature in source_data["features"]:
                district = District(
                    name=feature["properties"].get("DISTRICT"),
                    geometry=json.dumps(feature["geometry"]),
                    properties=feature["properties"]
                )
                db.add(district)
            
            db.commit()
            sync_logger.info("Database updated successfully")
            
        except Exception as e:
            db.rollback()
            sync_logger.error(f"Error updating database: {str(e)}")
            raise

    def sync(self):
        """Main synchronization method"""
        try:
            sync_logger.info("Starting data synchronization")
            
            # Fetch current data
            source_data = self.fetch_source_data()
            
            # Check if sync is needed
            if not self.sync_required(source_data):
                sync_logger.info("Data is already up to date")
                return False
            
            # Update database
            db = next(get_db())
            self.update_database(source_data, db)
            
            # Save sync info
            self.save_sync_info(self.calculate_hash(json.dumps(source_data)))
            
            sync_logger.info("Synchronization completed successfully")
            return True
            
        except Exception as e:
            sync_logger.error(f"Synchronization failed: {str(e)}")
            raise

def run_sync():
    """Convenience function to run synchronization"""
    sync_manager = DataSyncManager()
    return sync_manager.sync()
