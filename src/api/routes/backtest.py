from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api import service
from src.api.schemas import BacktestRequest, BacktestResponse

router = APIRouter(tags=["backtest"])


@router.post("/backtest", response_model=BacktestResponse)
def backtest(req: BacktestRequest) -> BacktestResponse:
    if req.end <= req.start:
        raise HTTPException(status_code=422, detail="end must be after start")
    try:
        out = service.backtest_one(
            req.ticker,
            req.start,
            req.end,
            req.model_name,
            fee=req.fee,
            horizon=req.horizon,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"model '{req.model_name}' not found") from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"data source error: {e}") from e
    return BacktestResponse(**out)
