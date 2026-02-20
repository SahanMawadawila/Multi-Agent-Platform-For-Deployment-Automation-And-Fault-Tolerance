from app.kafka_terminal_producer import send_terminal_message
from app.kafka_build_producer import send_build_event
import dotenv
import asyncio
import json
import time
import os
import shutil
from aiokafka import AIOKafkaConsumer  
from config.settings import settings  
from graph import component_graph, post_processing_graph  
from tools.git_tools import AsyncGitTools
from agents.monorepo_detector_agent import detect_monorepo
from agents.monorepo_analyzer_agent import analyze_monorepo

dotenv.load_dotenv()


async def process_job(job):
    repo_url = job.get("repo_url")
    project_id = job.get("project_id")
    build_id = job.get("build_id")
    build_version = job.get("build_version", "latest")
    skip_build = job.get("skip_build", False)
    gitops_commit_id = job.get("gitops_commit_id")
    
    # Handle rollback
    if skip_build:
        from utils.rollback_handler import handle_rollback
        await handle_rollback(project_id, build_id, build_version, gitops_commit_id)
        return
    
    send_build_event(project_id, build_id, "in_progress")
    
    repo_name_full = repo_url.split("github.com/")[-1].replace(".git", "")
    owner, name = repo_name_full.split("/")
    
    local_path = os.path.abspath(f"temp/{name}")
    
    # Clone repo and list files
    await AsyncGitTools.clone_repository(repo_url, local_path)
    files = await AsyncGitTools.list_files(local_path)
    
    config = { "recursion_limit": 50 }
    start_time = time.time()
    
    # Prepare shared gitops directory
    gitops_dir = os.path.join(os.getcwd(), "temp", f"gitops_{project_id}")
    if os.path.exists(gitops_dir):
        shutil.rmtree(gitops_dir)
    os.makedirs(gitops_dir, exist_ok=True)
    
    # Step 1: Detect if monorepo
    is_monorepo = await detect_monorepo(files, project_id)
    
    # Build the components list for post-processing
    pp_components = []
    
    if not is_monorepo:
        # ==========================================
        # SINGLE PROJECT
        # ==========================================
        initial_state = {
            "project_id": project_id,
            "build_id": build_id,
            "build_version": build_version,
            "local_path": local_path,
            "file_list": files,
            "repo_owner": owner,
            "repo_name": name,
            "messages": [],
            "retry_count": 0,
            "error_fixing_plan": None,
            "current_step_index": 0,
            "analysis_results": None,
            "start_time": start_time,
            "is_multi_project": False,
        }
        
        result = await component_graph.ainvoke(initial_state, config=config)
        
        if result.get("build_status") == "failed":
            send_build_event(project_id, build_id, "failed", details={
                "error": result.get("build_error_logs", "Build failed"),
                "duration": int(time.time() - start_time),
            })
            return
        
        app_name = result.get("k8s_app_name", f"app-{project_id}")
        analysis = result.get("analyzed_repository_details")
        pp_components = [{
            "name": "app",
            "app_name": app_name,
            "api_path_prefix": "/",
            "port": analysis.port if analysis else 3000,
            "health_check_path": getattr(analysis, "health_check_path", "/"),
        }]
    else:
        # ==========================================
        # MULTI-PROJECT (MONOREPO)
        # ==========================================
        components = await analyze_monorepo(files, project_id, local_path)
        
        send_terminal_message(project_id, f"🔀 Deploying {len(components)} components in parallel...\n\r")
        
        tasks = []
        for comp in components:
            comp_local_path = os.path.abspath(f"temp/{name}-{comp['name']}")
            await AsyncGitTools.clone_repository(repo_url, comp_local_path)
            
            branch_name = comp["name"]
            send_terminal_message(project_id, f"🔀 Creating branch '{branch_name}' for: {comp['name']}\n\r")
            await AsyncGitTools.create_and_checkout_branch(comp_local_path, branch_name)
            
            comp_state = {
                "project_id": project_id,
                "build_id": build_id,
                "build_version": build_version,
                "local_path": comp_local_path,
                "file_list": comp["file_list"],
                "repo_owner": owner,
                "repo_name": name,
                "messages": [],
                "retry_count": 0,
                "error_fixing_plan": None,
                "current_step_index": 0,
                "analysis_results": None,
                "start_time": start_time,
                "component_name": comp["name"],
                "component_path": comp["path"],
                "branch_name": branch_name,
                "is_multi_project": True,
                "overridden_envs": comp.get("networking_env_overrides", {}),
                "role": comp.get("role", "backend"),
                "api_path_prefix": comp.get("api_path_prefix", "/"),
            }
            tasks.append(component_graph.ainvoke(comp_state, config=config))
        
        results = await asyncio.gather(*tasks)
        
        # Build post-processing component list from results
        for comp, result in zip(components, results):
            app_name = result.get("k8s_app_name", f"app-{project_id}-{comp['name']}")
            analysis = result.get("analyzed_repository_details")
            pp_components.append({
                "name": comp["name"],
                "app_name": app_name,
                "api_path_prefix": comp.get("api_path_prefix", "/"),
                "port": analysis.port if analysis else 3000,
                "health_check_path": getattr(analysis, "health_check_path", "/") if analysis else "/",
            })
    
    # ==========================================
    # POST-PROCESSING GRAPH (runs once for both)
    # ==========================================
    send_terminal_message(project_id, "🔧 Starting post-processing...\n\r")
    
    post_state = {
        "project_id": project_id,
        "build_id": build_id,
        "start_time": start_time,
        "is_multi_project": is_monorepo,
        "components": pp_components,
    }
    
    await post_processing_graph.ainvoke(post_state, config=config)
    
    send_terminal_message(project_id, "✅ Deployment pipeline complete.\n\r")


async def consume():
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_server,
        group_id="agent-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        session_timeout_ms=60000,
        heartbeat_interval_ms=10000,
        max_poll_interval_ms=600000,
    )

    await consumer.start()
    print("Kafka Consumer Started...")
    
    try:
        async for message in consumer:
            job = message.value
            print(f"📥 Received Job: {job}")
            project_id = job.get("project_id")
            send_terminal_message(project_id, "🤖 Handing over deployment to the DevOps agentic framework...\n\r")
            asyncio.create_task(process_job(job))
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())