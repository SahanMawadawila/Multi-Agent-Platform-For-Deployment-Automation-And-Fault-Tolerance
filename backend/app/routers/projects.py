"""
UI routes for project-related operations.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
# from ..models import User
from app.models import UserProject, ProjectBuild, BuildStatus
from sqlalchemy.future import select
from app.deps import get_current_user
from app.utils.project_deploy_trigger import trigger_deployment_process, trigger_plan_generation
from app.dto.ProjectDTOs import ProjectDeploymentOutDTO
# DTOs
from app.dto.ProjectDTOs import UserProjectSimpleOutDTO, UserProjectDetailOutDTO, ProjectCreateInDTO

router = APIRouter()


"""
GET /projects/
Retrieve a list of all projects for the authenticated user.
"""
@router.get("/")
async def list_projects(
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    print("Authenticated user:", user)

    result_projects = await db.execute(
        select(UserProject)
        .where(UserProject.owner_id == int(user["id"]))
        .order_by(UserProject.project_name.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    projects = [UserProjectSimpleOutDTO.from_orm(project) for project in result_projects.scalars().all()]
    total_result = await db.execute(
        select(UserProject).where(UserProject.owner_id == int(user["id"]))
    )
    total_projects = total_result.scalars().all()


    return {
        "projects": projects,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": len(total_projects),
            "total_pages": (len(total_projects) + per_page - 1) // per_page,
        },
    }


"""
GET /projects/{project_id}
Retrieve detailed information about a specific project by its ID.
"""
@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    print("Getting project:", project_id, "for user:", user)
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}
    try:
        UserProjectDetailOutDTO.model_validate(project)
    except Exception as e:
        print(f"Validation error: {e}")
        return {"error": "Data validation error"}
    
    return UserProjectDetailOutDTO.from_orm(project)


"""
POST /projects/
Create a new project for the authenticated user.
"""
@router.post("/")
async def create_project(
    project_data: ProjectCreateInDTO,
    db: AsyncSession = Depends(get_db), 
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    new_project = UserProject(
        owner_id=int(user["id"]),
        project_name=project_data.project_name,
        github_url=project_data.repository_url,
        env_vars=project_data.env_vars,
        status="created",
        plan_status="generating" if project_data.trigger_deployment else None
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    # TODO: Create a Hook to receive updates when pushes are made to the repository

    if project_data.trigger_deployment and background_tasks:
        background_tasks.add_task(trigger_plan_generation, str(new_project.project_id))
        print(f"Plan generation triggered in background for project {new_project.project_id}")

    return UserProjectDetailOutDTO.from_orm(new_project)


"""
PUT /projects/{project_id}
Update the details of an existing project.
"""
@router.put("/{project_id}")
async def update_project(
    project_id: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}
    
    # Update env_vars if provided
    if "env_vars" in update_data:
        project.env_vars = update_data["env_vars"]
    
    # Update project_name if provided
    if "project_name" in update_data:
        project.project_name = update_data["project_name"]
    
    # Update is_auto_deploy_enabled if provided
    if "is_auto_deploy_enabled" in update_data:
        project.is_auto_deploy_enabled = update_data["is_auto_deploy_enabled"]
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return UserProjectDetailOutDTO.from_orm(project)


"""
POST /projects/{project_id}/deploy
Trigger a deployment process for the specified project.
"""
@router.post("/{project_id}/deploy")
async def deploy_project(
    project_id: str,
    db: AsyncSession = Depends(get_db), 
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}

    if background_tasks:
        background_tasks.add_task(trigger_deployment_process, str(project.project_id))
        print(f"Deployment process triggered in background for project {project.project_id}")
        return {"message": "Deployment process started in background."}
    else:
        return {"error": "Background tasks not available."}


"""
POST /projects/{project_id}/generate-plan
Trigger deployment plan generation for the specified project.
This does NOT deploy — it generates a plan and sends it to the frontend for review.
"""
@router.post("/{project_id}/generate-plan")
async def generate_plan(
    project_id: str,
    db: AsyncSession = Depends(get_db), 
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}

    if background_tasks:
        background_tasks.add_task(trigger_plan_generation, str(project.project_id))
        print(f"Plan generation triggered in background for project {project.project_id}")
        return {"message": "Plan generation started."}
    else:
        return {"error": "Background tasks not available."}
    

@router.get("/{project_id}/plan")
async def get_project_plan(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get the current deployment plan for a project.
    """
    result = await db.execute(
        select(UserProject)
        .where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}
        
    return {
        "status": project.plan_status,
        "plan": project.deployment_plan
    }

