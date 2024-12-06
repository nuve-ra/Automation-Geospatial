from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from utils.progress_monitor import ProgressMonitor

router = APIRouter()

# Set up templates directory
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
templates = Jinja2Templates(directory=templates_dir)

@router.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    """Render the monitoring dashboard"""
    return templates.TemplateResponse(
        "monitor.html",
        {"request": request}
    )

@router.get("/monitor/status")
async def get_status():
    """Get current ingestion status"""
    return ProgressMonitor.get_current_status()
