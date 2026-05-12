from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import service
from src.api.routes import backtest, health, models, ohlcv, predict, tickers


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.load_registry()
    yield


app = FastAPI(
    title="Trading ML API",
    version="0.1.0",
    description="REST API для 5-дневных предсказаний направления цены акций и бэктестов.",
    lifespan=lifespan,
)

# Dev-настройка: открыто всем origin, чтобы фронт мог обращаться с любого порта.
# В проде сузить allow_origins до конкретного домена и при необходимости включить credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # обязательно False при wildcard, иначе CORS-спека запрещает
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(models.router)
app.include_router(predict.router)
app.include_router(backtest.router)
app.include_router(ohlcv.router)
app.include_router(tickers.router)
