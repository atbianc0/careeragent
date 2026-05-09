from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
import sys
import os

# Add the project root to sys.path so we can import backend.app.database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from backend.app.database import Base

class JobSource(Base):
    __tablename__ = "job_sources"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, index=True)
    name = Column(String, nullable=True) # E.g., formal company name
    ats_type = Column(String, index=True)
    source_type = Column(String, nullable=True) # Direct, Agency, etc.
    base_url = Column(String, unique=True, index=True)
    normalized_url = Column(String, unique=True, index=True)
    original_discovered_url = Column(String, nullable=True)
    discovery_method = Column(String, nullable=True)
    search_query_used = Column(String, nullable=True)
    
    enabled = Column(Boolean, default=True)
    status = Column(String, default="valid") # valid, invalid, partial, unsupported, blocked
    
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    last_success_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    total_jobs_found = Column(Integer, default=0)
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
