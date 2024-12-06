from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class DistrictBase(BaseModel):
    name: str
    geometry: Dict[str, Any]  # GeoJSON geometry
    properties: Dict[str, Any]

class DistrictCreate(DistrictBase):
    pass

class DistrictUpdate(BaseModel):
    name: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None

class District(DistrictBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
