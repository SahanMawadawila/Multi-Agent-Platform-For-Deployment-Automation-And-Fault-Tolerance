import os
from kafka import KafkaProducer
import json

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_BUILD_EVENTS_TOPIC = os.getenv("KAFKA_PROJECT_BUILD_EVENTS_TOPIC", "project-build-events")
KAFKA_TERMINAL_TOPIC = os.getenv("KAFKA_TERMINAL_TOPIC", "project-terminal-events")
KAFKA_PLAN_RESULTS_TOPIC = os.getenv("KAFKA_PLAN_RESULTS_TOPIC", "plan-results")

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


def send_plan_event(project_id: str, build_id: str, plan_json: dict):
    """
    Sends the deployment plan to the backend via the unified build events topic.
    Uses 'event_type'='plan_result' to trigger the specific parsing route.
    """
    event = {
        "event_type": "plan_result",
        "project_id": project_id,
        "plan": plan_json
    }
    producer.send(KAFKA_BUILD_EVENTS_TOPIC, value=event)
    producer.flush()
