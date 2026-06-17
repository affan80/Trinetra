import json
import time
from kafka import KafkaProducer

def test_producer():
    producer = KafkaProducer(
        bootstrap_servers=['localhost:29092'],
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    test_data = {
        "source_name": "test_source",
        "source_type": "news",
        "url": "http://example.com/test",
        "title": "Test Title from Producer",
        "text": "This is a test message to verify Kafka and Spark connectivity.",
        "author": "Tester",
        "published_at": "2023-10-27T10:00:00",
        "topic_tags": ["test", "kafka"],
        "metadata": {"status": "200"}
    }
    
    print("Sending test message to Kafka...")
    producer.send('scraped_data_raw', value=test_data)
    producer.flush()
    print("Message sent.")

if __name__ == "__main__":
    test_producer()
