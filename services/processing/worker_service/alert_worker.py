import logging
import time

from services.shared.redis_client import ping_redis
from services.shared.redis_metrics import RedisMetrics
from services.shared.redis_queue import RedisQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alert_worker")

def main():
    logger.info("Starting Alert Worker...")
    
    if not ping_redis():
        logger.error("Could not connect to Redis. Exiting.")
        return

    queue = RedisQueue("raw_items")
    metrics = RedisMetrics()

    logger.info("Worker ready. Listening for items...")

    while True:
        try:
            # Simple polling or BRPOP
            item = queue.pop()
            if item:
                logger.info(f"Processing item: {item.get('title', 'No Title')}")
                # Logic for alerts would go here
                metrics.increment("processed_alerts")
                time.sleep(1) # Simulate processing
            else:
                time.sleep(2) # Wait for new items
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
