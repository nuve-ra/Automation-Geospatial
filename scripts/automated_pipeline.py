import logging
import os
from datetime import datetime
from pathlib import Path
import geopandas as gpd
import json
from shapely.geometry import shape
import sys
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class GeospatialPipeline:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.raw_file = self.data_dir / "karnataka_raw.geojson"
        self.processed_file = self.data_dir / "karnataka_processed.geojson"
        self.error_count = 0
        self.logger = logging.getLogger(__name__)

    def validate_geojson(self, data):
        """Validate GeoJSON data structure and geometry"""
        try:
            if not isinstance(data, dict):
                raise ValueError("Data is not a valid GeoJSON object")
            
            if "type" not in data or data["type"] != "FeatureCollection":
                raise ValueError("Data is not a FeatureCollection")
            
            if "features" not in data or not isinstance(data["features"], list):
                raise ValueError("No features array found")
            
            for feature in data["features"]:
                if "geometry" not in feature:
                    raise ValueError("Feature missing geometry")
                if "properties" not in feature:
                    raise ValueError("Feature missing properties")
                
                # Validate geometry
                geom = shape(feature["geometry"])
                if not geom.is_valid:
                    raise ValueError(f"Invalid geometry found: {geom.wkt}")
                
            return True
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False

    def process_data(self):
        """Process and validate the Karnataka GeoJSON data"""
        try:
            self.logger.info("Starting data processing pipeline")
            
            # Check if source file exists
            if not Path("karnataka.geojson").exists():
                raise FileNotFoundError("Source Karnataka GeoJSON file not found")

            # Read and validate source data
            self.logger.info("Reading source data")
            with open("karnataka.geojson", 'r', encoding='utf-8') as f:
                source_data = json.load(f)

            if not self.validate_geojson(source_data):
                raise ValueError("Source data validation failed")

            # Process with GeoPandas
            self.logger.info("Processing with GeoPandas")
            gdf = gpd.read_file("karnataka.geojson")
            
            # Ensure CRS is WGS84
            gdf = gdf.to_crs("EPSG:4326")
            
            # Save processed data
            self.logger.info("Saving processed data")
            gdf.to_file(self.processed_file, driver="GeoJSON")
            
            self.logger.info("Data processing completed successfully")
            return True

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error in data processing: {str(e)}")
            self.send_error_notification(str(e))
            return False

    def send_error_notification(self, error_message):
        """Send email notification for pipeline errors"""
        try:
            # Load email configuration from environment variables
            load_dotenv()
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            sender_email = os.getenv("SENDER_EMAIL")
            sender_password = os.getenv("SENDER_PASSWORD")
            recipient_email = os.getenv("RECIPIENT_EMAIL")

            if not all([smtp_server, smtp_port, sender_email, sender_password, recipient_email]):
                self.logger.error("Email configuration missing")
                return

            msg = EmailMessage()
            msg.set_content(f"""
            Pipeline Error Notification
            
            Time: {datetime.now()}
            Error: {error_message}
            
            Please check the pipeline logs for more details.
            """)

            msg['Subject'] = 'Karnataka Geospatial Pipeline Error'
            msg['From'] = sender_email
            msg['To'] = recipient_email

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            self.logger.info("Error notification sent successfully")

        except Exception as e:
            self.logger.error(f"Failed to send error notification: {str(e)}")

def run_pipeline():
    pipeline = GeospatialPipeline()
    if pipeline.process_data():
        logging.info("Pipeline executed successfully")
        return 0
    else:
        logging.error("Pipeline execution failed")
        return 1

if __name__ == "__main__":
    sys.exit(run_pipeline())
