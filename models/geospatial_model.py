from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry

Base = declarative_base()

class GeoFeature(Base):
    __tablename__ = 'geo_features'

    id = Column(Integer, primary_key=True)
    feature_id = Column(String, unique=True)
    geometry = Column(Geometry('GEOMETRY', srid=4326))
    properties = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
