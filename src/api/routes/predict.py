from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api import service
from src.api.schemas import PredictRequest, PredictResponse

router = APIRouter(tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    try:
        out = service.predict_one(req.ticker, req.date, req.model_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"model '{req.model_name}' not found") from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:  # сетевые ошибки yfinance и прочие upstream
        raise HTTPException(status_code=502, detail=f"data source error: {e}") from e
    return PredictResponse(**out)
