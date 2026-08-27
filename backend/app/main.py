from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard import router as dashboard_router
from app.api.operations import router as operations_router
from app.api.integrations import router as integrations_router
from app.api.webhooks import router as webhooks_router
from app.api.copilot import router as copilot_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "PayOps AI API"}


app.include_router(dashboard_router)
app.include_router(operations_router)
app.include_router(integrations_router)
app.include_router(webhooks_router)
app.include_router(copilot_router)
