from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class Winsorizer(BaseEstimator, TransformerMixin):
    """клиппинг хвостов по квантилям, посчитанным на train.

    fit считает квантили [lower, upper] по каждой колонке отдельно,
    transform клиппит выбросы. это убирает влияние редких экстремумов
    (Volume_ROC, Daily_Return имеют excess kurtosis 12-30) на линейные модели.
    """

    def __init__(self, lower: float = 0.01, upper: float = 0.99) -> None:
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):  # noqa: N803
        arr = np.asarray(X, dtype=float)
        self.lower_bounds_ = np.quantile(arr, self.lower, axis=0)
        self.upper_bounds_ = np.quantile(arr, self.upper, axis=0)
        return self

    def transform(self, X):  # noqa: N803
        arr = np.asarray(X, dtype=float)
        return np.clip(arr, self.lower_bounds_, self.upper_bounds_)
