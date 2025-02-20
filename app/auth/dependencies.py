from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from . import utils, models
from jose import JWTError
from app.config import settings
from typing import Optional


async def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    try:
        payload = utils.jwt.decode(
            str(token), settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> Optional[models.User]:
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


def verify_api_key(api_key: str, db: Session) -> Optional[models.User]:
    from app.api.models import APIKey

    db_key = (
        db.query(APIKey).filter(APIKey.key == api_key, APIKey.is_active == True).first()
    )
    if not db_key:
        return None
    return db.query(models.User).filter(models.User.id == db_key.user_id).first()
