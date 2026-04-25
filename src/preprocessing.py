from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange, BollingerBands

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

FEATURE_COLUMNS = [
    "Daily_Return",
    "Lag_Return_1",
    "RSI_14",
    "Price_to_SMA20",
    "MACD_Histogram",
    "Bollinger_pctB",
    "ATR_14",
    "Volume_ROC",
    "Upper_Shadow_Ratio",
]

# макро-фичи: контекст рынка независимый от конкретного тикера.
# VIX — implied vol S&P 500, индикатор страха/жадности.
# Yield_Spread = 10Y − 3M, отрицательный спред (инверсия) ≈ предвестник рецессии.
# DXY — индекс доллара: рост обычно давит на акции (отток в кэш) и сырьё.
MACRO_FEATURE_COLUMNS = [
    "VIX_Level",
    "VIX_Change",
    "Yield_Spread",
    "Yield_Spread_Change",
    "DXY_Return",
]

ALL_FEATURE_COLUMNS = FEATURE_COLUMNS + MACRO_FEATURE_COLUMNS

DEFAULT_TARGET_HORIZON = 5

_MACRO_TICKERS = {
    "VIX": "^VIX",
    "TNX": "^TNX",  # 10-year treasury yield
    "IRX": "^IRX",  # 13-week treasury bill yield
    "DXY": "DX-Y.NYB",
}


def load_ohlcv(
    ticker: str,
    start: str,
    end: str,
    *,
    use_cache: bool = True,
) -> pd.DataFrame:
    """скачивает OHLCV из yfinance с локальным кэшем в data/raw/.

    ключ для кэша: ``{ticker}_{start}_{end}.csv``. Передайте ``use_cache=False`` для принудительной повторной загрузки.
    возвращает DataFrame с DatetimeIndex и столбцами Open, High, Low, Close, Volume.
    """
    safe_ticker = ticker.replace("^", "").replace("/", "_")
    cache_path = RAW_DIR / f"{safe_ticker}_{start}_{end}.csv"

    if use_cache and cache_path.exists():
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)

    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if df.empty:
        raise ValueError(f"yfinance returned no data for {ticker} {start}..{end}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index.name = "Date"

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path)
    return df


