from __future__ import annotations

from fastapi import APIRouter

from src.api import service
from src.api.schemas import TickersResponse

router = APIRouter(tags=["tickers"])


@router.get("/tickers", response_model=TickersResponse)
def tickers() -> TickersResponse:
    return TickersResponse(tickers=service.list_supported_tickers())
