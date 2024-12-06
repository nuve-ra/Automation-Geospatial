from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import geopandas as gpd
from shapely.geometry import shape
import json
from models.database import get_db
from models.geospatial import GeospatialData
from schemas.geospatial import GeospatialResponse, GeospatialStats
from utils.logger import api_logger

router = APIRouter(
    prefix="/geospatial",
    tags=["Geospatial Operations"]
)

@router.post("/upload", response_model=GeospatialResponse)
async def upload_geospatial_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process geospatial data"""
    try:
        if not file.filename.endswith('.geojson'):
            raise HTTPException(status_code=400, detail="Only GeoJSON files are supported")
        
        content = await file.read()
        geojson_data = json.loads(content)
        
        # Convert to GeoDataFrame for processing
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        
        # Process and store each feature
        processed_features = []
        for _, row in gdf.iterrows():
            geom = shape(row.geometry)
            feature = GeospatialData(
                name=row.get('name', 'Unknown'),
                geometry=f'SRID=4326;{geom.wkt}',
                properties=row.to_dict()
            )
            db.add(feature)
            processed_features.append(feature)
        
        db.commit()
        api_logger.info(f"Successfully processed {len(processed_features)} features")
        
        return GeospatialResponse(
            message="Data uploaded successfully",
            feature_count=len(processed_features)
        )
    
    except Exception as e:
        api_logger.error(f"Error processing geospatial data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=GeospatialStats)
async def get_geospatial_stats(db: Session = Depends(get_db)):
    """Get statistics about the stored geospatial data"""
    try:
        total_features = db.query(GeospatialData).count()
        return GeospatialStats(
            total_features=total_features,
            last_updated=db.query(GeospatialData).order_by(
                GeospatialData.created_at.desc()
            ).first().created_at if total_features > 0 else None
        )
    except Exception as e:
        api_logger.error(f"Error fetching geospatial stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
