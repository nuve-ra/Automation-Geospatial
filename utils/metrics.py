import time
import psutil
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging
from functools import wraps
from typing import Dict, Optional
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

# Prometheus metrics
FEATURE_COUNTER = Counter('processed_features_total', 'Total number of features processed')
FAILED_FEATURES = Counter('failed_features_total', 'Total number of features that failed processing')
PROCESSING_TIME = Histogram('feature_processing_seconds', 'Time spent processing features',
                          buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float('inf')))
CHUNK_PROCESSING_TIME = Histogram('chunk_processing_seconds', 'Time spent processing chunks',
                                buckets=(1.0, 5.0, 10.0, 30.0, 60.0, float('inf')))
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Current memory usage')
CPU_USAGE = Gauge('cpu_usage_percent', 'Current CPU usage')
ACTIVE_WORKERS = Gauge('active_workers', 'Number of active worker threads')
DB_OPERATIONS = Counter('db_operations_total', 'Total number of database operations', ['operation'])
DOWNLOAD_SPEED = Gauge('download_speed_bytes', 'Current download speed in bytes per second')
PROCESSING_SPEED = Gauge('processing_speed_features', 'Features processed per second')

class MetricsCollector:
    def __init__(self, metrics_port: int = 8000):
        self.start_time = time.time()
        self.features_processed = 0
        self.features_failed = 0
        self.metrics_port = metrics_port
        self._lock = threading.Lock()
        
        # Start Prometheus metrics server
        try:
            start_http_server(metrics_port)
            logger.info(f"Metrics server started on port {metrics_port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    def collect_system_metrics(self):
        """Collect system metrics"""
        try:
            process = psutil.Process()
            MEMORY_USAGE.set(process.memory_info().rss)
            CPU_USAGE.set(process.cpu_percent())
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def track_feature_processing(self, success: bool = True):
        """Track feature processing metrics"""
        with self._lock:
            if success:
                FEATURE_COUNTER.inc()
                self.features_processed += 1
            else:
                FAILED_FEATURES.inc()
                self.features_failed += 1
            
            # Calculate and update processing speed
            elapsed_time = max(time.time() - self.start_time, 1)  # Avoid division by zero
            PROCESSING_SPEED.set(self.features_processed / elapsed_time)
    
    def track_db_operation(self, operation: str):
        """Track database operations"""
        DB_OPERATIONS.labels(operation=operation).inc()
    
    def update_download_speed(self, bytes_downloaded: int, duration: float):
        """Update download speed metric"""
        if duration > 0:
            DOWNLOAD_SPEED.set(bytes_downloaded / duration)
    
    def update_worker_count(self, count: int):
        """Update active worker count"""
        ACTIVE_WORKERS.set(count)

def with_metrics(name: Optional[str] = None):
    """Decorator to measure execution time of functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metric_name = name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record duration in appropriate histogram
                if 'chunk' in metric_name.lower():
                    CHUNK_PROCESSING_TIME.observe(duration)
                else:
                    PROCESSING_TIME.observe(duration)
                
                return result
            
            except Exception as e:
                logger.error(f"Error in {metric_name}: {str(e)}")
                raise
            
        return wrapper
    return decorator

class PerformanceMonitor:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._stop_event = threading.Event()
        self._monitor_thread = None
    
    def start(self):
        """Start performance monitoring"""
        def monitor():
            while not self._stop_event.is_set():
                try:
                    # Collect system metrics
                    process = psutil.Process()
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    
                    # Update Prometheus metrics
                    CPU_USAGE.set(cpu_percent)
                    MEMORY_USAGE.set(memory_info.rss)
                    
                    # Log performance data
                    logger.info(
                        f"Performance Metrics - CPU: {cpu_percent}%, "
                        f"Memory: {memory_info.rss / 1024 / 1024:.2f}MB, "
                        f"Features Processed: {FEATURE_COUNTER._value.get()}, "
                        f"Failed Features: {FAILED_FEATURES._value.get()}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")
                
                self._stop_event.wait(self.interval)
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        self._monitor_thread = threading.Thread(target=self.start, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join()

# Initialize global metrics collector
metrics_collector = MetricsCollector()
performance_monitor = PerformanceMonitor()
