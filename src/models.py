from __future__ import annotations

from collections.abc import Callable

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.ensemble import (
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.modeling import _predict_proba
from src.preprocessing import ALL_FEATURE_COLUMNS, FEATURE_COLUMNS, MACRO_FEATURE_COLUMNS
from src.transformers import Winsorizer

ModelFactory = Callable[[], ClassifierMixin]

# фичи без сильно-коллинеарной Price_to_SMA20 — для линейных моделей.
# RSI_14 ↔ Bollinger_pctB ↔ Price_to_SMA20: VIF > 7 на ^GSPC (см. EDA).
# деревья и бустинги не страдают от коллинеарности → им отдаём все 9 + 5 макро.
LINEAR_FEATURES: list[str] = [c for c in FEATURE_COLUMNS if c != "Price_to_SMA20"] + MACRO_FEATURE_COLUMNS
TREE_FEATURES: list[str] = list(ALL_FEATURE_COLUMNS)


def _logreg_pipeline(random_state: int) -> Pipeline:
    """winsorize → standard scaler → logreg. винзоризация на train-квантилях."""
    return Pipeline(
        [
            ("winsorize", Winsorizer(lower=0.01, upper=0.99)),
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    C=1.0,
                    max_iter=2000,
                    class_weight="balanced",
                    solver="lbfgs",
                    random_state=random_state,
                ),
            ),
        ]
    )


def _random_forest(random_state: int) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=20,
        max_features="sqrt",
        class_weight="balanced",
        n_jobs=-1,
        random_state=random_state,
    )


def _xgboost(random_state: int, scale_pos_weight: float = 1.0) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=400,
        learning_rate=0.05,
        max_depth=5,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        tree_method="hist",
        n_jobs=-1,
        random_state=random_state,
    )


def _lightgbm(random_state: int) -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=400,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=7,
        min_data_in_leaf=50,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        bagging_freq=5,
        class_weight="balanced",
        n_jobs=-1,
        random_state=random_state,
        verbose=-1,
    )


def _mlp_pipeline(random_state: int) -> Pipeline:
    """MLP требует скейлинга. винзоризация чтобы не вылетал на хвостах."""
    return Pipeline(
        [
            ("winsorize", Winsorizer(lower=0.01, upper=0.99)),
            ("scaler", StandardScaler()),
            (
                "clf",
                MLPClassifier(
                    hidden_layer_sizes=(32, 16),
                    activation="relu",
                    solver="adam",
                    alpha=1e-3,
                    learning_rate_init=1e-3,
                    max_iter=500,
                    early_stopping=False,
                    random_state=random_state,
                ),
            ),
        ]
    )


def get_model_factories(
    *,
    random_state: int = 42,
    scale_pos_weight: float = 1.0,
) -> dict[str, ModelFactory]:
    """5 моделей разных семейств. фабрики (а не инстансы) — чтобы CV давал свежие модели на каждом fold."""
    return {
        "LogReg": lambda: _logreg_pipeline(random_state),
        "RandomForest": lambda: _random_forest(random_state),
        "XGBoost": lambda: _xgboost(random_state, scale_pos_weight=scale_pos_weight),
        "LightGBM": lambda: _lightgbm(random_state),
        "MLP": lambda: _mlp_pipeline(random_state),
    }


def feature_set_for(name: str) -> list[str]:
    """для линейных и MLP отдаём 8 фичей (без Price_to_SMA20), деревьям — все 9."""
    if name in {"LogReg", "MLP"}:
        return LINEAR_FEATURES
    return TREE_FEATURES


def compute_scale_pos_weight(y) -> float:
    """neg / pos — стандартная формула для несбалансированных бинарных задач (XGBoost)."""
    y = np.asarray(y).astype(int)
    pos = int(y.sum())
    neg = int(len(y) - pos)
    if pos == 0:
        return 1.0
    return float(neg) / float(pos)


