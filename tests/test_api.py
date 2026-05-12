"""Тесты API. Сеть не дёргаем: реестр и тяжёлые операции мокаем через monkeypatch."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.dummy import DummyClassifier
from src.api import service
from src.api.main import app


def _make_dummy_entry(threshold: float = 0.5) -> dict:
    clf = DummyClassifier(strategy="constant", constant=1)
    clf.fit(np.array([[0.0], [1.0]]), np.array([0, 1]))
    return {
        "model": clf,
        "threshold": threshold,
        "features": ["F1"],
        "val_metrics": {"precision": 0.6, "recall": 0.4, "f1": 0.48},
        "test_metrics": {"precision": 0.55, "recall": 0.42, "f1": 0.47},
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_registry():
    service._set_registry_for_tests({}, default=None)
    yield
    service._set_registry_for_tests({}, default=None)


def test_health_empty(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok", "model_loaded": False, "models_count": 0}


def test_health_loaded(client: TestClient) -> None:
    service._set_registry_for_tests({"Dummy": _make_dummy_entry()}, default="Dummy")
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["model_loaded"] is True
    assert body["models_count"] == 1


def test_models_endpoint(client: TestClient) -> None:
    service._set_registry_for_tests({"Dummy": _make_dummy_entry(threshold=0.42)}, default="Dummy")
    r = client.get("/models")
    assert r.status_code == 200
    body = r.json()
    assert body["default_model"] == "Dummy"
    assert len(body["models"]) == 1
    m = body["models"][0]
    assert m["name"] == "Dummy"
    assert m["threshold"] == pytest.approx(0.42)
    assert m["features_used"] == ["F1"]
    assert "precision" in m["val_metrics"]


def test_predict_model_not_found(client: TestClient) -> None:
    service._set_registry_for_tests({"Dummy": _make_dummy_entry()}, default="Dummy")
    r = client.post(
        "/predict",
        json={"ticker": "^GSPC", "date": "2024-06-03", "model_name": "Ghost"},
    )
    assert r.status_code == 404


def test_predict_empty_registry(client: TestClient) -> None:
    r = client.post("/predict", json={"ticker": "^GSPC", "date": "2024-06-03"})
    assert r.status_code == 503


def test_predict_happy(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    service._set_registry_for_tests({"Dummy": _make_dummy_entry(threshold=0.5)}, default="Dummy")

    fake_row = pd.Series({"F1": 0.7}, name=pd.Timestamp("2024-06-03"))

    def fake_features(ticker: str, target_date: date):
        return fake_row, pd.Timestamp("2024-06-03"), []

    monkeypatch.setattr(service, "compute_features_for_date", fake_features)

    r = client.post("/predict", json={"ticker": "^GSPC", "date": "2024-06-03"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ticker"] == "^GSPC"
    assert body["model"] == "Dummy"
    assert body["signal"] in (0, 1)
    assert 0.0 <= body["probability"] <= 1.0
    assert body["threshold"] == pytest.approx(0.5)
    assert body["warnings"] == []


def test_predict_invalid_payload(client: TestClient) -> None:
    r = client.post("/predict", json={"ticker": "^GSPC"})  # отсутствует date
    assert r.status_code == 422


def test_backtest_happy(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    service._set_registry_for_tests({"Dummy": _make_dummy_entry()}, default="Dummy")

    def fake_backtest(ticker, start, end, model_name, *, fee, horizon):
        idx = pd.date_range("2024-01-02", periods=3, freq="B")
        eq = pd.Series([1.0, 1.01, 1.02], index=idx)
        dd = pd.Series([0.0, 0.0, -0.005], index=idx)
        return {
            "model": "Dummy",
            "ticker": ticker,
            "cum_return": 0.02,
            "sharpe": 1.23,
            "max_drawdown": -0.005,
            "trade_freq": 0.5,
            "n_trades": 2,
            "equity_curve": service._series_to_points(eq),
            "drawdown_curve": service._series_to_points(dd),
        }

    monkeypatch.setattr(service, "backtest_one", fake_backtest)

    r = client.post(
        "/backtest",
        json={"ticker": "^GSPC", "start": "2024-01-01", "end": "2024-01-10"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cum_return"] == pytest.approx(0.02)
    assert len(body["equity_curve"]) == 3
    assert body["equity_curve"][0]["date"] == "2024-01-02"
    assert body["equity_curve"][0]["value"] == pytest.approx(1.0)


def test_backtest_bad_range(client: TestClient) -> None:
    service._set_registry_for_tests({"Dummy": _make_dummy_entry()}, default="Dummy")
    r = client.post(
        "/backtest",
        json={"ticker": "^GSPC", "start": "2024-06-01", "end": "2024-06-01"},
    )
    assert r.status_code == 422


def test_cors_headers_present(client: TestClient) -> None:
    """CORS middleware должен отдавать Access-Control-Allow-Origin на preflight."""
    r = client.options(
        "/predict",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "*"
