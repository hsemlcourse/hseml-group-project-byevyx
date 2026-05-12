from __future__ import annotations

from fastapi import APIRouter

from src.api import service
from src.api.schemas import ModelInfo, ModelsResponse

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelsResponse)
def list_models() -> ModelsResponse:
    reg = service.get_registry()
    items = [
        ModelInfo(
            name=name,
            threshold=entry["threshold"],
            features_used=entry["features"],
            val_metrics=entry["val_metrics"],
            test_metrics=entry["test_metrics"],
        )
        for name, entry in reg.items()
    ]
    return ModelsResponse(models=items, default_model=service.get_default_model())
