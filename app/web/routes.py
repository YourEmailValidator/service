from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.utils import get_usage_stats
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.api.models import APIKey
from datetime import datetime
from app.auth.models import User, UserStatus
import json

from app.web.utils import get_dashboard_stats

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Load FAQ data
with open("faq.json", "r") as f:
    FAQ_ITEMS = json.load(f)


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    data = """User-agent: *\nDisallow: /admin/\nDisallow: /upgrade-to-donatur/"""
    return data


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "pages/home.html",
        {
            "request": request,
            "hero_title": "Validate emails with confidence ✨",
            "hero_description": "Simple, reliable email validation API for developers.",
            "faq_items": FAQ_ITEMS,
            "current_year": datetime.now().year,
            "current_user": current_user,
        },
    )


@router.get("/docs-temp", response_class=HTMLResponse)
async def docs(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "pages/documentation.html",
        {
            "request": request,
            "hero_title": "Validate emails with confidence ✨",
            "hero_description": "Simple, reliable email validation API for developers.",
            "faq_items": FAQ_ITEMS,
            "current_year": datetime.now().year,
            "current_user": current_user,
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get active API keys
    api_keys = (
        db.query(APIKey)
        .filter(APIKey.user_id == current_user.id, APIKey.is_active == True)
        .all()
    )

    # Get usage statistics
    usage_stats = get_dashboard_stats(current_user, db)
    usage_stats["dates"] = [date.isoformat() for date in usage_stats["dates"]]
    return templates.TemplateResponse(
        "pages/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "api_keys": api_keys,
            "usage_stats": usage_stats,
        },
    )


@router.get("/docs-api", response_class=HTMLResponse)
async def docs_api(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "pages/docs-api.html",
        {
            "request": request,
            "hero_title": "Validate emails with confidence ✨",
            "hero_description": "Simple, reliable email validation API for developers.",
            "faq_items": FAQ_ITEMS,
            "current_year": datetime.now().year,
            "current_user": current_user,
        },
    )


# @router.post("/upgrade-to-donatur" name='upgrade_to_donatur')
# async def upgrade_to_donatur(
#     request: Request,
#     current_user=Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     try:
#         current_user.status = UserStatus.DONATUR
#         db.commit()
#         return RedirectResponse(
#             url="/dashboard?upgraded=true", status_code=status.HTTP_302_FOUND
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail="Failed to upgrade user status")


@router.get("/usage-stats")
async def get_user_usage_stats(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stats = get_usage_stats(current_user.id, db)
    monthly_limit = None if current_user.status == UserStatus.DONATUR else 100

    return {
        "status": current_user.status,
        "monthly_limit": monthly_limit,
        "current_usage": stats["total_calls"],
        "remaining_calls": None
        if monthly_limit is None
        else max(0, monthly_limit - stats["total_calls"]),
        "is_limited": current_user.status == UserStatus.FREE,
    }
