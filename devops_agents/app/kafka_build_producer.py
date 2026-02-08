import os
from kafka import KafkaProducer
import json

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_BUILD_EVENTS_TOPIC = os.getenv("KAFKA_BUILD_EVENTS_TOPIC", "project-build-events")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_build_event(project_id: str, build_id: str, status: str, details: str = ""):
    """
    Sends a build status event to the 'project-build-events' topic.
    Status should be 'in_progress', 'success', or 'failed'.
    """
    event = {
        "project_id": project_id,
        "build_id": build_id,
        "status": status,
        "details": details
    }
    producer.send(KAFKA_BUILD_EVENTS_TOPIC, value=event)
    producer.flush()
