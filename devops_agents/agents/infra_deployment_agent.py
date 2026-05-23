import json
import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.kafka_terminal_producer import send_terminal_message
from config.settings import settings


async def infra_deployment_agent(state: dict):
    """
    Generates K8s manifests for infrastructure components only.
    Outputs into temp/gitops_{project_id}/app/infra/{service_name}/
    """
    project_id = state.get("project_id", "")
    component = state.get("infra_component") or {}
    service_name = component.get("name")

    send_terminal_message(project_id, f"🧱 Generating infra manifests for {service_name or 'infra'}...\n\r")

    gitops_base = state.get("gitops_dir")
    manifests_path = os.path.join(gitops_base, "app", "infra", service_name or "infra")
    os.makedirs(manifests_path, exist_ok=True)

    llm = ChatOpenAI(
        model="gpt-5.4-mini",
        api_key=settings.openai_key,
        temperature=0,
    )

    system_prompt = (
        "You are a Kubernetes expert. Generate only valid Kubernetes YAML. "
        "Output MUST be plain YAML, no markdown or explanations. "
        "Create infrastructure manifests that are fully deployable on Kubernetes using the provided details. "
        "Use the provided infra component fields as your baseline source of truth. "
        "Namespace MUST be exactly the provided namespace value. "
        "CRITICAL RULES FOR DATABASES AND INFRASTRUCTURE: "
        "1. NEVER use emptyDir for data volumes. MUST use a PersistentVolumeClaim requesting at least 1Gi of storage with `storageClassName: gp2`. "
        "2. DO NOT create any helper, placeholder, mounter, or volume-attacher pods. Only generate the actual StatefulSet/Deployment, Service, PVC, and Secret. "
        "3. For StatefulSets, ensure the YAML is fully valid. Do NOT include read-only fields like `templateGeneration` and do NOT include empty `volumeClaimTemplates: []`."
    )
    
    # Load specific infra fixes dynamically
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "error_fixus.json")
        with open(config_path, "r") as f:
            error_fixus = json.load(f)
            
        component_name = (service_name or "").lower()
        image_name = (component.get("image") or "").lower()
        
        specific_rules = []
        for key, rule in error_fixus.items():
            if key.lower() in component_name or key.lower() in image_name:
                specific_rules.append(rule)
                
        if specific_rules:
            system_prompt += "\n\nCOMPONENT SPECIFIC CRITICAL RULES:\n"
            for idx, rule in enumerate(specific_rules, 1):
                system_prompt += f"{idx}. {rule}\n"
    except Exception as e:
        send_terminal_message(project_id, f"⚠️ Warning: Could not load error_fixus.json: {e}\n\r")

    user_payload = {
        "project_id": project_id,
        "namespace": project_id,
        "infra_component": component,
    }

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(user_payload, indent=2)),
    ]

    response = await llm.ainvoke(messages)
    manifest_yaml = response.content.strip()

    if manifest_yaml.startswith("```"):
        lines = manifest_yaml.split("\n")
        manifest_yaml = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    output_path = os.path.join(manifests_path, "infra-manifest.yaml")
    with open(output_path, "w") as f:
        f.write(manifest_yaml)

    send_terminal_message(project_id, f"📄 Generated infra/{service_name or 'infra'}/infra-manifest.yaml\n\r")

    send_terminal_message(project_id, f"✅ Infra manifests ready for {service_name or 'infra'}.\n\r")

    return {"infra_status": "manifests_ready"}
