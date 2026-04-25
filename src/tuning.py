from __future__ import annotations

from typing import Any

import numpy as np
import optuna
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

from src.modeling import _predict_proba
from src.threshold import tune_threshold

optuna.logging.set_verbosity(optuna.logging.WARNING)


def _build_xgb(params: dict[str, Any], random_state: int, scale_pos_weight: float) -> XGBClassifier:
    return XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=-1,
        random_state=random_state,
        scale_pos_weight=scale_pos_weight,
        **params,
    )


def _objective_factory(
    x: np.ndarray,
    y: np.ndarray,
    n_splits: int,
    random_state: int,
    scale_pos_weight: float,
    min_trade_freq: float,
):
    """строит objective-функцию для Optuna: средний Precision на TimeSeriesSplit OOF.

    для каждого fold подбираем порог на val-fold (чтобы не зависеть от единого 0.5),
    усредняем. Это и есть «честный» CV-precision.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 800, step=100),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 5.0, log=True),
        }
        precisions = []
        for tr_idx, va_idx in tscv.split(x):
            model = _build_xgb(params, random_state, scale_pos_weight)
            model.fit(x[tr_idx], y[tr_idx], verbose=False)
            proba = _predict_proba(model, x[va_idx])
            tuning = tune_threshold(y[va_idx], proba, min_trade_freq=min_trade_freq)
            prec = tuning.get("precision", 0.0)
            if not np.isnan(prec):
                precisions.append(prec)
        return float(np.mean(precisions)) if precisions else 0.0

    return objective


def tune_xgboost(
    x_train: np.ndarray,
    y_train: np.ndarray,
    *,
    n_trials: int = 50,
    n_splits: int = 5,
    random_state: int = 42,
    scale_pos_weight: float = 1.0,
    min_trade_freq: float = 0.15,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Optuna-тюнинг XGBoost на TimeSeriesSplit с целью max(Precision @ trade_freq>=min_trade_freq).

    возвращает dict с лучшими params и историей trials.
    """
    x = np.asarray(x_train, dtype=float)
    y = np.asarray(y_train).astype(int)

    sampler = optuna.samplers.TPESampler(seed=random_state)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    objective = _objective_factory(
        x=x,
        y=y,
        n_splits=n_splits,
        random_state=random_state,
        scale_pos_weight=scale_pos_weight,
        min_trade_freq=min_trade_freq,
    )
    study.optimize(objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)

    return {
        "best_params": study.best_params,
        "best_value": float(study.best_value),
        "trials": pd.DataFrame(
            [
                {
                    "trial": t.number,
                    "value": t.value,
                    **t.params,
                }
                for t in study.trials
                if t.state == optuna.trial.TrialState.COMPLETE
            ]
        ),
    }


def fit_calibrated_xgboost(
    x_train: np.ndarray,
    y_train: np.ndarray,
    *,
    params: dict[str, Any],
    random_state: int = 42,
    scale_pos_weight: float = 1.0,
    method: str = "isotonic",
    n_splits: int = 5,
) -> CalibratedClassifierCV:
    """fit XGBoost с TimeSeriesSplit-калибровкой вероятностей.

    method='isotonic' — non-parametric, сильнее, но требует данных >1k.
    method='sigmoid'  — Platt scaling, устойчивее на маленьких выборках.

    Калибратор использует ту же CV-схему (TimeSeriesSplit), что и тюнинг —
    нет утечки между fit и calibration.
    """
    base = _build_xgb(params, random_state, scale_pos_weight)
    cv = TimeSeriesSplit(n_splits=n_splits)
    calibrated = CalibratedClassifierCV(base, method=method, cv=cv)
    calibrated.fit(np.asarray(x_train, dtype=float), np.asarray(y_train).astype(int))
    return calibrated
