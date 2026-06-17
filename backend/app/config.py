import os

class Config:
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
    KAFKA_TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "scraped_data_raw")
    KAFKA_TOPIC_PROCESSED = os.getenv("KAFKA_TOPIC_PROCESSED", "scraped_data_processed")
    
    # Spark
    SPARK_MASTER = os.getenv("SPARK_MASTER", "spark://spark-master:7077")
    SPARK_CHECKPOINT_DIR = os.getenv("SPARK_CHECKPOINT_DIR", "/tmp/spark-checkpoints")
    
    # Scraper
    SCRAPER_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    SCRAPER_DEPTH_LIMIT = int(os.getenv("SCRAPER_DEPTH_LIMIT", "5"))
    SCRAPER_DOWNLOAD_DELAY = float(os.getenv("SCRAPER_DOWNLOAD_DELAY", "0.5"))
