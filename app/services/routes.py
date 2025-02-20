from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Tuple

from app.api.utils import verify_api_key_header, verify_donatur_access
from app.auth.models import User, UserStatus
from .schemas import EmailRequest, DonaturEmailRequest, EmailResponse
from .email_validator import (
    EmailValidator,
    EmailFormatError,
    DisposableEmailError,
    EmailMXRecordError,
)
from app.api.models import APIKey

router = APIRouter(prefix="/api/v1")


@router.post("/validate-email", response_model=EmailResponse)
async def validate_email(
    request: EmailRequest,
    auth: tuple[APIKey, Session] = Depends(verify_api_key_header),
):
    """Endpoint to validate a single email."""
    api_key, db = auth
    options = request.model_dump(exclude={"email"})
    email_validator = EmailValidator(request.email, **options)
    try:
        email_validator.validate()
        return EmailResponse(
            email=request.email, is_valid=True, message="Email is valid."
        )
    except (EmailFormatError, DisposableEmailError, EmailMXRecordError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-disposable", response_model=EmailResponse)
async def check_disposable_email(
    request: EmailRequest,
    auth: tuple[APIKey, Session] = Depends(verify_api_key_header),
):
    """Endpoint to check if an email is disposable."""
    api_key, db = auth
    options = request.model_dump(exclude={"email"})
    email_validator = EmailValidator(request.email, **options)
    try:
        email_validator.check_disposable()
        return EmailResponse(
            email=request.email, is_valid=True, message="Email is not disposable."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-mx-record", response_model=EmailResponse)
async def check_mx_record_email(
    request: EmailRequest,
    auth: tuple[APIKey, Session] = Depends(verify_api_key_header),
):
    """Endpoint to check if an email has valid MX records."""
    api_key, db = auth
    options = request.model_dump(exclude={"email"})
    email_validator = EmailValidator(request.email, **options)
    try:
        email_validator.check_mx_record()
        return EmailResponse(
            email=request.email, is_valid=True, message="Email has valid MX records."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-email-validate", response_model=List[EmailResponse])
async def bulk_validate_email(
    request: DonaturEmailRequest,
    auth: Tuple[APIKey, Session] = Depends(verify_donatur_access),
):
    """Endpoint to validate a list of emails. Only available for DONATUR users."""
    api_key, db = auth

    MAX_BULK_EMAILS = 1000
    if len(request.email) > MAX_BULK_EMAILS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_BULK_EMAILS} emails allowed per request",
        )

    responses = []
    success_count = 0
    options = request.model_dump(exclude={"email"})
    for email in request.email:
        email_validator = EmailValidator(email, **options)
        try:
            email_validator.validate()
            response = EmailResponse(
                email=email, is_valid=True, message="Email is valid."
            )
            success_count += 1
        except EmailFormatError:
            response = EmailResponse(
                email=email, is_valid=False, message="Invalid email format."
            )
        except DisposableEmailError:
            response = EmailResponse(
                email=email,
                is_valid=False,
                message="Disposable email addresses are not allowed.",
            )
        except EmailMXRecordError:
            response = EmailResponse(
                email=email, is_valid=False, message="Domain has no valid MX records."
            )
        responses.append(response)
    return responses


@router.get("/check-bulk-access")
async def check_bulk_validation_access(
    auth: Tuple[APIKey, Session] = Depends(verify_api_key_header),
):
    """Check if the current user has access to bulk validation."""
    api_key, db = auth
    user = db.query(User).filter(User.id == api_key.user_id).first()

    return {
        "has_access": user.status == UserStatus.DONATUR,
        "current_status": user.status,
        "required_status": UserStatus.DONATUR,
        "upgrade_required": user.status != UserStatus.DONATUR,
    }
