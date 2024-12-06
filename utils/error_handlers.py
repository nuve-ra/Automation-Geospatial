from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from geoalchemy2.exceptions import ArgumentError
from shapely.errors import ShapelyError
from typing import Any, Dict
from .logger import log_error, APIException

async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database-related exceptions"""
    error_detail = {
        "type": "database_error",
        "message": str(exc),
        "path": request.url.path
    }
    log_error(exc, {"request_path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_detail}
    )

async def spatial_exception_handler(request: Request, exc: (ArgumentError, ShapelyError)) -> JSONResponse:
    """Handle spatial data processing exceptions"""
    error_detail = {
        "type": "spatial_error",
        "message": str(exc),
        "path": request.url.path
    }
    log_error(exc, {"request_path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": error_detail}
    )

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions"""
    error_detail = {
        "type": "api_error",
        "message": exc.message,
        "path": request.url.path,
        **exc.context
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": error_detail}
    )

def handle_validation_error(exc: Any) -> Dict[str, Any]:
    """Format validation errors"""
    return {
        "type": "validation_error",
        "detail": [
            {
                "loc": err["loc"],
                "msg": err["msg"],
                "type": err["type"]
            }
            for err in exc.errors()
        ]
    }
