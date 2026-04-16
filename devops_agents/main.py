from app.kafka_terminal_producer import send_terminal_message
from app.kafka_build_producer import send_build_event, send_plan_event
import dotenv
import asyncio
import json
import time
import os
import shutil
import uuid
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer  
from config.settings import settings  
from graph import component_graph, post_processing_graph  
from tools.git_tools import AsyncGitTools
from agents.monorepo_detector_agent import detect_monorepo
from agents.monorepo_analyzer_agent import analyze_monorepo
from agents.deployment_planner_agent import run_deployment_planner

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


# ====================================================================
# Phase 1: Deployment Planning
# ====================================================================
async def generate_deployment_plan(job):
    """
    Planning-only flow: clone repo, run planner agent, send plan to frontend.
    This does NOT trigger any deployment. The user reviews the plan first.
    """
    repo_url = job.get("repo_url")
    project_id = job.get("project_id")
    build_id = job.get("build_id", "")

    print(f"[Plan] Starting deployment plan generation for {project_id}")

    try:
        repo_name_full = repo_url.split("github.com/")[-1].replace(".git", "")
        owner, name = repo_name_full.split("/")
        local_path = os.path.abspath(f"temp/{name}")

        # Clone repo and list files
        print(f"[Plan] Cloning repository for {project_id}...")
        await AsyncGitTools.clone_repository(repo_url, local_path)
        files = await AsyncGitTools.list_files(local_path)
        print(f"[Plan] Repository cloned. Found {len(files)} files.")

        # Run the deployment planner agent
        plan = await run_deployment_planner(
            file_list=files,
            local_path=local_path,
            project_id=project_id,
            build_id=build_id,
            repo_url=repo_url,
        )

        # Build the full plan JSON with metadata
        plan_json = {
            "plan_id": f"plan_{uuid.uuid4().hex[:12]}",
            "project_id": project_id,
            "build_id": build_id,
            "repo_url": repo_url,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_approval",
            **plan.model_dump(),
        }

        # --- Debugging: Save to local 'logs' folder ---
        os.makedirs("logs", exist_ok=True)
        debug_log_path = os.path.join("logs", f"deployment_plan_{project_id}.json")
        try:
            with open(debug_log_path, "w", encoding="utf-8") as f:
                json.dump(plan_json, f, indent=4)
            print(f"[Plan Debug] Saved local copy to {debug_log_path}")
        except Exception as e:
            print(f"[Plan Debug] Failed to save local debug JSON: {e}")
        # ----------------------------------------------

        # Send plan to frontend via Kafka
        send_plan_event(project_id, build_id, plan_json)
        print(f"[Plan] Deployment plan sent for review for {project_id}")

    except Exception as e:
        print(f"[Plan] Plan generation error for {project_id}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup cloned repo
        if 'local_path' in dir() and os.path.exists(local_path):
            shutil.rmtree(local_path, ignore_errors=True)


# ====================================================================
# Kafka Consumers
# ====================================================================

async def consume_agent_jobs():
    """Existing consumer for agent-jobs topic (deployment execution)."""
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
    print("✅ Kafka Consumer Started (agent-jobs)...")
    
    try:
        async for message in consumer:
            job = message.value
            print(f"📥 Received Agent Job: {job}")
            project_id = job.get("project_id")
            send_terminal_message(project_id, "🤖 DevOps agents received the job. Starting pipeline...\n\r")
            asyncio.create_task(process_job(job))
    finally:
        await consumer.stop()


async def consume_plan_requests():
    """New consumer for generate-plan topic (deployment planning)."""
    consumer = AIOKafkaConsumer(
        "generate-plan",
        bootstrap_servers=settings.kafka_server,
        group_id="plan-agent-group",
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        session_timeout_ms=60000,
        heartbeat_interval_ms=10000,
        max_poll_interval_ms=600000,
    )

    await consumer.start()
    print("✅ Kafka Consumer Started (generate-plan)...")
    
    try:
        async for message in consumer:
            job = message.value
            print(f"📥 Received Plan Request: {job}")
            project_id = job.get("project_id")
            send_terminal_message(project_id, "🤖 Planning agent received your request...\n\r")
            asyncio.create_task(generate_deployment_plan(job))
    finally:
        await consumer.stop()


async def main():
    """Start both consumers concurrently."""
    await asyncio.gather(
        consume_agent_jobs(),
        consume_plan_requests(),
    )


if __name__ == "__main__":
    asyncio.run(main())