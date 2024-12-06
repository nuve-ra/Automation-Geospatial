import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from config.logging_config import setup_logging

logger = setup_logging()

def setup_database():
    """Setup PostgreSQL database with PostGIS extension"""
    try:
        # Connect to PostgreSQL server
        logger.info("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Create database if it doesn't exist
        logger.info("Creating database if it doesn't exist...")
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'geospatial_db'")
        if not cur.fetchone():
            cur.execute("CREATE DATABASE geospatial_db")
            logger.info("Database 'geospatial_db' created successfully")
        
        cur.close()
        conn.close()
        
        # Connect to the new database
        logger.info("Connecting to geospatial_db...")
        conn = psycopg2.connect(
            dbname="geospatial_db",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Enable PostGIS
        logger.info("Enabling PostGIS extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        logger.info("PostGIS extension enabled successfully")
        
        # Verify PostGIS installation
        cur.execute("SELECT PostGIS_version()")
        version = cur.fetchone()[0]
        logger.info(f"PostGIS version: {version}")
        
        cur.close()
        conn.close()
        logger.info("Database setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        return False

if __name__ == "__main__":
    setup_database()
