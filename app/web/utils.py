from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.api.models import APIKey, APIUsage
from app.auth.models import User, UserStatus
from typing import Dict, Any

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_dashboard_stats(user: User, db: Session) -> Dict[str, Any]:
    """Calculate dashboard statistics for a user."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Get daily API calls for the last 30 days
    daily_usage = (
        db.query(
            func.date(APIUsage.timestamp).label("date"),
            func.count(APIUsage.id).label("count"),
        )
        .filter(
            APIUsage.user_id == user.id,
            APIUsage.timestamp >= start_date,
            APIUsage.timestamp <= end_date,
        )
        .group_by(func.date(APIUsage.timestamp))
        .all()
    )

    # Create a dict with all dates
    dates = [(start_date + timedelta(days=x)).date() for x in range(31)]
    usage_dict = {date: 0 for date in dates}

    # Fill in actual usage
    for result in daily_usage:
        date, count = result
        if isinstance(date, str):
            date = datetime.fromisoformat(date).date()
        usage_dict[date] = count

    # Calculate total calls and success rate
    total_calls = db.query(APIUsage).filter(APIUsage.user_id == user.id).count()

    successful_calls = (
        db.query(APIUsage)
        .filter(APIUsage.user_id == user.id, APIUsage.is_success == True)
        .count()
    )

    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0

    # Get current month's usage for limit checking
    first_day_of_month = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    current_month_usage = (
        db.query(APIUsage)
        .filter(APIUsage.user_id == user.id, APIUsage.timestamp >= first_day_of_month)
        .count()
    )

    # Get endpoint usage breakdown
    endpoint_usage = (
        db.query(APIUsage.endpoint, func.count(APIUsage.id).label("count"))
        .filter(APIUsage.user_id == user.id)
        .group_by(APIUsage.endpoint)
        .all()
    )

    # Get usage by API key
    key_usage = (
        db.query(APIKey.name, func.count(APIUsage.id).label("count"))
        .join(APIUsage, APIUsage.api_key_id == APIKey.id)
        .filter(APIKey.user_id == user.id)
        .group_by(APIKey.name)
        .all()
    )

    return {
        "total_calls": total_calls,
        "success_rate": round(success_rate, 2),
        "dates": list(usage_dict.keys()),
        "calls": list(usage_dict.values()),
        "current_month_usage": current_month_usage,
        "monthly_limit": None if user.status == UserStatus.DONATUR else 100,
        "remaining_calls": None
        if user.status == UserStatus.DONATUR
        else max(0, 100 - current_month_usage),
        "endpoint_breakdown": dict(endpoint_usage),
        "key_usage": dict(key_usage),
    }
