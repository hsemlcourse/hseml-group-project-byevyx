from __future__ import annotations

from fastapi import APIRouter

from src.api import service
from src.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    reg = service.get_registry()
    return HealthResponse(status="ok", model_loaded=bool(reg), models_count=len(reg))
