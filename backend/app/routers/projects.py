"""
UI routes for project-related operations.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .deps import get_db
# from ..models import User
from app.models import UserProject
from sqlalchemy.future import select
from app.deps import get_current_user

# DTOs
from app.dto.ProjectDTOs import UserProjectSimpleOutDTO, UserProjectDetailOutDTO

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
    result = await db.execute(
        select(UserProject).where(UserProject.project_id == project_id)
        .where(UserProject.owner_id == int(user["id"]))
    )
    project = result.scalars().first()
    if not project:
        return {"error": "Project not found"}

    return UserProjectDetailOutDTO.from_orm(project)



"""
POST /projects/
Create a new project for the authenticated user.
"""



"""
PUT /projects/{project_id}
Update the details of an existing project.
"""