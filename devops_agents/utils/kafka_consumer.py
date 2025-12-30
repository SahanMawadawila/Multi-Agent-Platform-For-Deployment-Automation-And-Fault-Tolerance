import json
from kafka import KafkaConsumer
from dotenv import load_dotenv
import os

KAFKA_TOPIC = 'agent-jobs'
KAFKA_SERVER = 'localhost:9092'

def start_consumer():
    load_dotenv()
    openai_key = os.getenv('OPENAI_KEY')
    if not openai_key:
        raise ValueError("OPENAI_KEY not found in environment variables")

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_SERVER],
        group_id='my-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    print("Kafka Consumer started, waiting for messages...")
    for message in consumer:
        job = message.value
        print(f"Received job: {job}")