from fastapi import FastAPI

from app.config import settings
from app.controllers.reports import router as reports_router
from app.utils.logging import configure_logging


configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Downloader e processador de CSVs student_analysis do Canvas LMS.",
)

app.include_router(reports_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
