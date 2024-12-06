import time
from datetime import datetime
import logging
from typing import Dict, Any
import json
import os

class ProgressMonitor:
    def __init__(self):
        self.start_time = None
        self.total_features = 0
        self.processed_features = 0
        self.successful_features = 0
        self.failed_features = 0
        self.current_status = "Not Started"
        self.logger = logging.getLogger(__name__)
        
        # Create status directory if it doesn't exist
        self.status_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'status')
        os.makedirs(self.status_dir, exist_ok=True)
        
    def start_process(self, total_features: int):
        """Start monitoring process"""
        self.start_time = time.time()
        self.total_features = total_features
        self.current_status = "In Progress"
        self._save_status()
        self.logger.info(f"Starting process with {total_features} features to process")
        
    def update_progress(self, success: bool = True):
        """Update progress counters"""
        self.processed_features += 1
        if success:
            self.successful_features += 1
        else:
            self.failed_features += 1
        
        self._save_status()
        self._log_progress()
        
    def complete_process(self):
        """Mark process as complete and log summary"""
        self.current_status = "Completed"
        duration = time.time() - self.start_time
        
        summary = {
            "total_features": self.total_features,
            "successful_features": self.successful_features,
            "failed_features": self.failed_features,
            "duration_seconds": duration,
            "success_rate": (self.successful_features / self.total_features * 100) if self.total_features > 0 else 0
        }
        
        self._save_status()
        self.logger.info("Process completed!")
        self.logger.info(f"Summary: {json.dumps(summary, indent=2)}")
        
    def _log_progress(self):
        """Log current progress"""
        progress = (self.processed_features / self.total_features * 100) if self.total_features > 0 else 0
        self.logger.info(f"Progress: {progress:.2f}% ({self.processed_features}/{self.total_features})")
        
    def _save_status(self):
        """Save current status to file"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "status": self.current_status,
            "total_features": self.total_features,
            "processed_features": self.processed_features,
            "successful_features": self.successful_features,
            "failed_features": self.failed_features,
            "progress_percentage": (self.processed_features / self.total_features * 100) if self.total_features > 0 else 0
        }
        
        status_file = os.path.join(self.status_dir, 'current_status.json')
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
            
    @staticmethod
    def get_current_status() -> Dict[str, Any]:
        """Read current status from file"""
        status_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'status', 'current_status.json')
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                return json.load(f)
        return {"status": "No status available"}
