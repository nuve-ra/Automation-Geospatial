from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from config.database import Base

class GeospatialData(Base):
    __tablename__ = "geospatial_data"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    data_type = Column(String)
    geometry = Column(Geometry('GEOMETRY', srid=4326))  # PostGIS geometry column
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
