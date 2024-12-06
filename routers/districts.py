from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models.district import District as DistrictModel
from schemas.district import District, DistrictCreate, DistrictUpdate
from shapely.geometry import shape, mapping
from geoalchemy2.shape import from_shape
import json
from utils.sync_manager import run_sync

router = APIRouter()

@router.post("/districts/", response_model=District, tags=["districts"])
def create_district(district: DistrictCreate, db: Session = Depends(get_db)):
    """Create a new district"""
    # Convert GeoJSON geometry to WKB
    geom = shape(district.geometry)
    db_district = DistrictModel(
        name=district.name,
        geometry=from_shape(geom, srid=4326),
        properties=district.properties
    )
    db.add(db_district)
    db.commit()
    db.refresh(db_district)
    return db_district

@router.get("/districts/", response_model=List[District], tags=["districts"])
def read_districts(
    skip: int = Query(0, description="Skip first N items"),
    limit: int = Query(100, description="Limit the number of items returned"),
    db: Session = Depends(get_db)
):
    """Get all districts with pagination"""
    districts = db.query(DistrictModel).offset(skip).limit(limit).all()
    return districts

@router.get("/districts/{district_id}", response_model=District, tags=["districts"])
def read_district(district_id: int, db: Session = Depends(get_db)):
    """Get a specific district by ID"""
    district = db.query(DistrictModel).filter(DistrictModel.id == district_id).first()
    if district is None:
        raise HTTPException(status_code=404, detail="District not found")
    return district

@router.put("/districts/{district_id}", response_model=District, tags=["districts"])
def update_district(
    district_id: int,
    district_update: DistrictUpdate,
    db: Session = Depends(get_db)
):
    """Update a district"""
    db_district = db.query(DistrictModel).filter(DistrictModel.id == district_id).first()
    if db_district is None:
        raise HTTPException(status_code=404, detail="District not found")
    
    # Update fields if provided
    if district_update.name is not None:
        db_district.name = district_update.name
    if district_update.properties is not None:
        db_district.properties = district_update.properties
    
    db.commit()
    db.refresh(db_district)
    return db_district

@router.delete("/districts/{district_id}", tags=["districts"])
def delete_district(district_id: int, db: Session = Depends(get_db)):
    """Delete a district"""
    district = db.query(DistrictModel).filter(DistrictModel.id == district_id).first()
    if district is None:
        raise HTTPException(status_code=404, detail="District not found")
    
    db.delete(district)
    db.commit()
    return {"message": f"District {district_id} deleted successfully"}

# Spatial Queries
@router.get("/districts/within/bbox", response_model=List[District], tags=["spatial"])
def get_districts_within_bbox(
    min_lon: float = Query(..., description="Minimum longitude"),
    min_lat: float = Query(..., description="Minimum latitude"),
    max_lon: float = Query(..., description="Maximum longitude"),
    max_lat: float = Query(..., description="Maximum latitude"),
    db: Session = Depends(get_db)
):
    """Get all districts within a bounding box"""
    bbox = f'POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))'
    districts = db.query(DistrictModel).filter(
        DistrictModel.geometry.ST_Within(f'ST_SetSRID(ST_GeomFromText(\'{bbox}\'), 4326)')
    ).all()
    return districts

@router.post("/sync", tags=["sync"])
def sync_data():
    """Synchronize district data with source"""
    try:
        updated = run_sync()
        if updated:
            return {"message": "Data synchronized successfully"}
        return {"message": "Data is already up to date"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )
