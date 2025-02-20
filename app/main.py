from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .core.middleware import authenticate_user_middleware, log_api_requests
from .database import Base, engine
from .web.routes import router as web_router
from .api.routes import router as api_router
from .auth.routes import router as auth_router
from .services.routes import router as services_router
from fastapi.openapi.utils import get_openapi


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="YourEmailValidator API",
    version="1.0.0",
    description="API for validating emails.",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.middleware("http")(authenticate_user_middleware)
app.middleware("http")(log_api_requests)

# Include routers
app.include_router(web_router)
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(services_router)


def custom_get_openapi():
    """Generate OpenAPI schema that includes only the email validation endpoints."""
    openapi_schema = get_openapi(
        title="",
        version="",
        routes=app.routes,
    )

    # Filter only email-related endpoints
    filtered_paths = {
        "/api/v1/check-bulk-access": openapi_schema["paths"].get(
            "/api/v1/check-bulk-access"
        ),
        "/api/v1/validate-email": openapi_schema["paths"].get("/api/v1/validate-email"),
        "/api/v1/bulk-email-validate": openapi_schema["paths"].get(
            "/api/v1/bulk-email-validate"
        ),
        "/api/v1/check-disposable": openapi_schema["paths"].get(
            "/api/v1/check-disposable"
        ),
        "/api/v1/check-mx-record": openapi_schema["paths"].get(
            "/api/v1/check-mx-record"
        ),
    }

    openapi_schema["paths"] = filtered_paths
    openapi_schema["openapi"] = "3.0.0"
    return openapi_schema


app.openapi = custom_get_openapi


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
