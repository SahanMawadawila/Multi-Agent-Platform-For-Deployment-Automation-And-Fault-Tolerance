from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Enum, String
from sqlalchemy.dialects.postgresql import UUID # Using UUID from the postgresql dialect
import enum
from datetime import datetime
from . import Base

# 1. Define the Python Enum class
class BuildStatus(enum.Enum):
    """
    Python Enum for the build_statuses.
    The string values must match the desired values in the database.
    """
    queued = 'queued'
    in_process = 'in_process'
    success = 'success'
    failed = 'failed'


class ProjectBuild(Base):
    """
    SQLAlchemy model for the 'project_builds' table in PostgreSQL.
    """
    __tablename__ = 'project_builds'
    
    # build_id int [primary key]
    # Uses Integer primary key with autoincrement
    build_id = Column(
        Integer, 
        primary_key=True, 
        autoincrement=True
    )
    
    # project_id uuid [ref: > user_projects.project_id, not null]
    # Foreign Key linking to the UserProject model's project_id (using UUID type)
    project_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('user_projects.project_id'), 
        nullable=False
    )
    
    # build_version string (semantic versioning: "1.0", "1.1", etc.)
    build_version = Column(
        String, 
        nullable=False,
        default="1.0"
    )
    
    # build_date datetime
    # Uses DateTime and defaults to the current time on creation
    build_date = Column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    # build_status build_statuses
    # Uses PostgreSQL's native Enum type for database enforcement
    build_status = Column(
        Enum(BuildStatus, name='build_statuses', create_type=True),
        nullable=False
    )

    # Commit ID associated with this build
    commit_id = Column(
        String,
        nullable=True
    )
    
    
    # is_current bool
    is_current = Column(
        Boolean, 
        default=False, 
        nullable=False
    )

    def __repr__(self):
        return (
            f"<ProjectBuild("
            f"build_id={self.build_id}, "
            f"project_id='{self.project_id}', "
            f"status='{self.build_status.value}')>"
        )

# --- Note on Enum Creation ---
# When you use Base.metadata.create_all(engine), SQLAlchemy will automatically 
# issue the CREATE TYPE SQL command to the PostgreSQL database for the 'build_statuses' 
# enum because 'create_type=True' is set in the Column definition.