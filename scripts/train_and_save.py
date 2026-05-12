"""Обучает модели через run_experiment() и сохраняет лучшую (или все) в models/.

Использование:
    python -m scripts.train_and_save --ticker ^GSPC --start 2010-01-01 --end 2024-12-31
    python -m scripts.train_and_save --all --metric f1
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
from src.experiments import run_experiment
from src.models import feature_set_for

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"


def _to_jsonable(d: dict) -> dict:
    """numpy/pandas скаляры → плоские float/int для json.dump."""
    out = {}
    for k, v in d.items():
        if hasattr(v, "item"):
            out[k] = v.item()
        elif isinstance(v, int | float | str | bool) or v is None:
            out[k] = v
        else:
            out[k] = float(v)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="train models and persist artifacts to models/")
    parser.add_argument("--ticker", default="^GSPC", help="один тикер для обучения (по умолчанию ^GSPC)")
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument(
        "--metric",
        default="precision",
        choices=["precision", "recall", "f1", "roc_auc", "pr_auc"],
        help="метрика для выбора лучшей модели по test_metrics",
    )
    parser.add_argument("--all", action="store_true", help="сохранить все обученные модели, а не только лучшую")
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[train] ticker={args.ticker} start={args.start} end={args.end}")
    result = run_experiment(
        ticker=args.ticker,
        start=args.start,
        end=args.end,
        run_cv=False,
    )

    best_name = str(result.test_metrics[args.metric].idxmax())
    print(f"[train] best model by test {args.metric}: {best_name}")

    names_to_save = list(result.fitted.keys()) if args.all else [best_name]

    models_meta: dict[str, dict] = {}
    for name in names_to_save:
        model = result.fitted[name]
        path = MODELS_DIR / f"{name}.joblib"
        joblib.dump(model, path)
        print(f"[train] saved {path.relative_to(PROJECT_ROOT)}")

        # feature_set_for() возвращает TREE_FEATURES для неизвестных имён (ансамбли, тюнеры),
        # что и нужно: они обучались на TREE_FEATURES в run_experiment.
        features = feature_set_for(name)
        models_meta[name] = {
            "threshold": float(result.thresholds[name]),
            "features": features,
            "val_metrics": _to_jsonable(result.val_metrics.loc[name].to_dict()),
            "test_metrics": _to_jsonable(result.test_metrics.loc[name].to_dict()),
        }

    metadata = {
        "default_model": best_name,
        "trained_at": datetime.now(UTC).isoformat(),
        "training_config": {
            "ticker": args.ticker,
            "start": args.start,
            "end": args.end,
            **result.config,
        },
        "models": models_meta,
    }

    metadata_path = MODELS_DIR / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"[train] wrote {metadata_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
