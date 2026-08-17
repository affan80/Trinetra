import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, MapType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SparkProcessor")

SPARK_VERSION = "3.5.3"

def create_spark_session():
    """Create and return a Scalable Spark session."""
    spark_master_url = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")
    return SparkSession.builder \
        .appName("OsintSparkProcessor") \
        .master(spark_master_url) \
        .config(
            "spark.jars.packages",
            f"org.apache.spark:spark-sql-kafka-0-10_2.12:{SPARK_VERSION}",
        ) \
        .config("spark.streaming.stopGracefullyOnShutdown", "true") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()

def main():
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    kafka_topic_raw = os.getenv("KAFKA_TOPIC", "scraped_data_raw")
    kafka_topic_processed = os.getenv("KAFKA_TOPIC_PROCESSED", "scraped_data_processed")
    checkpoint_dir = os.getenv("SPARK_CHECKPOINT_DIR", "/tmp/spark-checkpoints")

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # Schema definition
    schema = StructType([
        StructField("source_name", StringType(), True),
        StructField("source_type", StringType(), True),
        StructField("url", StringType(), True),
        StructField("title", StringType(), True),
        StructField("text", StringType(), True),
        StructField("author", StringType(), True),
        StructField("published_at", StringType(), True),
        StructField("topic_tags", ArrayType(StringType()), True),
        StructField("metadata", MapType(StringType(), StringType()), True)
    ])

    # 1. Read from Kafka (Raw Topic)
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", kafka_topic_raw) \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load()

    # 2. Parse and Transform
    parsed_df = df.selectExpr("CAST(value AS STRING)", "timestamp") \
        .select(from_json(col("value"), schema).alias("data"), "timestamp") \
        .select("data.*", "timestamp") \
        .withWatermark("timestamp", "10 minutes") \
        .dropDuplicates(["url", "timestamp"])

    # 3. Output to Console (for debugging)
    console_query = parsed_df \
        .writeStream \
        .outputMode("append") \
        .option("checkpointLocation", f"{checkpoint_dir}/console_output") \
        .format("console") \
        .trigger(processingTime='10 seconds') \
        .start()

    # 4. Output to Kafka (Processed Topic)
    kafka_query = parsed_df \
        .selectExpr("CAST(url AS STRING) AS key", "to_json(struct(*)) AS value") \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("topic", kafka_topic_processed) \
        .option("checkpointLocation", f"{checkpoint_dir}/kafka_output") \
        .outputMode("append") \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()
