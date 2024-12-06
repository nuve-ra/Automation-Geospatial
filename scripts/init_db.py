from sqlalchemy import create_engine, text
from config.database import Base, engine
from models.geospatial import GeospatialData
import geopandas as gpd
from shapely.geometry import mapping
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_postgis():
    """Check if PostGIS extension is installed"""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        result = session.execute(text("SELECT PostGIS_Version()"))
        version = result.scalar()
        logger.info(f"PostGIS version: {version}")
        return True
    except Exception as e:
        logger.error(f"PostGIS not available: {str(e)}")
        logger.info("Attempting to create PostGIS extension...")
        try:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            session.commit()
            logger.info("PostGIS extension created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create PostGIS extension: {str(e)}")
            return False
    finally:
        session.close()

def init_database():
    try:
        # First check PostGIS
        if not check_postgis():
            logger.error("PostGIS is required but not available. Please install PostGIS in your database.")
            return

        # Create tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Load Karnataka data
        data_file = Path("data/karnataka_processed.geojson")
        
        if not data_file.exists():
            logger.info("Karnataka data not found. Downloading...")
            from scripts.download_karnataka_data import download_karnataka_data
            gdf = download_karnataka_data()
            if gdf is None:
                logger.error("Failed to download data")
                return
        else:
            logger.info("Loading existing Karnataka data...")
            gdf = gpd.read_file(data_file)
        
        # Create database session
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Clear existing data
            session.query(GeospatialData).delete()
            
            # Add each district as a feature
            for idx, row in gdf.iterrows():
                geom_json = json.loads(row.geometry.json())
                feature = GeospatialData(
                    name=row.get('DISTRICT', f'District_{idx}'),
                    data_type="district",
                    geometry=f"SRID=4326;{row.geometry.wkt}"  # Using WKT format with SRID
                )
                session.add(feature)
                if idx % 10 == 0:  # Log progress every 10 districts
                    logger.info(f"Processed {idx} districts...")
            
            session.commit()
            logger.info(f"Successfully loaded {len(gdf)} districts into the database")
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error loading data: {str(e)}")
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")

if __name__ == "__main__":
    init_database()
