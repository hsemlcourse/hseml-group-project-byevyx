from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.modeling import (
    DEFAULT_RANDOM_SEED,
    DEFAULT_TRAIN_END,
    DEFAULT_VAL_END,
    _predict_proba,
    evaluate_predictions,
    time_split,
)
from src.models import (
    LINEAR_FEATURES,
    TREE_FEATURES,
    build_stacking_ensemble,
    build_voting_ensemble,
    compute_scale_pos_weight,
    feature_set_for,
    get_model_factories,
)
from src.preprocessing import (
    DEFAULT_TARGET_HORIZON,
    FEATURE_COLUMNS,
    build_dataset,
    build_pooled_dataset,
)
from src.threshold import tune_threshold


@dataclass
class ExperimentResult:
    """контейнер с результатами полного прогона.

    val_metrics — таблица для подбора порога / гиперпараметров.
    test_metrics — отложенные метрики (один прогон!), close to truth.
    cv_metrics — TimeSeriesSplit-CV на train, оценка стабильности.
    tuning — результат Optuna-тюнинга XGBoost (опц.).
    """

    val_metrics: pd.DataFrame
    test_metrics: pd.DataFrame
    cv_metrics: pd.DataFrame | None
    thresholds: dict[str, float]
    fitted: dict[str, Any] = field(repr=False)
    val_proba: dict[str, np.ndarray] = field(repr=False)
    test_proba: dict[str, np.ndarray] = field(repr=False)
    splits: dict[str, pd.DataFrame] = field(repr=False)
    tuning: dict[str, Any] | None = None
    config: dict[str, Any] = field(default_factory=dict, repr=False)


def _fit_and_proba(
    model: Any,
    feats: list[str],
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
) -> tuple[Any, np.ndarray, np.ndarray]:
    """fit на train → proba на val и test (test трогаем, но НЕ используем для тюнинга)."""
    y_train = train[target_col].astype(int).to_numpy()
    model.fit(train[feats].to_numpy(), y_train)
    proba_val = _predict_proba(model, val[feats].to_numpy())
    proba_test = _predict_proba(model, test[feats].to_numpy())
    return model, proba_val, proba_test


def _load_data(
    ticker: str | list[str],
    start: str,
    end: str,
    use_cache: bool,
    target_horizon: int,
    include_macro: bool,
) -> pd.DataFrame:
    """один тикер → build_dataset; список тикеров → build_pooled_dataset."""
    if isinstance(ticker, str):
        return build_dataset(
            ticker,
            start,
            end,
            use_cache=use_cache,
            target_horizon=target_horizon,
            include_macro=include_macro,
        )
    return build_pooled_dataset(
        ticker,
        start,
        end,
        use_cache=use_cache,
        target_horizon=target_horizon,
        include_macro=include_macro,
    )


