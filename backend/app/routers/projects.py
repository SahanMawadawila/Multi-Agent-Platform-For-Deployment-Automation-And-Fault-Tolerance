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
from app.utils.project_deploy_trigger import trigger_deployment_process
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
        status="created"
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    # TODO: Create a Hook to receive updates when pushes are made to the repository

    if project_data.trigger_deployment and background_tasks:
        background_tasks.add_task(trigger_deployment_process, str(new_project.project_id))
        print(f"Deployment process triggered in background for project {new_project.project_id}")

    return UserProjectDetailOutDTO.from_orm(new_project)


"""
PUT /projects/{project_id}
Update the details of an existing project.
"""



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