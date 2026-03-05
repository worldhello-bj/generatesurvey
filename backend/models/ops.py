from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base


class OpsRecord(Base):
    __tablename__ = "ops_records"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(64), nullable=False, index=True)
    user_id = Column(String(128), nullable=True, index=True)
    model = Column(String(128), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    success = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
