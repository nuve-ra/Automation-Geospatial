from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from geoalchemy2.exceptions import ArgumentError
from shapely.errors import ShapelyError
from database import engine, Base
from routers import districts, geospatial
from utils.logger import LoggerMiddleware, api_logger
from utils.error_handlers import (
    database_exception_handler,
    spatial_exception_handler,
    api_exception_handler,
    APIException
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Karnataka Geospatial API",
    description="API for managing Karnataka district geospatial data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggerMiddleware)

# Register error handlers
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(ArgumentError, spatial_exception_handler)
app.add_exception_handler(ShapelyError, spatial_exception_handler)
app.add_exception_handler(APIException, api_exception_handler)

# Include routers
app.include_router(districts.router, prefix="/api/v1")
app.include_router(geospatial.router, prefix="/api/v1")

@app.get("/")
async def read_root():
    api_logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to Karnataka Geospatial API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    api_logger.info(f"Request path: {request.url.path}")
    response = await call_next(request)
    return response
