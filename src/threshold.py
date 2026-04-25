from __future__ import annotations

import numpy as np
from sklearn.metrics import precision_score


def tune_threshold(
    y_true,
    y_proba,
    *,
    min_trade_freq: float = 0.15,
    grid: np.ndarray | None = None,
) -> dict[str, float]:
    """находит порог, максимизирующий Precision при `trade_freq >= min_trade_freq`.

    почему так:
    - precision — наша целевая метрика (BUY-сигналы должны быть точными);
    - но если задрать порог слишком высоко, модель почти не торгует → precision на 1-2 сделках бессмыслен;
    - ограничение `trade_freq >= min_trade_freq` гарантирует, что сделок достаточно.

    тюнить порог надо ТОЛЬКО на validation, не на test (последний — отложен).
    """
    y_true = np.asarray(y_true).astype(int)
    y_proba = np.asarray(y_proba).astype(float)
    if grid is None:
        grid = np.linspace(0.30, 0.80, 51)

    best: dict[str, float] | None = None
    for threshold in grid:
        pred = (y_proba >= threshold).astype(int)
        freq = float(pred.mean())
        if freq < min_trade_freq:
            continue
        prec = precision_score(y_true, pred, zero_division=0)
        if best is None or prec > best["precision"]:
            best = {
                "threshold": float(threshold),
                "precision": float(prec),
                "trade_freq": freq,
            }

    if best is None:
        # ни один порог не дал нужной частоты — берём такой, который даёт ровно min_trade_freq
        target_pred_count = int(np.ceil(min_trade_freq * len(y_proba)))
        if target_pred_count == 0:
            return {"threshold": 0.5, "precision": float("nan"), "trade_freq": 0.0}
        cutoff = np.partition(y_proba, -target_pred_count)[-target_pred_count]
        pred = (y_proba >= cutoff).astype(int)
        return {
            "threshold": float(cutoff),
            "precision": float(precision_score(y_true, pred, zero_division=0)),
            "trade_freq": float(pred.mean()),
        }
    return best
