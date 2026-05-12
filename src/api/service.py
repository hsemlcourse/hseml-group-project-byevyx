from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.backtest import backtest_signals
from src.modeling import _predict_proba
from src.preprocessing import add_features, build_dataset, load_ohlcv

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
METADATA_PATH = MODELS_DIR / "metadata.json"

# Достаточно для самого длинного rolling-окна (MACD ~26+9) + макро ffill + запас под праздники.
PREDICT_HISTORY_DAYS = 120

_registry: dict[str, dict[str, Any]] = {}
_default_model: str | None = None


def load_registry() -> None:
    """читает metadata.json и грузит все .joblib артефакты в память.

    идемпотентна: повторный вызов перезагружает реестр (полезно после переобучения).
    если файла нет — тихо очищает реестр (тогда /health отдаст model_loaded=False).
    """
    global _default_model
    _registry.clear()
    _default_model = None

    if not METADATA_PATH.exists():
        return

    with METADATA_PATH.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    _default_model = meta.get("default_model")

    for name, entry in meta.get("models", {}).items():
        joblib_path = MODELS_DIR / f"{name}.joblib"
        if not joblib_path.exists():
            continue
        _registry[name] = {
            "model": joblib.load(joblib_path),
            "threshold": float(entry["threshold"]),
            "features": list(entry["features"]),
            "val_metrics": {k: float(v) for k, v in entry.get("val_metrics", {}).items()},
            "test_metrics": {k: float(v) for k, v in entry.get("test_metrics", {}).items()},
        }


def get_registry() -> dict[str, dict[str, Any]]:
    return _registry


def get_default_model() -> str | None:
    if _default_model and _default_model in _registry:
        return _default_model
    return next(iter(_registry), None)


def get_model_entry(name: str | None) -> tuple[str, dict[str, Any]]:
    """резолвит имя (None → default) и возвращает (name, entry). KeyError если нет."""
    if not _registry:
        raise RuntimeError("model registry is empty — train models first (make api-train)")
    if name is None:
        name = get_default_model()
        if name is None:
            raise RuntimeError("no default model available")
    if name not in _registry:
        raise KeyError(name)
    return name, _registry[name]


def _series_to_points(s: pd.Series) -> list[dict[str, Any]]:
    """pandas Series с DatetimeIndex → [{date, value}] для JSON-ответа."""
    return [{"date": idx.date(), "value": float(v)} for idx, v in s.items()]


def compute_features_for_date(ticker: str, target_date: date) -> tuple[pd.Series, pd.Timestamp, list[str]]:
    """строит фичи через build_dataset() и возвращает последнюю строку <= target_date.

    target_horizon=1 минимизирует количество строк, отбрасываемых на хвосте (build_target
    зануляет target_horizon последних строк). сам Target колонка для инференса не нужен.

    возвращает (row, actual_date, warnings).
    """
    start = (target_date - timedelta(days=PREDICT_HISTORY_DAYS)).isoformat()
    end = (target_date + timedelta(days=1)).isoformat()  # у yfinance end exclusive

    df = build_dataset(ticker, start, end, target_horizon=1, include_macro=True)

    mask = df.index.date <= target_date
    df = df.loc[mask]
    if df.empty:
        raise ValueError(f"no feature row for {ticker} on or before {target_date}")

    row = df.iloc[-1]
    actual = df.index[-1]
    warnings: list[str] = []
    if actual.date() != target_date:
        warnings.append(f"used {actual.date().isoformat()} instead of {target_date.isoformat()} (no data)")
    return row, actual, warnings


