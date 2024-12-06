from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import Base, SQLALCHEMY_DATABASE_URL
from models.district import District
from models.geospatial import GeospatialData

def init_database():
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # Create database if it doesn't exist
    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Created database")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Created all database tables")

if __name__ == "__main__":
    init_database()