def build_voting_ensemble(
    *,
    random_state: int = 42,
    scale_pos_weight: float = 1.0,
) -> VotingClassifier:
    """soft voting — усреднение predict_proba.

    NB: внутри voting каждая модель работает на ОДНОМ feature-наборе (передаём 9 фичей).
    LogReg/MLP здесь работают на всех 9 → коллинеарность их слегка штрафует, но через
    регуляризацию (StandardScaler + L2) это не критично, а перенос фичей-спец-логики
    в voting сильно усложнил бы код. деревья всё равно доминируют по весу.
    """
    factories = get_model_factories(random_state=random_state, scale_pos_weight=scale_pos_weight)
    return VotingClassifier(
        estimators=[(name, factory()) for name, factory in factories.items()],
        voting="soft",
        n_jobs=1,  # вложенный n_jobs у RF/XGB/LGBM
    )


class TimeSeriesStacker(BaseEstimator, ClassifierMixin):
    """stacking с TimeSeriesSplit — без утечки из будущего в метамодель.

    почему свой класс, а не sklearn.StackingClassifier:
    - sklearn использует cross_val_predict, который требует partitions (каждая точка в test
      ровно один раз). TimeSeriesSplit этому не удовлетворяет — точки до первого fold
      никогда не попадают в test → cross_val_predict падает.

    схема:
    1. на train фитим базовые на каждом fold tscv → собираем OOF-вероятности (точки до
       первого test-fold отбрасываются — у них нет честного OOF).
    2. метамодель (LogReg) обучается на OOF-вероятностях.
    3. для inference базовые модели переобучаются на ВСЕМ train.
    """

    def __init__(
        self,
        base_estimators: list[tuple[str, ClassifierMixin]],
        final_estimator: ClassifierMixin,
        n_splits: int = 5,
    ) -> None:
        self.base_estimators = base_estimators
        self.final_estimator = final_estimator
        self.n_splits = n_splits

    def fit(self, x, y):
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y).astype(int)
        n = len(x_arr)
        n_base = len(self.base_estimators)
        tscv = TimeSeriesSplit(n_splits=self.n_splits)

        oof = np.full((n, n_base), np.nan, dtype=float)
        for tr_idx, te_idx in tscv.split(x_arr):
            for j, (_, est) in enumerate(self.base_estimators):
                est_fold = clone(est)
                est_fold.fit(x_arr[tr_idx], y_arr[tr_idx])
                oof[te_idx, j] = _predict_proba(est_fold, x_arr[te_idx])

        mask = ~np.isnan(oof).any(axis=1)
        if mask.sum() < 50:
            raise ValueError(f"too few OOF samples for meta-model: {mask.sum()}")

        self.final_estimator_ = clone(self.final_estimator)
        self.final_estimator_.fit(oof[mask], y_arr[mask])

        self.fitted_base_ = []
        for name, est in self.base_estimators:
            est_full = clone(est)
            est_full.fit(x_arr, y_arr)
            self.fitted_base_.append((name, est_full))

        self.classes_ = np.array([0, 1])
        return self

    def _meta_features(self, x):
        x_arr = np.asarray(x, dtype=float)
        return np.column_stack([_predict_proba(est, x_arr) for _, est in self.fitted_base_])

    def predict_proba(self, x):
        return self.final_estimator_.predict_proba(self._meta_features(x))

    def predict(self, x):
        return self.final_estimator_.predict(self._meta_features(x))


def build_stacking_ensemble(
    *,
    random_state: int = 42,
    scale_pos_weight: float = 1.0,
    n_splits: int = 5,
) -> TimeSeriesStacker:
    """stacking c TimeSeriesSplit для OOF.

    base learners: RF + XGB + LGBM (бустинги дают разные ошибки → есть смысл усреднять).
    LogReg/MLP опускаем — на 9 коллинеарных фичах слабее, в ансамбле приоритет деревьям.
    финальная модель — LogReg на вероятностях (классическая схема).
    """
    rs = random_state
    base = [
        ("rf", _random_forest(rs)),
        ("xgb", _xgboost(rs, scale_pos_weight=scale_pos_weight)),
        ("lgbm", _lightgbm(rs)),
    ]
    final = LogisticRegression(C=1.0, max_iter=1000, random_state=rs)
    return TimeSeriesStacker(base_estimators=base, final_estimator=final, n_splits=n_splits)
