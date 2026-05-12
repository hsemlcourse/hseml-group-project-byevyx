from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model_loaded: bool
    models_count: int


class ModelInfo(BaseModel):
    name: str
    threshold: float
    features_used: list[str]
    val_metrics: dict[str, float]
    test_metrics: dict[str, float]


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    default_model: str | None = None


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=16)
    date: date
    model_name: str | None = None


class PredictResponse(BaseModel):
    ticker: str
    date: date
    model: str
    probability: float
    signal: int
    threshold: float
    warnings: list[str] = Field(default_factory=list)


class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=16)
    start: date
    end: date
    model_name: str | None = None
    fee: float = Field(0.002, ge=0.0, le=0.1)
    horizon: int = Field(5, ge=1, le=60)


class EquityPoint(BaseModel):
    date: date
    value: float


class BacktestResponse(BaseModel):
    model: str
    ticker: str
    cum_return: float
    sharpe: float
    max_drawdown: float
    trade_freq: float
    n_trades: int
    equity_curve: list[EquityPoint]
    drawdown_curve: list[EquityPoint]


class OhlcvBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    # Technical indicators (computed server-side from the same pipeline used for prediction).
    rsi_14: float | None = None
    macd_hist: float | None = None
    bollinger_pctb: float | None = None
    sma_20: float | None = None


class OhlcvResponse(BaseModel):
    ticker: str
    start: date
    end: date
    bars: list[OhlcvBar]


class TickersResponse(BaseModel):
    tickers: list[str]
