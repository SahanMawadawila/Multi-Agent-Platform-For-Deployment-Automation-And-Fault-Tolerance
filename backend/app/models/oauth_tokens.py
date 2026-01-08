from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from . import Base

class OauthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    provider = Column(String, nullable=False)
    access_token = Column(String, nullable=True)            
    refresh_token = Column(String, nullable=True)
    access_token_expires_at = Column(DateTime, nullable=True)
    refresh_token_expires_at = Column(DateTime, nullable=True)
    scope = Column(String, nullable=True)  
    token_type = Column(String, nullable=True)  
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