@router.put("/{project_id}/plan")
async def update_project_plan(
    project_id: str,
    plan_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Update the deployment plan. Used when the user edits fields in the UI.
    """
    result = await db.execute(
        select(UserProject)
        .where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}
        
    project.deployment_plan = plan_data
    db.add(project)
    await db.commit()
    
    return {"message": "Plan updated successfully"}



"""
GET /projects/{project_id}/delployments
Retrieve a list of deployments for the specified project.
Support pagination through query parameters.
"""
@router.get("/{project_id}/deployments")
async def list_deployments(
    project_id: str,
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db), 
    user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}

    result_deployments = await db.execute(
        select(ProjectBuild)
        .where(ProjectBuild.project_id == project_id)
        .order_by(ProjectBuild.build_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    deployments = result_deployments.scalars().all()
    deployments = [ProjectDeploymentOutDTO.from_orm(deployment) for deployment in deployments]

    total_result = await db.execute(
        select(ProjectBuild).where(ProjectBuild.project_id == project_id)
    )
    total_deployments = total_result.scalars().all()

    return {
        "deployments": deployments,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": len(total_deployments),
            "total_pages": (len(total_deployments) + per_page - 1) // per_page,
        },
    }


"""
GET /projects/{project_id}/current-deployment
Get the current active deployment for the project.
"""
@router.get("/{project_id}/current-deployment")
async def get_current_deployment(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Verify project ownership
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}
    
    # Get current deployment (is_current=True)
    result = await db.execute(
        select(ProjectBuild)
        .where(ProjectBuild.project_id == project_id)
        .where(ProjectBuild.is_current == True)
        .limit(1)
    )
    current_build = result.scalars().first()
    
    if not current_build:
        # Fallback to latest successful build
        result = await db.execute(
            select(ProjectBuild)
            .where(ProjectBuild.project_id == project_id)
            .where(ProjectBuild.build_status == BuildStatus.success)
            .order_by(ProjectBuild.build_date.desc())
            .limit(1)
        )
        current_build = result.scalars().first()
    
    if not current_build:
        return {"deployment": None}
    
    return {"deployment": ProjectDeploymentOutDTO.from_orm(current_build)}


"""
POST /projects/{project_id}/rollback/{build_id}
Rollback to a previous deployment. Uses existing commit and skips rebuild.
"""
@router.post("/{project_id}/rollback/{build_id}")
async def rollback_deployment(
    project_id: str,
    build_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    from app.utils.project_deploy_trigger import trigger_rollback_process
    
    # Verify project ownership
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}
    
    # Get the build to rollback to
    result = await db.execute(
        select(ProjectBuild)
        .where(ProjectBuild.build_id == build_id)
        .where(ProjectBuild.project_id == project_id)
    )
    target_build = result.scalars().first()
    
    if not target_build:
        return {"error": "Build not found"}
    
    if background_tasks:
        background_tasks.add_task(
            trigger_rollback_process,
            str(project.project_id),
            target_build.build_id,
            target_build.build_version
        )
        return {"message": f"Rollback to version {target_build.build_version} started"}
    else:
        return {"error": "Background tasks not available"}


import os
import time
import requests
from fastapi import HTTPException

@router.get("/{project_id}/logs")
async def get_project_logs(
    project_id: str,
    db: AsyncSession = Depends(get_db), 
    user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Loki proxy
    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    
    # Query logs specifically for the generated application namespace (which matches project_id)
    query = f'{{namespace="{project.project_id}"}}'

    # Loki query_range defaults to 1 hour. We pull up to 7 days of logs to ensure we
    # catch startup messages on apps that have been running for a while.
    start_time = int((time.time() - (7 * 24 * 3600)) * 1e9) # nanoseconds

    try:
        response = requests.get(
            f"{loki_url}/loki/api/v1/query_range",
            params={
                "query": query, 
                "limit": 500,
                "start": start_time
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Loki error: {response.text}")
    except Exception as e:
        print(f"Failed to fetch logs from Loki: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Loki: {str(e)}")
