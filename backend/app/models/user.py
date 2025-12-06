from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)            
    provider = Column(String, nullable=False)       
    provider_id = Column(String, unique=True)       
    image = Column(String, nullable=True)           
    is_active = Column(Boolean, default=True)
