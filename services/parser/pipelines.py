import json
import logging
from services.shared.redis_queue import RedisQueue
from services.shared.redis_metrics import RedisMetrics

logger = logging.getLogger(__name__)

class OsintPipeline:
    """
    Generic OSINT pipeline that handles News, Blog, and Image items.
    Saves to local files and pushes to Redis queue.
    """

    def open_spider(self, spider):
        """
        Initializes storage and Redis connections when the spider starts.
        """
        # Create a spider-specific output file to avoid collisions
        self.filename = f"{spider.name}_data.jsonl"
        self.file = open(self.filename, "a", encoding="utf-8")
        
        # Initialize Redis components
        try:
            self.queue = RedisQueue("raw_items")
            self.metrics = RedisMetrics()
            self.redis_available = True
        except Exception as e:
            logger.error(f"Failed to connect to Redis in pipeline: {e}")
            self.redis_available = False

    def process_item(self, item, spider):
        """
        Processes each scraped item: saves to file and pushes to Redis.
        """
        article = dict(item)

        # 1. Validation Logic
        if not self.is_valid_item(article):
            return item

        # 2. Local File Storage
        try:
            line = json.dumps(article, ensure_ascii=False)
            self.file.write(line + "\n")
        except Exception as e:
            logger.error(f"Failed to write item to file {self.filename}: {e}")

        # 3. Redis Integration (with error handling)
        if self.redis_available:
            try:
                self.queue.push(article)
                
                # Update metrics
                source = article.get("source_name") or article.get("domain", "unknown")
                self.metrics.increment("scraped_items")
                self.metrics.increment_source(source)
            except Exception as e:
                logger.error(f"Redis operation failed in pipeline: {e}")
                # Don't disable redis_available here, just log the error for this item

        return item

    def is_valid_item(self, item):
        """
        Custom validation logic for different item types.
        """
        # For News and Blogs: must have at least a title or text
        if item.get("source_type") in ["news", "blog"]:
            if not item.get("title") and not item.get("text"):
                return False
        
        # For Images: must have a URL
        if item.get("source_type") == "image":
            if not item.get("image_url"):
                return False
                
        return True

    def close_spider(self, spider):
        """
        Cleans up resources when the spider finishes.
        """
        if hasattr(self, "file"):
            self.file.close()
