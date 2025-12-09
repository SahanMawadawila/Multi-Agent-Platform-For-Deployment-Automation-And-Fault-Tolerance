from sqlalchemy.orm import declarative_base

# Create a single Base instance to be used by all models
Base = declarative_base()

# Import all models to register them with the Base metadata
from .user import User
from .user_project import UserProject
from .project_builds import ProjectBuild

__all__ = ["Base", "User", "UserProject", "ProjectBuild"]
