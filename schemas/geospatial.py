from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GeospatialResponse(BaseModel):
    message: str
    feature_count: int

class GeospatialStats(BaseModel):
    total_features: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True
