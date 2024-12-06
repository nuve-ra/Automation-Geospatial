from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import json
import geopandas as gpd
from shapely.geometry import shape, mapping
from config.database import SessionLocal, engine, Base
from models.geospatial import GeospatialData
from pathlib import Path

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Read the uploaded file
        content = await file.read()
        
        # Parse the file using geopandas
        if file.filename.endswith('.geojson'):
            gdf = gpd.read_file(content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Store each feature in the database
        for _, row in gdf.iterrows():
            geom_json = json.loads(row.geometry.json())
            feature = GeospatialData(
                name=file.filename,
                data_type="geojson",
                geometry=geom_json
            )
            db.add(feature)
        
        db.commit()
        return {"message": "File uploaded successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data")
def get_data(db: Session = Depends(get_db)):
    features = db.query(GeospatialData).all()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": feature.geometry,
                "properties": {
                    "id": feature.id,
                    "name": feature.name,
                    "created_at": feature.created_at
                }
            }
            for feature in features
        ]
    }

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(GeospatialData).count()
    return {
        "total": total,
        "processing": 0,
        "completed": total,
        "failed": 0
    }

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/api/karnataka-data")
async def get_karnataka_data():
    try:
        # First try to read from processed data
        data_file = Path("data/karnataka_processed.geojson")
        if not data_file.exists():
            # Fall back to original file if processed doesn't exist
            data_file = Path("karnataka.geojson")
        
        if not data_file.exists():
            raise HTTPException(status_code=404, detail="Karnataka GeoJSON data not found")
        
        with open(data_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        return JSONResponse(content=geojson_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
