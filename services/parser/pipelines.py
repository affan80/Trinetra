import json
import logging
import os
<<<<<<< HEAD
from datetime import datetime, timezone
=======
from kafka import KafkaProducer
>>>>>>> a6911bd (create kafka piplines and add apche spark)
from services.shared.redis_queue import RedisQueue
from services.shared.redis_metrics import RedisMetrics
from services.shared.redis_client import ping_redis
from services.shared.redis_dedupe import RedisDedupe

logger = logging.getLogger(__name__)

class KafkaPipeline:
    """
    Optimized Kafka Pipeline with connection pooling and async flushing.
    """
    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
        self.topic = os.getenv("KAFKA_TOPIC", "scraped_data")
        self.producer = None

    def open_spider(self, spider):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                acks='all',
                retries=5,
                linger_ms=10,
                compression_type='gzip'
            )
            logger.info(f"Scalable Kafka Producer initialized for {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Kafka Initialization Failed: {e}")

    def process_item(self, item, spider):
        if self.producer:
            try:
                # Use callbacks for non-blocking confirmation
                self.producer.send(self.topic, value=dict(item)).add_errback(self._on_error)
            except Exception as e:
                logger.error(f"Kafka Produce Error: {e}")
        return item

    def _on_error(self, exc):
        logger.error(f"Async Kafka Error: {exc}")

    def close_spider(self, spider):
        if self.producer:
            self.producer.flush(timeout=10)
            self.producer.close()

class OsintPipeline:
    """
    Generic OSINT pipeline that handles News, Blog, and Image items.
    Saves to local files and pushes to Redis queue.
    """

    def open_spider(self, spider=None):
        """
        Initializes storage and Redis connections when the spider starts.
        """
        spider_name = getattr(spider, "name", "spider")
        self.file = None
        self.write_local_file = os.getenv("OSINT_PIPELINE_LOCAL_FILE", "0") == "1"

        if self.write_local_file:
            output_dir = os.getenv("OSINT_PIPELINE_OUTPUT_DIR", ".")
            os.makedirs(output_dir, exist_ok=True)
            self.filename = os.path.join(output_dir, f"{spider_name}_data.jsonl")
            self.file = open(self.filename, "a", encoding="utf-8")
        
        # Initialize Redis components
        try:
            if not ping_redis():
                raise ConnectionError("Redis ping failed")

            self.queue = RedisQueue("raw_items")
            self.metrics = RedisMetrics()
            self.dedupe = RedisDedupe()
            self.redis_available = True
        except Exception as e:
            logger.warning(f"Redis unavailable in pipeline; continuing without Redis: {e}")
            self.redis_available = False

    def process_item(self, item, spider=None):
        """
        Processes each scraped item: saves to file and pushes to Redis.
        """
        article = dict(item)

        # 1. Validation Logic
        if not self.is_valid_item(article):
            self.track_metric("invalid_items")
            return item

        self.add_audit_metadata(article)

        # 2. Local File Storage
        if self.file:
            try:
                line = json.dumps(article, ensure_ascii=False)
                self.file.write(line + "\n")
            except Exception as e:
                logger.error(f"Failed to write item to file {self.filename}: {e}")

        # 3. Redis Integration (with error handling)
        if self.redis_available:
            try:
                dedupe_url = self.get_dedupe_url(article)
                source = article.get("source_name") or article.get("domain", "unknown")

                if dedupe_url and not self.dedupe.is_new_url(dedupe_url, source=source):
                    self.metrics.increment("duplicate_items")
                    return item

                self.queue.push(article)
                
                # Update metrics
                self.metrics.increment("scraped_items")
                self.metrics.increment_source(source)
                self.track_provenance_metrics(article)
            except Exception as e:
                logger.error(f"Redis operation failed in pipeline: {e}")
                self.redis_available = False

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
            image_url = item.get("image_url", "")
            if not image_url or not image_url.startswith(("http://", "https://")):
                return False
                
        return True

    def close_spider(self, spider=None):
        """
        Cleans up resources when the spider finishes.
        """
        if self.file:
            self.file.close()

    def add_audit_metadata(self, article):
        metadata = article.setdefault("metadata", {})
        metadata.setdefault("collected_at", datetime.now(timezone.utc).isoformat())
        metadata.setdefault("validation_status", "valid")

        source_url = article.get("url") or article.get("page_url") or article.get("image_url", "")
        metadata.setdefault("source_url", source_url)
        metadata.setdefault("canonical_url", metadata.get("canonical_url") or source_url)

    def get_dedupe_url(self, article):
        metadata = article.get("metadata", {})
        return (
            metadata.get("canonical_url")
            or article.get("url")
            or article.get("page_url")
            or article.get("image_url")
            or ""
        )

    def track_metric(self, name, amount=1):
        if self.redis_available and hasattr(self, "metrics"):
            try:
                self.metrics.increment(name, amount)
            except Exception:
                pass

    def track_provenance_metrics(self, article):
        metadata = article.get("metadata", {})

        if metadata.get("fallback_used"):
            self.metrics.increment("scrapling_fallback_used")

        fallback_reason = metadata.get("fallback_reason", "")
        if fallback_reason:
            self.metrics.increment("scrapling_fallback_attempted")

        if "blocked_status" in fallback_reason:
            self.metrics.increment("blocked_pages")
