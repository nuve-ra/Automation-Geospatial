import schedule
import time
from ingest_data import main as ingest_main
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def job():
    logger.info("Starting scheduled data ingestion...")
    ingest_main()
    logger.info("Completed scheduled data ingestion")

def main():
    # Schedule job to run daily at midnight
    schedule.every().day.at("00:00").do(job)
    
    logger.info("Scheduler started. Will run data ingestion daily at midnight.")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
