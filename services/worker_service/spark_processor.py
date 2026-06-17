import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, MapType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SparkProcessor")

def create_spark_session():
    """Create and return a Scalable Spark session."""
    return SparkSession.builder \
        .appName("OsintSparkProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .config("spark.streaming.stopGracefullyOnShutdown", "true") \
        .config("spark.sql.shuffle.partitions", "10") \
        .getOrCreate()

def main():
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    kafka_topic = os.getenv("KAFKA_TOPIC", "scraped_data")
    checkpoint_dir = os.getenv("SPARK_CHECKPOINT_DIR", "/tmp/spark-checkpoints")

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # Schema definition (unchanged for brevity...)
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

    # Read from Kafka with optimized throughput
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", kafka_topic) \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load()

    # Parse and transform
    parsed_df = df.selectExpr("CAST(value AS STRING)", "timestamp") \
        .select(from_json(col("value"), schema).alias("data"), "timestamp") \
        .select("data.*", "timestamp") \
        .withWatermark("timestamp", "10 minutes")

    # Output to console and potentially a database or another Kafka topic
    query = parsed_df \
        .writeStream \
        .outputMode("append") \
        .option("checkpointLocation", f"{checkpoint_dir}/console_output") \
        .format("console") \
        .trigger(processingTime='10 seconds') \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
