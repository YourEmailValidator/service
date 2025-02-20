from fastapi import Request, HTTPException, status
from datetime import datetime
from app.core.utils import check_user_limit
from app.database import get_db
from app.auth.dependencies import get_current_user_optional, verify_api_key
from app.api.models import APIKey, APIUsage

# Add list of endpoints that don't require API key verification
EXEMPT_ENDPOINTS = [
    "/api/keys",
    "/api/auth",
    "/api/docs",
    "/api/openapi.json",
]


async def log_api_requests(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        if not any(
            request.url.path.startswith(endpoint) for endpoint in EXEMPT_ENDPOINTS
        ):
            start_time = datetime.now()
            api_key = request.headers.get("X-API-Key")

            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
                )

            db = next(get_db())
            user = verify_api_key(api_key, db)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
                )

            # Check usage limits for non-exempt endpoints
            if not check_user_limit(user.id, db):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Monthly API limit reached. Please upgrade to Donatur status for unlimited access.",
                )

            response = await call_next(request)

            key_record = (
                db.query(APIKey)
                .filter(APIKey.key == api_key, APIKey.is_active == True)
                .first()
            )

            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000

            usage_log = APIUsage(
                user_id=user.id,
                api_key_id=key_record.id,
                endpoint=request.url.path,
                is_success=response.status_code < 400,
                response_time=response_time,
            )

            key_record.usage_count += 1
            db.add(usage_log)
            db.commit()

            return response

    return await call_next(request)


async def authenticate_user_middleware(request: Request, call_next):
    try:
        db = next(get_db())
        request.state.user = await get_current_user_optional(request, db)
    except Exception:
        request.state.user = None
    response = await call_next(request)
    return response