def load_macro_panel(
    start: str,
    end: str,
    *,
    use_cache: bool = True,
) -> pd.DataFrame:
    """скачивает макро-серии (VIX, 10Y, 3M, DXY) и собирает в одну панель.

    возвращает DataFrame со столбцами VIX, TNX, IRX, DXY (Close-цены).
    отсутствующие даты — forward-fill (макро публикуется не каждый день).
    """
    panel = {}
    for label, ticker in _MACRO_TICKERS.items():
        try:
            data = load_ohlcv(ticker, start, end, use_cache=use_cache)
            panel[label] = data["Close"]
        except (ValueError, KeyError) as exc:
            # если макро недоступно — продолжаем без него (будет NaN, отбросится в dropna)
            print(f"[warn] failed to load macro ticker {ticker}: {exc}")
            panel[label] = pd.Series(dtype=float)

    macro = pd.DataFrame(panel).sort_index()
    # причинно: forward-fill использует только прошлое, не будущее
    macro = macro.ffill()
    return macro


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """добавляет 9 EDA features DataFrame OHLCV. (иммутабельный метод)"""
    out = df.copy()
    close = out["Close"]
    high = out["High"]
    low = out["Low"]
    open_ = out["Open"]
    volume = out["Volume"]

    out["Daily_Return"] = close.pct_change()
    out["Lag_Return_1"] = out["Daily_Return"].shift(1)
    out["RSI_14"] = RSIIndicator(close=close, window=14).rsi()
    out["Price_to_SMA20"] = close / close.rolling(window=20).mean() - 1.0
    out["MACD_Histogram"] = MACD(close=close).macd_diff()
    out["Bollinger_pctB"] = BollingerBands(close=close, window=20, window_dev=2).bollinger_pband()
    out["ATR_14"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    prev_volume = volume.shift(1).replace(0.0, np.nan)
    out["Volume_ROC"] = (volume - prev_volume) / prev_volume

    body_top = pd.concat([open_, close], axis=1).max(axis=1)
    candle_range = (high - low).replace(0.0, np.nan)
    out["Upper_Shadow_Ratio"] = (high - body_top) / candle_range
    out["Upper_Shadow_Ratio"] = out["Upper_Shadow_Ratio"].fillna(0.0)

    return out


def add_macro_features(df: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """джойнит макро-серии и считает 5 макро-фичей.

    причинность: все фичи — pct_change/diff на текущий день, без shift(-).
    при джойне используем reindex + ffill, чтобы непраздничные дни тикера получали
    последнее доступное макро-значение.
    """
    out = df.copy()
    macro_aligned = macro.reindex(out.index).ffill()

    vix = macro_aligned.get("VIX")
    tnx = macro_aligned.get("TNX")
    irx = macro_aligned.get("IRX")
    dxy = macro_aligned.get("DXY")

    if vix is not None:
        out["VIX_Level"] = vix
        out["VIX_Change"] = vix.pct_change()
    else:
        out["VIX_Level"] = np.nan
        out["VIX_Change"] = np.nan

    if tnx is not None and irx is not None:
        spread = tnx - irx
        out["Yield_Spread"] = spread
        out["Yield_Spread_Change"] = spread.diff()
    else:
        out["Yield_Spread"] = np.nan
        out["Yield_Spread_Change"] = np.nan

    if dxy is not None:
        out["DXY_Return"] = dxy.pct_change()
    else:
        out["DXY_Return"] = np.nan

    return out


def build_target(df: pd.DataFrame, horizon: int = DEFAULT_TARGET_HORIZON) -> pd.DataFrame:
    """добавляет бинарную Target колонку: 1 если Close через `horizon` дней выше сегодня.

    horizon=1 — классический next-day направление (исходный baseline).
    horizon=5 — недельное движение, шум усредняется, тренд выживает (см. analysis.md §5.3).

    последние `horizon` строк имеют NaN target (нет данных через horizon дней).
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    out = df.copy()
    future_close = out["Close"].shift(-horizon)
    out["Target"] = (future_close > out["Close"]).astype("float")
    out.loc[future_close.isna(), "Target"] = np.nan
    return out


def build_dataset(
    ticker: str,
    start: str,
    end: str,
    *,
    use_cache: bool = True,
    target_horizon: int = DEFAULT_TARGET_HORIZON,
    include_macro: bool = True,
    macro_panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """загружает OHLCV → 9 ТА-фичей (+ 5 макро-фичей) → Target → удаляет NaN строки.

    Args:
        target_horizon: на сколько дней вперёд предсказываем направление (5 по умолчанию).
        include_macro: добавлять ли макро-фичи (VIX, yield spread, DXY).
        macro_panel: предзагруженная панель макро (для multi-ticker training, чтобы не качать 5 раз).
    """
    raw = load_ohlcv(ticker, start, end, use_cache=use_cache)
    with_features = add_features(raw)

    if include_macro:
        if macro_panel is None:
            macro_panel = load_macro_panel(start, end, use_cache=use_cache)
        with_features = add_macro_features(with_features, macro_panel)

    with_target = build_target(with_features, horizon=target_horizon)
    return with_target.dropna()


def build_pooled_dataset(
    tickers: list[str],
    start: str,
    end: str,
    *,
    use_cache: bool = True,
    target_horizon: int = DEFAULT_TARGET_HORIZON,
    include_macro: bool = True,
) -> pd.DataFrame:
    """собирает датасет по нескольким тикерам в один DataFrame с колонкой Ticker.

    multi-ticker pooled training: модель учит общие паттерны, не специфику одного актива.
    обучающая выборка увеличивается в N раз (N = число тикеров).

    причинность сохраняется: все фичи и таргет считаются ВНУТРИ одного тикера,
    потом конкатенируются. сортировка по Date важна для правильного TimeSeriesSplit.
    """
    macro = load_macro_panel(start, end, use_cache=use_cache) if include_macro else None
    parts = []
    for ticker in tickers:
        df = build_dataset(
            ticker,
            start,
            end,
            use_cache=use_cache,
            target_horizon=target_horizon,
            include_macro=include_macro,
            macro_panel=macro,
        )
        df = df.copy()
        df["Ticker"] = ticker
        parts.append(df)

    pooled = pd.concat(parts, axis=0).sort_index(kind="stable")
    return pooled
