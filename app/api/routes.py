from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from . import models, schemas

router = APIRouter(prefix="/api")


@router.post("/keys", response_model=schemas.APIKeyResponse)
async def create_api_key(
    key_data: schemas.APIKeyCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        new_key = models.APIKey(
            key=models.APIKey.generate_key(),
            name=key_data.name,
            user_id=current_user.id,
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)

        return schemas.APIKeyResponse(
            id=new_key.id,
            name=new_key.name,
            key=new_key.key,
            created_at=new_key.created_at,
            usage_count=new_key.usage_count,
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        )


@router.delete("/keys/{key_id}")
async def delete_api_key(
    key_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    api_key = (
        db.query(models.APIKey)
        .filter(models.APIKey.id == key_id, models.APIKey.user_id == current_user.id)
        .first()
    )

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()
    return {"message": "API key deleted successfully"}


# Add endpoint to get user's API keys
@router.get("/keys", response_model=List[schemas.APIKeyResponse])
async def get_api_keys(
    current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    api_keys = (
        db.query(models.APIKey)
        .filter(
            models.APIKey.user_id == current_user.id, models.APIKey.is_active == True
        )
        .all()
    )

    return api_keys
