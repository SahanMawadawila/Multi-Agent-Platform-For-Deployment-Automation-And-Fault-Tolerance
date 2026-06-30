import yaml
import os
import subprocess

path = r"c:\fyp\fyp\source_code\Multi-Agent-Platform-For-Deployment-Automation-And-Fault-Tolerance\devops_agents\temp\gitops_1226a5a3-32df-4d62-8c65-e0b6293e6aa5\app\infra\kafka\infra-manifest.yaml"
repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(path)))

with open(path, "r") as f:
    docs = list(yaml.safe_load_all(f))

for d in docs:
    if d and d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == "kafka":
        envs = d["spec"]["template"]["spec"]["containers"][0]["env"]
        # Keep the first occurrence of each variable (which corresponds to the template's hardcoded ones in our old template before we swapped order)
        # Wait, if we keep the first occurrence, the hallucinated ones are AT THE BOTTOM.
        # So we should iterate forwards and keep the first occurrence of each key.
        clean_envs = []
        seen = set()
        for e in envs:
            if e["name"] not in seen:
                seen.add(e["name"])
                clean_envs.append(e)
        d["spec"]["template"]["spec"]["containers"][0]["env"] = clean_envs

with open(path, "w") as f:
    yaml.dump_all(docs, f)

# Commit and push
subprocess.run(["git", "add", "."], cwd=repo_dir)
subprocess.run(["git", "commit", "-m", "fix kafka env vars manually"], cwd=repo_dir)
subprocess.run(["git", "push"], cwd=repo_dir)
