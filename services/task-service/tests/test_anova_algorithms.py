from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("joblib")
pytest.importorskip("statsmodels")

import joblib
import numpy as np
import pandas as pd

from app.algorithm_catalog import normalize_parameters
from app.algorithm_runners.statistics import run_anova

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "algorithms"


def prepare_config(tmp_path: Path, algorithm_id: str) -> tuple[dict[str, object], pd.DataFrame]:
    filename = "anova_one_factor.csv" if algorithm_id == "one_way_anova" else "anova_multi_factor.csv"
    frame = pd.read_csv(FIXTURE_DIRECTORY / filename, encoding="utf-8")
    dataset_path = tmp_path / "dataset.parquet"
    frame.to_parquet(dataset_path, index=False)
    artifact_directory = tmp_path / "models" / algorithm_id
    artifact_directory.mkdir(parents=True)
    supplied: dict[str, bool | int | float | str] = {}
    factors = ["treatment"]
    if algorithm_id == "factorial_anova":
        factors = ["treatment", "region"]
        supplied = {"sum_squares_type": "2", "include_interactions": True}
    return (
        {
            "jobId": f"job-{algorithm_id}",
            "projectRoot": str(tmp_path),
            "datasetPath": str(dataset_path),
            "artifactDirectory": str(artifact_directory),
            "method": "anova",
            "taskType": "anova",
            "algorithmId": algorithm_id,
            "targetColumn": "score",
            "factorColumns": factors,
            "featureColumns": [],
            "randomSeed": 42,
            "computeMode": "cpu",
            "parameters": normalize_parameters(algorithm_id, supplied),
        },
        frame,
    )


@pytest.mark.parametrize("algorithm_id", ["one_way_anova", "factorial_anova"])
def test_anova_algorithms_write_tables_assumptions_and_reload(tmp_path: Path, algorithm_id: str) -> None:
    config, _frame = prepare_config(tmp_path, algorithm_id)

    result = run_anova(config)
    report_path = tmp_path / result["artifactRelativePath"]
    model_path = tmp_path / next(item["relativePath"] for item in result["artifacts"] if item["kind"] == "model")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    bundle = joblib.load(model_path)
    table = result["tables"]["anova"]

    assert result["status"] == "succeeded"
    assert report["algorithmId"] == algorithm_id
    assert table
    assert all("pValue" in row and "partialEtaSquared" in row for row in table)
    assert result["metrics"]["model_p_value"] < 0.001
    assert result["tables"]["assumptions"][0]["groupCount"] >= 2
    assert bundle["model"].rsquared > 0.4
    if algorithm_id == "one_way_anova":
        assert len(result["tables"]["tukey"]) == 6
    else:
        assert any(":" in str(row["term"]) for row in table)


def test_anova_rejects_non_numeric_target(tmp_path: Path) -> None:
    config, frame = prepare_config(tmp_path, "one_way_anova")
    frame["score"] = frame["treatment"]
    frame.to_parquet(config["datasetPath"], index=False)

    with pytest.raises(ValueError, match="数值类型"):
        run_anova(config)


def test_anova_rejects_missing_factor(tmp_path: Path) -> None:
    config, _frame = prepare_config(tmp_path, "factorial_anova")
    config["factorColumns"] = ["treatment", "missing_factor"]

    with pytest.raises(ValueError, match="因素字段不存在"):
        run_anova(config)
