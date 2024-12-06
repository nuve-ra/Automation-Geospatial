from sqlalchemy import Column, Integer, String, JSON, DateTime
from geoalchemy2 import Geometry
from datetime import datetime
from database import Base

class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    geometry = Column(Geometry('MULTIPOLYGON', srid=4326))
    properties = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class Config:
        orm_mode = True
