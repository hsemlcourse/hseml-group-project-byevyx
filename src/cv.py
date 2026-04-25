from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.modeling import _predict_proba, evaluate_predictions
from src.models import ModelFactory, feature_set_for


def cv_evaluate(
    factories: dict[str, ModelFactory],
    df: pd.DataFrame,
    *,
    target_col: str = "Target",
    n_splits: int = 5,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """TimeSeriesSplit CV: каждой модели — свежий instance на каждом fold, без shuffle.

    NB: фичи берутся из `feature_set_for(name)` — линейные модели на 8 фичах,
    деревья на 9.
    threshold фиксированный (0.5) — оценка стабильности sortировки, а не precision при тюнинге.
    """
    y = df[target_col].astype(int)
    tscv = TimeSeriesSplit(n_splits=n_splits)

    rows = []
    for name, factory in factories.items():
        x = df[feature_set_for(name)]
        fold_metrics: list[dict[str, float]] = []
        for train_idx, val_idx in tscv.split(x):
            model = factory()
            model.fit(x.iloc[train_idx].to_numpy(), y.iloc[train_idx].to_numpy())
            proba = _predict_proba(model, x.iloc[val_idx].to_numpy())
            fold_metrics.append(evaluate_predictions(y.iloc[val_idx].to_numpy(), proba, threshold=threshold))
        agg = pd.DataFrame(fold_metrics)
        row = {"model": name, "n_splits": n_splits}
        for col in ["precision", "recall", "f1", "roc_auc", "pr_auc", "trade_freq"]:
            row[f"{col}_mean"] = float(agg[col].mean())
            row[f"{col}_std"] = float(agg[col].std(ddof=1)) if len(agg) > 1 else float("nan")
        rows.append(row)
    return pd.DataFrame(rows).set_index("model")


def fold_indices(n: int, n_splits: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
    """returns индексы folds для отладки/визуализации."""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    return list(tscv.split(np.arange(n)))
