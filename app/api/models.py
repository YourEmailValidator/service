import random
import string
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)

    @staticmethod
    def generate_key(length=32):
        characters = string.ascii_letters + string.digits
        return "".join(random.choice(characters) for _ in range(length))

    # Relationships
    user = relationship("User", back_populates="api_keys")
    usage = relationship(
        "APIUsage", back_populates="api_key", cascade="all, delete-orphan"
    )


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    api_key_id = Column(
        Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    endpoint = Column(String(255), nullable=False)
    is_success = Column(Boolean, default=True)
    response_time = Column(Float)

    # Relationships
    user = relationship("User", back_populates="api_usage")
    api_key = relationship("APIKey", back_populates="usage")
