from pydantic import BaseModel
from datetime import datetime


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str
    created_at: datetime
    usage_count: int

    class Config:
        from_attributes = True
