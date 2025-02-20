from fastapi import HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import Tuple
from app.core.utils import check_user_limit
from app.database import get_db
from app.api.models import APIKey
from app.auth.dependencies import verify_api_key
from app.auth.models import User, UserStatus


async def verify_api_key_header(
    x_api_key: str = Header(...), db: Session = Depends(get_db)
) -> tuple[APIKey, Session]:
    """Verify API key and return the associated user and API key record."""
    user = verify_api_key(x_api_key, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Get API key record
    api_key = (
        db.query(APIKey)
        .filter(APIKey.key == x_api_key, APIKey.is_active == True)
        .first()
    )

    # Check usage limits
    if not check_user_limit(user.id, db):
        raise HTTPException(
            status_code=429,
            detail="Monthly API limit reached. Please upgrade to Donatur status for unlimited access.",
        )

    return api_key, db


async def verify_donatur_access(
    x_api_key: str = Header(...), db: Session = Depends(get_db)
) -> Tuple[APIKey, Session]:
    """Verify API key and ensure user has DONATUR status."""
    api_key, db = await verify_api_key_header(x_api_key, db)

    # Check if user has DONATUR status
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user or user.status != UserStatus.DONATUR:
        raise HTTPException(
            status_code=403,
            detail="Bulk validation is only available for DONATUR users. Please upgrade your account.",
        )

    return api_key, db
