import time
import random
from utils.progress_monitor import ProgressMonitor
import logging
from config.logging_config import setup_logging

# Initialize logging
logger = setup_logging()

def simulate_feature_processing():
    """Simulate processing a feature with random success/failure"""
    # Simulate some processing time (0.5 to 2 seconds)
    time.sleep(random.uniform(0.5, 2))
    # 80% success rate
    return random.random() < 0.8

def run_test_ingestion():
    """Run a test ingestion process"""
    # Initialize progress monitor
    monitor = ProgressMonitor()
    
    # Simulate processing 50 features
    total_features = 50
    monitor.start_process(total_features)
    
    logger.info(f"Starting test ingestion of {total_features} features")
    
    for i in range(total_features):
        # Simulate processing a feature
        success = simulate_feature_processing()
        monitor.update_progress(success)
        
        if success:
            logger.info(f"Successfully processed feature {i+1}/{total_features}")
        else:
            logger.error(f"Failed to process feature {i+1}/{total_features}")
    
    monitor.complete_process()
    logger.info("Test ingestion completed")

if __name__ == "__main__":
    run_test_ingestion()
