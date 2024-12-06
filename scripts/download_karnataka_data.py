import geopandas as gpd
import os
from pathlib import Path
import shutil

def process_karnataka_data():
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Source file in main directory
    source_file = Path("karnataka.geojson")
    raw_file_path = data_dir / "karnataka_raw.geojson"
    
    if not source_file.exists():
        print(f"Error: Karnataka GeoJSON file not found at {source_file}")
        return None

    try:
        # Copy file to data directory
        shutil.copy2(source_file, raw_file_path)
        print(f"Copied Karnataka data to {raw_file_path}")

        print("Loading and processing the data...")
        # Load and process the data
        gdf = gpd.read_file(raw_file_path)
        
        # Basic data cleaning
        gdf = gdf.to_crs("EPSG:4326")  # Ensure WGS84 coordinate system
        
        # Save processed data
        processed_file_path = data_dir / "karnataka_processed.geojson"
        gdf.to_file(processed_file_path, driver="GeoJSON")
        
        print(f"Successfully processed data")
        print(f"Processed data saved to: {processed_file_path}")
        
        return gdf
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return None

if __name__ == "__main__":
    process_karnataka_data()
