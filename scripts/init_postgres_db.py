import psycopg2
from dotenv import load_dotenv
import os
import sys

def init_database():
    # Load environment variables
    load_dotenv()

    # Database connection parameters
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "karnataka_geodb")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

    # Connect to default PostgreSQL database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database="postgres",
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            # Create database if it doesn't exist
            cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
            if not cur.fetchone():
                print(f"Creating database {DB_NAME}...")
                cur.execute(f"CREATE DATABASE {DB_NAME}")
                print("Database created successfully!")
            else:
                print(f"Database {DB_NAME} already exists.")

        # Close connection to postgres database
        conn.close()

        # Connect to our new database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            # Enable PostGIS
            print("Enabling PostGIS extension...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            
            # Create districts table with PostGIS geometry
            print("Creating districts table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS districts (
                    id SERIAL PRIMARY KEY,
                    district_name VARCHAR(100) NOT NULL,
                    geom geometry(MultiPolygon, 4326),
                    properties JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create spatial index
            print("Creating spatial index...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS districts_geom_idx 
                ON districts 
                USING GIST (geom)
            """)

            print("Database initialization completed successfully!")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
