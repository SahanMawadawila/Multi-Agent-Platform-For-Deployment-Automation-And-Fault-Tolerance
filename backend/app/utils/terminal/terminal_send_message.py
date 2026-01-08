"""
This is a prototype implementation of terminal message sending utility.
"""
import os
from kafka import KafkaProducer
import json

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TERMINAL_TOPIC = os.getenv("KAFKA_TERMINAL_TOPIC", "project-terminal-events")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_terminal_message(project_id: str, message: str):
    event = {
        "project_id": project_id,
        "message": message
    }
    producer.send(KAFKA_TERMINAL_TOPIC, value=event)
    producer.flush()