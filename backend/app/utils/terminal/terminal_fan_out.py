import asyncio
import json
from aiokafka import AIOKafkaConsumer
import websockets
import os


KAFKA_TERMINAL_TOPIC = os.getenv("KAFKA_TERMINAL_TOPIC", "project-terminal-events")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TERMINAL_CONSUMER_GROUP = os.getenv("KAFKA_TERMINAL_CONSUMER_GROUP", "project-terminal-consumers")



PROJECT_CLIENTS = {}   # project_id -> set(websocket)

async def register(ws, project_id):
    PROJECT_CLIENTS.setdefault(project_id, set()).add(ws)

async def unregister(ws, project_id):
    PROJECT_CLIENTS[project_id].remove(ws)

async def websocket_handler(ws):
    msg = await ws.recv()          # Client sends {"project_id": "..."}
    data = json.loads(msg)
    project_id = data["project_id"]

    await register(ws, project_id)
    try:
        while True:
            await asyncio.sleep(1) # keep alive
    finally:
        await unregister(ws, project_id)

async def kafka_listener():
    consumer = AIOKafkaConsumer(
        KAFKA_TERMINAL_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_TERMINAL_CONSUMER_GROUP,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode())
    )
    print(f"Starting kafka_listener for topic={KAFKA_TERMINAL_TOPIC} group={KAFKA_TERMINAL_CONSUMER_GROUP}")
    await consumer.start()
    try:
        async for msg in consumer:
            event = msg.value
            
            project_id = event.get("project_id")
            if not project_id:
                continue

            if "message" not in event:
                continue
            else:
                message_to_send = event["message"]

            if project_id in PROJECT_CLIENTS:
                dead = []
                for ws in PROJECT_CLIENTS[project_id]:
                    try:
                        await ws.send_text(message_to_send)
                    except:
                        dead.append(ws)

                for ws in dead:
                    PROJECT_CLIENTS[project_id].discard(ws)
    finally:
        await consumer.stop()

# async def main():
#     server = websockets.serve(websocket_handler, "0.0.0.0", 8080)
#     await asyncio.gather(server, kafka_listener())

# asyncio.run(main())
