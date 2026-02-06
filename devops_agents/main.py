from app.kafka_terminal_producer import send_terminal_message
import dotenv
import asyncio
import json 
from aiokafka import AIOKafkaConsumer  
from config.settings import settings  
from graph import app  
from tools.git_tools import AsyncGitTools
dotenv.load_dotenv()

async def process_job(job):
    repo_url = job.get("repo_url")
    project_id = job.get("project_id")
    
    repo_name_full = repo_url.split("github.com/")[-1].replace(".git", "")
    owner, name = repo_name_full.split("/")
    
    local_path = f"temp/{name}"
    
    # Execute setup steps before the graph
    await AsyncGitTools.clone_repository(repo_url, local_path)
    files = await AsyncGitTools.list_files(local_path)
    
    initial_state = {
        "project_id": job.get("project_id"),
        "local_path": local_path,
        "file_list": files,
        "repo_owner": owner,
        "repo_name": name,
        "messages": [],
        "retry_count": 0
    }

    #This is just for debug purposes
    config = { "recursion_limit": 25 }
    
    result = await app.ainvoke(initial_state, config=config)

    send_terminal_message(project_id, "Analysis Complete")

async def consume():
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_server,
        group_id="agent-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    await consumer.start()
    print("Kafka Consumer Started...")
    
    try:
        async for message in consumer:
            job = message.value
            print(f"📥 Received Job: {job}")
            project_id = job.get("project_id")
            send_terminal_message(project_id, "Handover the deployment to the devops agentic framework")
            #now it not wait until the job is completed
            asyncio.create_task(process_job(job))
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())