def predict_one(ticker: str, target_date: date, model_name: str | None) -> dict[str, Any]:
    name, entry = get_model_entry(model_name)
    row, actual, warnings = compute_features_for_date(ticker, target_date)

    features = entry["features"]
    missing = [c for c in features if c not in row.index]
    if missing:
        raise ValueError(f"features missing from dataset: {missing}")

    x = row[features].to_numpy(dtype=float).reshape(1, -1)
    proba = float(_predict_proba(entry["model"], x)[0])
    threshold = entry["threshold"]
    signal = int(proba >= threshold)

    return {
        "ticker": ticker,
        "date": actual.date(),
        "model": name,
        "probability": proba,
        "signal": signal,
        "threshold": threshold,
        "warnings": warnings,
    }


DEFAULT_TICKERS: list[str] = ["^GSPC", "AAPL", "MSFT", "JPM", "XOM", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]


def list_supported_tickers() -> list[str]:
    """возвращает дефолтный набор тикеров для UI-селектора."""
    return list(DEFAULT_TICKERS)


def fetch_ohlcv(
    ticker: str,
    start: date,
    end: date,
) -> dict[str, Any]:
    """возвращает OHLCV-серию + базовые TA-индикаторы для отрисовки графика.

    индикаторы считаются той же функцией add_features(), что и для инференса —
    это гарантирует, что фронт видит ровно те значения, на которых обучалась модель.
    """
    df = load_ohlcv(ticker, start.isoformat(), end.isoformat())
    if df.empty:
        raise ValueError(f"empty ohlcv for {ticker} {start}..{end}")

    enriched = add_features(df)
    # SMA20 пригождается для наложения на свечной график.
    enriched["SMA_20"] = enriched["Close"].rolling(window=20).mean()

    bars: list[dict[str, Any]] = []
    for idx, row in enriched.iterrows():
        bars.append(
            {
                "date": idx.date(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "rsi_14": _safe_float(row.get("RSI_14")),
                "macd_hist": _safe_float(row.get("MACD_Histogram")),
                "bollinger_pctb": _safe_float(row.get("Bollinger_pctB")),
                "sma_20": _safe_float(row.get("SMA_20")),
            }
        )
    return {"ticker": ticker, "start": start, "end": end, "bars": bars}


def _safe_float(value: Any) -> float | None:
    """pandas NaN/None → None; иначе float."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN check
        return None
    return f


def backtest_one(
    ticker: str,
    start: date,
    end: date,
    model_name: str | None,
    *,
    fee: float = 0.002,
    horizon: int = 5,
) -> dict[str, Any]:
    name, entry = get_model_entry(model_name)

    df = build_dataset(
        ticker,
        start.isoformat(),
        end.isoformat(),
        target_horizon=horizon,
        include_macro=True,
    )
    if df.empty:
        raise ValueError(f"empty dataset for {ticker} {start}..{end}")

    features = entry["features"]
    proba = _predict_proba(entry["model"], df[features].to_numpy(dtype=float))
    signals = (proba >= entry["threshold"]).astype(int)

    result = backtest_signals(df, signals, fee=fee, horizon=horizon)

    return {
        "model": name,
        "ticker": ticker,
        "cum_return": float(result["cum_return"]),
        "sharpe": float(result["sharpe"]),
        "max_drawdown": float(result["max_drawdown"]),
        "trade_freq": float(result["trade_freq"]),
        "n_trades": int(result["n_trades"]),
        "equity_curve": _series_to_points(result["equity_curve"]),
        "drawdown_curve": _series_to_points(result["drawdown_curve"]),
    }


# приватные хелперы для тестов (monkeypatch удобнее, чем через настоящий load_registry)
def _set_registry_for_tests(registry: dict[str, dict[str, Any]], default: str | None = None) -> None:
    global _default_model
    _registry.clear()
    _registry.update(registry)
    _default_model = default


__all__ = [
    "DEFAULT_TICKERS",
    "MODELS_DIR",
    "METADATA_PATH",
    "PREDICT_HISTORY_DAYS",
    "backtest_one",
    "compute_features_for_date",
    "fetch_ohlcv",
    "get_default_model",
    "get_model_entry",
    "get_registry",
    "list_supported_tickers",
    "load_registry",
    "predict_one",
]