def run_experiment(
    ticker: str | list[str] = "^GSPC",
    start: str = "2010-01-01",
    end: str = "2024-12-31",
    *,
    train_end: str = DEFAULT_TRAIN_END,
    val_end: str = DEFAULT_VAL_END,
    random_state: int = DEFAULT_RANDOM_SEED,
    min_trade_freq: float = 0.15,
    use_cache: bool = True,
    run_cv: bool = True,
    cv_splits: int = 5,
    target_col: str = "Target",
    target_horizon: int = DEFAULT_TARGET_HORIZON,
    include_macro: bool = True,
    tune_xgb: bool = False,
    n_trials: int = 30,
    calibrate: bool = True,
    eval_ticker: str | None = None,
) -> ExperimentResult:
    """полный пайплайн: данные → 5 моделей → 2 ансамбля → подбор порога на val → один прогон на test.

    Args:
        ticker: один тикер или список тикеров (multi-ticker pooled training).
        target_horizon: на сколько дней вперёд предсказываем (5 по умолчанию, см. analysis §5.3).
        include_macro: добавлять ли макро-фичи (VIX, yield spread, DXY).
        tune_xgb: выполнить Optuna-тюнинг XGBoost на TimeSeriesSplit.
        n_trials: число Optuna-trials.
        calibrate: завернуть тюненый XGBoost в CalibratedClassifierCV (isotonic).
        eval_ticker: при pooled training — на каком тикере считать val/test метрики.
                     None = на всех (сводно).

    специфика временных рядов:
    - сплит strictly chronological (`time_split`), без shuffle.
    - winsorize + scaler внутри Pipeline → fit считаются на train fold, не на eval.
    - threshold tuning ТОЛЬКО на val.
    - test — отложен, прогон один раз в конце.
    - CV на train — TimeSeriesSplit (n_splits=5), 5 fold с расширяющимся окном.
    """
    df = _load_data(ticker, start, end, use_cache, target_horizon, include_macro)
    train, val, test = time_split(df, train_end=train_end, val_end=val_end)

    if train.empty or val.empty or test.empty:
        raise ValueError(f"empty split: train={len(train)}, val={len(val)}, test={len(test)}")

    # для pooled-trainа отбираем eval-тикер для метрик (test часто меряется на одном активе)
    val_eval = val
    test_eval = test
    if eval_ticker is not None and "Ticker" in df.columns:
        val_eval = val[val["Ticker"] == eval_ticker]
        test_eval = test[test["Ticker"] == eval_ticker]
        if val_eval.empty or test_eval.empty:
            raise ValueError(f"eval_ticker={eval_ticker} not found in val/test split")

    spw = compute_scale_pos_weight(train[target_col])
    factories = get_model_factories(random_state=random_state, scale_pos_weight=spw)

    fitted: dict[str, Any] = {}
    val_proba: dict[str, np.ndarray] = {}
    test_proba: dict[str, np.ndarray] = {}

    # 1. базовые модели — каждая на своём наборе фичей
    for name, factory in factories.items():
        feats = feature_set_for(name)
        model, p_val, p_test = _fit_and_proba(factory(), feats, train, val_eval, test_eval, target_col)
        fitted[name] = model
        val_proba[name] = p_val
        test_proba[name] = p_test

    # 2. ансамбли — на всех фичах (TREE_FEATURES)
    voting = build_voting_ensemble(random_state=random_state, scale_pos_weight=spw)
    voting, vp, vt = _fit_and_proba(voting, TREE_FEATURES, train, val_eval, test_eval, target_col)
    fitted["Voting"] = voting
    val_proba["Voting"] = vp
    test_proba["Voting"] = vt

    stacking = build_stacking_ensemble(random_state=random_state, scale_pos_weight=spw, n_splits=cv_splits)
    stacking, sp, st = _fit_and_proba(stacking, TREE_FEATURES, train, val_eval, test_eval, target_col)
    fitted["Stacking"] = stacking
    val_proba["Stacking"] = sp
    test_proba["Stacking"] = st

    # 2.5. опциональный Optuna-тюнинг XGBoost + калибровка
    tuning: dict[str, Any] | None = None
    if tune_xgb:
        from src.tuning import fit_calibrated_xgboost, tune_xgboost

        x_train = train[TREE_FEATURES].to_numpy()
        y_train = train[target_col].astype(int).to_numpy()
        tuning = tune_xgboost(
            x_train,
            y_train,
            n_trials=n_trials,
            n_splits=cv_splits,
            random_state=random_state,
            scale_pos_weight=spw,
            min_trade_freq=min_trade_freq,
        )

        if calibrate:
            best_model = fit_calibrated_xgboost(
                x_train,
                y_train,
                params=tuning["best_params"],
                random_state=random_state,
                scale_pos_weight=spw,
                method="isotonic",
                n_splits=cv_splits,
            )
            label = "XGBoost_tuned_calibrated"
        else:
            from src.tuning import _build_xgb

            best_model = _build_xgb(tuning["best_params"], random_state, spw)
            best_model.fit(x_train, y_train)
            label = "XGBoost_tuned"

        fitted[label] = best_model
        val_proba[label] = _predict_proba(best_model, val_eval[TREE_FEATURES].to_numpy())
        test_proba[label] = _predict_proba(best_model, test_eval[TREE_FEATURES].to_numpy())

    # 3. порог тюним на val (precision @ trade_freq >= min_trade_freq)
    y_val = val_eval[target_col].astype(int).to_numpy()
    y_test = test_eval[target_col].astype(int).to_numpy()

    thresholds: dict[str, float] = {}
    val_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []

    for name in fitted:
        tuning_th = tune_threshold(y_val, val_proba[name], min_trade_freq=min_trade_freq)
        threshold = tuning_th["threshold"]
        thresholds[name] = threshold

        m_val = evaluate_predictions(y_val, val_proba[name], threshold=threshold)
        m_test = evaluate_predictions(y_test, test_proba[name], threshold=threshold)
        val_rows.append({"model": name, "threshold": threshold, **m_val})
        test_rows.append({"model": name, "threshold": threshold, **m_test})

    val_metrics = pd.DataFrame(val_rows).set_index("model")
    test_metrics = pd.DataFrame(test_rows).set_index("model")

    # 4. опциональный CV-ран на train для оценки стабильности
    cv_metrics: pd.DataFrame | None = None
    if run_cv:
        from src.cv import cv_evaluate

        cv_metrics = cv_evaluate(factories, train, n_splits=cv_splits)

    return ExperimentResult(
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        cv_metrics=cv_metrics,
        thresholds=thresholds,
        fitted=fitted,
        val_proba=val_proba,
        test_proba=test_proba,
        splits={"train": train, "val": val_eval, "test": test_eval},
        tuning=tuning,
        config={
            "ticker": ticker,
            "target_horizon": target_horizon,
            "include_macro": include_macro,
            "tune_xgb": tune_xgb,
            "calibrate": calibrate,
            "eval_ticker": eval_ticker,
        },
    )


def comparison_table(result: ExperimentResult) -> pd.DataFrame:
    """склеивает val и test метрики side-by-side для финальной таблицы в отчёте."""
    cols = ["precision", "recall", "f1", "roc_auc", "pr_auc", "trade_freq"]
    val = result.val_metrics[cols].add_suffix("_val")
    test = result.test_metrics[cols].add_suffix("_test")
    out = pd.concat([val, test], axis=1)
    out["threshold"] = result.val_metrics["threshold"]
    out["delta_precision"] = out["precision_test"] - out["precision_val"]
    return out


__all__ = [
    "ExperimentResult",
    "FEATURE_COLUMNS",
    "LINEAR_FEATURES",
    "TREE_FEATURES",
    "comparison_table",
    "run_experiment",
]
