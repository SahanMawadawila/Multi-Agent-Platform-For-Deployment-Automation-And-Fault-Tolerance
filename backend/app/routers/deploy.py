from fastapi import APIRouter
from kafka import KafkaProducer
import json

router = APIRouter()

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

@router.post("/sync")
async def trigger_deploy(payload: dict):
    #1. upload to github repo

    #2. send message to kafka
    producer.send('agent-jobs', value=payload)
    producer.flush()
    return {"status": "Job sent to Kafka"}