from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UUID, JSON, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from . import Base

class UserProject(Base):
    """
    SQLAlchemy model for the 'user_projects' table in PostgreSQL.
    """
    __tablename__ = 'user_projects'

    # project_id uuid [primary key]
    # We use SQLAlchemy's UUID type and generate a default UUID on creation
    project_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        nullable=False
    )
    
    # owner_id int [ref: > users.id]
    # Assumes 'users' table exists and has an 'id' column
    owner_id = Column(
        Integer, 
        ForeignKey('users.id'), 
        nullable=False
    )
    
    # project_name varchar
    project_name = Column(
        String, 
        nullable=False
    )
    
    # github_url varchar
    github_url = Column(
        String
    )
    
    # is_auto_deploy_enabled bool
    is_auto_deploy_enabled = Column(
        Boolean, 
        default=False, 
        nullable=False
    )

    # domain_name varchar
    domain_name = Column(
        String,
        nullable=True
    )
    
    # status varchar
    status = Column(
        String,
        nullable=True
    )

    # env_vars jsonb
    env_vars = Column(
        JSONB,
        nullable=True
    )

    # GitHub webhook ID for auto-sync (stored as BigInteger since GitHub IDs can be large)
    webhook_id = Column(
        BigInteger,
        nullable=True
    )

    # Webhook secret for verifying payloads
    webhook_secret = Column(
        String,
        nullable=True
    )

    # Project access URL (e.g., https://myapp.flowpilot.io)
    project_access_url = Column(
        String,
        nullable=True
    )

    def __repr__(self):
        return (
            f"<UserProject("
            f"project_id='{self.project_id}', "
            f"project_name='{self.project_name}', "
            f"owner_id={self.owner_id})>"
        )

# --- Example Usage (requires a database connection, omitted for brevity) ---
# To create the table in the database:
# from sqlalchemy import create_engine
# engine = create_engine("postgresql+psycopg2://user:pass@host/dbname")
# Base.metadata.create_all(engine)