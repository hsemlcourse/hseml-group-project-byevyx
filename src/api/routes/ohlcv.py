from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from src.api import service
from src.api.schemas import OhlcvResponse

router = APIRouter(tags=["ohlcv"])


@router.get("/ohlcv", response_model=OhlcvResponse)
def ohlcv(
    ticker: Annotated[str, Query(min_length=1, max_length=16)],
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
) -> OhlcvResponse:
    """OHLCV + базовые TA-индикаторы для свечного графика на фронте."""
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")
    try:
        out = service.fetch_ohlcv(ticker, start, end)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:  # сетевые ошибки yfinance и прочее
        raise HTTPException(status_code=502, detail=f"data source error: {e}") from e
    return OhlcvResponse(**out)
