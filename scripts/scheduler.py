from apscheduler.schedulers.blocking import BlockingScheduler
from data_ingestion import main as ingest_data
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scheduled_job():
    """Run the data ingestion job"""
    try:
        logger.info("Starting scheduled data ingestion...")
        ingest_data()
        logger.info("Scheduled data ingestion completed successfully")
    except Exception as e:
        logger.error(f"Scheduled data ingestion failed: {str(e)}")

def main():
    """Initialize and start the scheduler"""
    scheduler = BlockingScheduler()
    
    # Schedule the job to run daily at midnight
    scheduler.add_job(scheduled_job, 'cron', hour=0, minute=0)
    
    # Also run it once at startup
    scheduler.add_job(scheduled_job)
    
    logger.info("Starting scheduler...")
    scheduler.start()

if __name__ == "__main__":
    main()
