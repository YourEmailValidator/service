from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from . import models, schemas, utils
from .dependencies import get_current_user_optional, get_current_user
from app.core.utils import send_email

router = APIRouter()
templates = Jinja2Templates(directory="templates")
utc_now = datetime.now(timezone.utc)


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user_optional(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        "pages/login.html", {"request": request, "current_user": None}
    )


@router.post("/login", name="login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not utils.verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "error": "Invalid username or password",
                "current_user": None,
            },
            status_code=400,
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,
        expires=1800,
        path="/",
        samesite="lax",
        secure=True,
    )

    return response


@router.get("/register", response_class=HTMLResponse, name="register")
async def register_page(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user_optional(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        "pages/register.html", {"request": request, "current_user": None}
    )


@router.post("/register", name="register_post")
async def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if username exists
        if (
            db.query(models.User)
            .filter(models.User.username == user_data.username)
            .first()
        ):
            raise HTTPException(status_code=400, detail="Username already registered")

        # Check if email exists
        if db.query(models.User).filter(models.User.email == user_data.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create new user
        hashed_password = utils.get_password_hash(user_data.password)
        user = models.User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Registration successful"},
        )

    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(
            status_code=500, detail="An error occurred during registration"
        )


@router.post("/logout", name="logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=False,
        httponly=True,
    )
    return response


@router.get("/forgot-password", response_class=HTMLResponse, name="forgot_password")
async def forgot_password_page(request: Request):
    """Render forgot password form."""
    return templates.TemplateResponse(
        "pages/forgot_password.html", {"request": request, "current_user": None}
    )


@router.post("/forgot-password")
async def forgot_password(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    email = form_data.get("email")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Don't reveal if email exists
        return templates.TemplateResponse(
            "pages/forgot_password.html",
            {
                "request": request,
                "message": "If your email is registered, you will receive a password reset link.",
                "current_user": None,
            },
        )

    # Create password reset token
    token = utils.generate_password_reset_token()
    expires_at = utc_now + timedelta(minutes=30)

    reset_request = models.PasswordReset(
        user_id=user.id, token=token, expires_at=expires_at
    )

    db.add(reset_request)
    db.commit()

    # Create reset URL
    reset_url = f"{request.base_url}reset-password/{token}"

    # Send email
    try:
        email_body = utils.create_password_reset_email(reset_url)
        send_email(
            to_email=user.email,
            subject="Reset Your Password - YourEmailValidator",
            body=email_body,
        )
    except Exception:
        db.rollback()
        return templates.TemplateResponse(
            "pages/forgot_password.html",
            {
                "request": request,
                "error": "Failed to send reset email. Please try again.",
                "current_user": None,
            },
        )

    return templates.TemplateResponse(
        "pages/forgot_password.html",
        {
            "request": request,
            "message": "If your email is registered, you will receive a password reset link.",
            "current_user": None,
        },
    )


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(request: Request, db: Session = Depends(get_db)):
    """Render reset password form."""
    token = request.path_params.get("token")
    reset_request = (
        db.query(models.PasswordReset)
        .filter(
            models.PasswordReset.token == token,
            models.PasswordReset.is_used == False,
            models.PasswordReset.expires_at > utc_now,
        )
        .first()
    )

    if not reset_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return templates.TemplateResponse(
        "pages/reset_password.html",
        {"request": request, "token": token, "current_user": None},
    )


@router.post("/reset-password/")
async def reset_password(request: Request, db: Session = Depends(get_db)):
    """Handle password reset."""
    form_data = await request.form()
    token: str = form_data.get("token")
    new_password = form_data.get("new_password")
    confirm_password = form_data.get("confirm_password")

    if new_password != confirm_password:
        return templates.TemplateResponse(
            "pages/reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Passwords do not match",
                "current_user": None,
            },
        )

    reset_request = (
        db.query(models.PasswordReset)
        .filter(
            models.PasswordReset.token == token,
            models.PasswordReset.is_used == False,
            models.PasswordReset.expires_at > utc_now,
        )
        .first()
    )

    if not reset_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password
    user = reset_request.user
    user.hashed_password = utils.get_password_hash(new_password)

    # Mark token as used
    reset_request.is_used = True
    db.commit()

    return RedirectResponse(
        url="/login?reset=success", status_code=status.HTTP_302_FOUND
    )


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request, current_user: models.User = Depends(get_current_user)
):
    """Render change password form."""
    return templates.TemplateResponse(
        "pages/change_password.html", {"request": request, "current_user": current_user}
    )


@router.post("/change-password", name="change_password")
async def change_password(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handle password change."""
    form_data = await request.form()
    current_password = form_data.get("current_password")
    new_password = form_data.get("new_password")
    confirm_password = form_data.get("confirm_password")

    if not utils.verify_password(current_password, current_user.hashed_password):
        return templates.TemplateResponse(
            "pages/change_password.html",
            {
                "request": request,
                "error": "Current password is incorrect",
                "current_user": current_user,
            },
        )

    if new_password != confirm_password:
        return templates.TemplateResponse(
            "pages/change_password.html",
            {
                "request": request,
                "error": "New passwords do not match",
                "current_user": current_user,
            },
        )

    # Update password
    current_user.hashed_password = utils.get_password_hash(new_password)
    db.commit()

    # Send confirmation email
    try:
        email_body = """
Hello,

Your password has been successfully changed.
If you did not make this change, please contact support immediately.

Best regards,
YourEmailValidator Team
        """
        send_email(
            to_email=current_user.email,
            subject="Password Changed - YourEmailValidator",
            body=email_body,
        )
    except Exception:
        pass

    return RedirectResponse(
        url="/dashboard?password=changed", status_code=status.HTTP_302_FOUND
    )
