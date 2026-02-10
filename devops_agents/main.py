from app.kafka_terminal_producer import send_terminal_message
from app.kafka_build_producer import send_build_event
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
    build_id = job.get("build_id")
    build_version = job.get("build_version", "latest")
    skip_build = job.get("skip_build", False)
    gitops_commit_id = job.get("gitops_commit_id")  # For rollback
    
    # Handle rollback (skip_build=True)
    if skip_build:
        from utils.rollback_handler import handle_rollback
        await handle_rollback(project_id, build_id, build_version, gitops_commit_id)
        return
    
    # Notify backend that build is now in progress
    send_build_event(project_id, build_id, "in_progress")
    
    repo_name_full = repo_url.split("github.com/")[-1].replace(".git", "")
    owner, name = repo_name_full.split("/")
    
    local_path = f"temp/{name}"
    
    # Execute setup steps before the graph
    await AsyncGitTools.clone_repository(repo_url, local_path)
    files = await AsyncGitTools.list_files(local_path)
    
    initial_state = {
        "project_id": job.get("project_id"),
        "build_id": job.get("build_id"),
        "build_version": build_version,
        "local_path": local_path,
        "file_list": files,
        "repo_owner": owner,
        "repo_name": name,
        "messages": [],
        "retry_count": 0,
        "error_fixing_plan": None,
        "current_step_index": 0,
        "analysis_results": None
    }

    #This is just for debug purposes
    config = { "recursion_limit": 50 }
    
    result = await app.ainvoke(initial_state, config=config)

    send_terminal_message(project_id, "Analysis Complete")

async def consume():
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_server,
        group_id="agent-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        session_timeout_ms=60000,        # 60s before Kafka considers consumer dead
        heartbeat_interval_ms=10000,     # Send heartbeat every 10s
        max_poll_interval_ms=600000,     # Allow 10 min between polls (for long jobs)
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