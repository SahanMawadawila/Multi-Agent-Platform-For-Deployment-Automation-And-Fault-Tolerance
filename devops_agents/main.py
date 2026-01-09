# main.py
from app.kafka_consumer import start_consumer
from app.kafka_terminal_producer import send_terminal_message  # Producer to terminal topic
import dotenv
dotenv.load_dotenv()

import asyncio  # Async IO
import json  # JSON parsing
from aiokafka import AIOKafkaConsumer  # ASYNC Kafka client (Critical change)
from config.settings import settings  # Settings
from graph import app  # The compiled LangGraph

async def process_job(job):
    """
    Runs the graph for a single job.
    """
    repo_url = job.get("repo_url")
    project_id = job.get("project_id")
    print(f"🚀 Processing Repo: {repo_url}")
    send_terminal_message(project_id, f"🚀 Processing Repo: {repo_url}\n\r")
    
    # Initialize state
    initial_state = {
        "repo_url": repo_url,
        "project_id": job.get("project_id"),
        "messages": [] # Empty history
    }

    config = { "recursion_limit": 15 }
    
    # Run the graph (ainvoke is the async method)
    result = await app.ainvoke(initial_state, config=config)
    
    # Print the result
    print(f"✅ Analysis Complete for {repo_url}")
    send_terminal_message(project_id, f"✅ Analysis Complete for {repo_url}\n\r")

    print(f"📄 Result: {result['final_analysis']}")
    send_terminal_message(project_id, f"📄 Result: {result['final_analysis']}\n\r")
    # Here you would typically send the result back to another Kafka topic

async def consume():
    """
    Starts the Async Kafka Consumer loop.
    """
    # Initialize AIOKafkaConsumer (Non-blocking)
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_server,
        group_id="agent-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    # Start the consumer connection
    await consumer.start()
    print("📡 Async Kafka Consumer Started...")
    
    try:
        # Loop strictly asynchronously
        async for message in consumer:
            job = message.value
            print(f"📥 Received Job: {job}")
            project_id = job.get("project_id")
            if not project_id:
                print("⚠️ Job missing project_id, skipping terminal message.")
            
            send_terminal_message(project_id, f"📥 Received Job\n\r")

            
            # Run processing in background (or await if you want sequential processing)
            # Awaiting ensures we don't crash the consumer with too many concurrent graphs
            await process_job(job)
            
    finally:
        # Close connection on stop
        await consumer.stop()

if __name__ == "__main__":
    # Entry point for asyncio
    asyncio.run(consume())