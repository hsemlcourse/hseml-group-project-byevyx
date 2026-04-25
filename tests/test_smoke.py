import numpy as np
from src.preprocessing import FEATURE_COLUMNS, build_dataset


def test_build_dataset_gspc() -> None:
    df = build_dataset("^GSPC", "2020-01-01", "2024-12-31")

    assert not df.empty
    assert df.isna().sum().sum() == 0
    assert not np.isinf(df[FEATURE_COLUMNS].to_numpy()).any()

    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"missing feature {col}"
    assert "Target" in df.columns
    assert set(df["Target"].unique()).issubset({0.0, 1.0})
