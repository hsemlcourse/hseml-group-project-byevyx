from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.preprocessing import DEFAULT_TARGET_HORIZON, build_target, load_ohlcv

RAW_FEATURES: list[str] = ["Open", "High", "Low", "Close", "Volume"]

DEFAULT_TRAIN_END = "2021-12-31"
DEFAULT_VAL_END = "2023-12-31"
DEFAULT_THRESHOLD = 0.5
DEFAULT_RANDOM_SEED = 42

ModelFactory = Callable[[], object]


def build_raw_dataset(
    ticker: str,
    start: str,
    end: str,
    *,
    use_cache: bool = True,
    target_horizon: int = DEFAULT_TARGET_HORIZON,
) -> pd.DataFrame:
    """OHLCV + Target БЕЗ feature engineering.

    последняя строка с NaN-таргетом отбрасывается.
    """
    raw = load_ohlcv(ticker, start, end, use_cache=use_cache)
    with_target = build_target(raw, horizon=target_horizon)
    return with_target.dropna()


def time_split(
    df: pd.DataFrame,
    train_end: str = DEFAULT_TRAIN_END,
    val_end: str = DEFAULT_VAL_END,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """временной сплит train/val/test по датам (EDA раздел 7).

    границы включаются в левую часть: train ≤ train_end < val ≤ val_end < test.
    """
    train = df.loc[df.index <= train_end]
    val = df.loc[(df.index > train_end) & (df.index <= val_end)]
    test = df.loc[df.index > val_end]
    return train, val, test


def get_baseline_models(random_state: int = DEFAULT_RANDOM_SEED) -> dict[str, ModelFactory]:
    """набор стандартных baseline-моделей.

    возвращат фабрики, а не уже созданные модели — чтобы на каждом fold
    TimeSeriesSplit получать свежий экземпляр без сохранённого состояния.
    """
    return {
        "Dummy (stratified)": lambda: DummyClassifier(strategy="stratified", random_state=random_state),
        "LogReg (raw OHLCV)": lambda: Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
    }


def _predict_proba(model: object, x: np.ndarray) -> np.ndarray:
    """унифицированный score → вероятность класса 1 (для моделей без predict_proba используем sigmoid от decision_function)."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(x)[:, 1]
    if hasattr(model, "decision_function"):
        scores = model.decision_function(x)
        return 1.0 / (1.0 + np.exp(-scores))
    return model.predict(x).astype(float)


def evaluate_predictions(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, float]:
    """набор метрик для бинарной классификации направления.

    - precision/recall/f1 — при заданном пороге.
    - roc_auc / pr_auc — независимо от порога.
    - trade_freq — доля «BUY»-сигналов (контроль вырождения в `никогда не торгуем`).
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = (y_proba >= threshold).astype(int)
    has_two_classes = len(np.unique(y_true)) > 1
    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_proba) if has_two_classes else float("nan"),
        "pr_auc": average_precision_score(y_true, y_proba) if has_two_classes else float("nan"),
        "trade_freq": float(y_pred.mean()),
        "n_samples": int(len(y_true)),
    }


def fit_and_score(
    model_factory: ModelFactory,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_eval: pd.DataFrame,
    y_eval: pd.Series,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, float]:
    """fit на train → predict_proba на eval → метрики."""
    model = model_factory()
    model.fit(x_train.to_numpy(), y_train.to_numpy().astype(int))
    proba = _predict_proba(model, x_eval.to_numpy())
    return evaluate_predictions(y_eval.to_numpy(), proba, threshold=threshold)


def run_baseline_holdout(
    ticker: str,
    start: str,
    end: str,
    *,
    train_end: str = DEFAULT_TRAIN_END,
    val_end: str = DEFAULT_VAL_END,
    threshold: float = DEFAULT_THRESHOLD,
    random_state: int = DEFAULT_RANDOM_SEED,
    use_cache: bool = True,
) -> pd.DataFrame:
    """прогон всех baseline-моделей на сплите train→val.

    test-выборку не трогаем — она для финального сравнения уже подобранной модели.
    """
    df = build_raw_dataset(ticker, start, end, use_cache=use_cache)
    train, val, _ = time_split(df, train_end=train_end, val_end=val_end)
    x_train, y_train = train[RAW_FEATURES], train["Target"]
    x_val, y_val = val[RAW_FEATURES], val["Target"]

    rows = []
    for name, factory in get_baseline_models(random_state=random_state).items():
        metrics = fit_and_score(factory, x_train, y_train, x_val, y_val, threshold=threshold)
        rows.append({"model": name, **metrics})
    return pd.DataFrame(rows).set_index("model")


def run_baseline_cv(
    ticker: str,
    start: str,
    end: str,
    *,
    n_splits: int = 5,
    threshold: float = DEFAULT_THRESHOLD,
    random_state: int = DEFAULT_RANDOM_SEED,
    use_cache: bool = True,
) -> pd.DataFrame:
    """TimeSeriesSplit CV: для каждой модели возвращает mean/std по fold'ам."""
    df = build_raw_dataset(ticker, start, end, use_cache=use_cache)
    x = df[RAW_FEATURES]
    y = df["Target"]
    tscv = TimeSeriesSplit(n_splits=n_splits)

    rows = []
    for name, factory in get_baseline_models(random_state=random_state).items():
        fold_metrics: list[dict[str, float]] = []
        for train_idx, val_idx in tscv.split(x):
            metrics = fit_and_score(
                factory,
                x.iloc[train_idx],
                y.iloc[train_idx],
                x.iloc[val_idx],
                y.iloc[val_idx],
                threshold=threshold,
            )
            fold_metrics.append(metrics)
        agg = pd.DataFrame(fold_metrics)
        row = {"model": name}
        for col in ["precision", "recall", "f1", "roc_auc", "pr_auc", "trade_freq"]:
            row[f"{col}_mean"] = float(agg[col].mean())
            row[f"{col}_std"] = float(agg[col].std(ddof=1))
        rows.append(row)
    return pd.DataFrame(rows).set_index("model")
