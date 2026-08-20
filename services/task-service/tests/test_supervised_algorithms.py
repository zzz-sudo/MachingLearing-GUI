from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

pytest.importorskip("joblib")
pytest.importorskip("sklearn")
pytest.importorskip("xgboost")

import joblib
import numpy as np
import pandas as pd

from app.algorithm_catalog import normalize_parameters
from app.algorithm_runners.supervised import run_supervised

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "algorithms"

CLASSIFICATION_ALGORITHMS = [
    "logistic_regression",
    "decision_tree_classifier",
    "random_forest_classifier",
    "extra_trees_classifier",
    "hist_gradient_boosting_classifier",
    "xgboost_classifier",
]

REGRESSION_ALGORITHMS = [
    "linear_regression",
    "ridge_regression",
    "random_forest_regressor",
    "extra_trees_regressor",
    "hist_gradient_boosting_regressor",
    "xgboost_regressor",
]


def prepare_config(
    tmp_path: Path,
    filename: str,
    task_type: str,
    algorithm_id: str,
    target_column: str,
    feature_columns: list[str],
) -> tuple[dict[str, object], pd.DataFrame]:
    frame = pd.read_csv(FIXTURE_DIRECTORY / filename, encoding="utf-8")
    dataset_path = tmp_path / "dataset.parquet"
    frame.to_parquet(dataset_path, index=False)
    artifact_directory = tmp_path / "models" / algorithm_id
    artifact_directory.mkdir(parents=True)
    supplied: dict[str, bool | int | float | str] = {}
    if algorithm_id.startswith("xgboost"):
        supplied = {"n_estimators": 40, "max_depth": 4, "learning_rate": 0.1, "subsample": 0.9}
    elif algorithm_id.startswith(("random_forest", "extra_trees")):
        supplied = {"n_estimators": 60, "max_depth": 8}
    return (
        {
            "jobId": f"job-{algorithm_id}",
            "projectRoot": str(tmp_path),
            "datasetPath": str(dataset_path),
            "artifactDirectory": str(artifact_directory),
            "method": task_type,
            "taskType": task_type,
            "algorithmId": algorithm_id,
            "targetColumn": target_column,
            "featureColumns": feature_columns,
            "timeColumn": None,
            "groupColumn": None,
            "validationRatio": 20,
            "randomSeed": 42,
            "computeMode": "cpu",
            "parameters": normalize_parameters(algorithm_id, supplied),
        },
        frame,
    )


@pytest.mark.parametrize("algorithm_id", CLASSIFICATION_ALGORITHMS)
def test_classification_algorithms_train_and_reload(tmp_path: Path, algorithm_id: str) -> None:
    config, frame = prepare_config(
        tmp_path,
        "classification_fixture.csv",
        "classification",
        algorithm_id,
        "target_class",
        ["feature_x", "feature_y", "feature_sum", "channel"],
    )

    result = run_supervised(config)
    model_path = tmp_path / result["artifactRelativePath"]
    bundle = joblib.load(model_path)
    sample = frame[bundle["featureColumns"]].head(12)
    first_prediction = bundle["pipeline"].predict(sample)
    reloaded_prediction = joblib.load(model_path)["pipeline"].predict(sample)

    assert result["status"] == "succeeded"
    assert result["algorithmId"] == algorithm_id
    assert result["metrics"]["accuracy"] >= 0.90
    assert result["metrics"]["f1_weighted"] >= 0.90
    assert result["tables"]["confusionMatrix"]
    assert model_path.is_file()
    np.testing.assert_allclose(first_prediction, reloaded_prediction, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("algorithm_id", REGRESSION_ALGORITHMS)
def test_regression_algorithms_train_and_reload(tmp_path: Path, algorithm_id: str) -> None:
    config, frame = prepare_config(
        tmp_path,
        "regression_fixture.csv",
        "regression",
        algorithm_id,
        "target_value",
        ["feature_x", "feature_y", "region"],
    )

    result = run_supervised(config)
    model_path = tmp_path / result["artifactRelativePath"]
    bundle = joblib.load(model_path)
    sample = frame[bundle["featureColumns"]].head(12)
    first_prediction = bundle["pipeline"].predict(sample)
    reloaded_prediction = joblib.load(model_path)["pipeline"].predict(sample)

    assert result["status"] == "succeeded"
    assert result["algorithmId"] == algorithm_id
    assert result["metrics"]["r2"] >= 0.85
    assert result["metrics"]["mae"] < 4.0
    assert result["tables"]["residualPreview"]
    assert model_path.is_file()
    np.testing.assert_allclose(first_prediction, reloaded_prediction, rtol=1e-12, atol=1e-12)


def test_supervised_runner_rejects_missing_target(tmp_path: Path) -> None:
    config, _frame = prepare_config(
        tmp_path,
        "regression_fixture.csv",
        "regression",
        "random_forest_regressor",
        "missing_target",
        ["feature_x", "feature_y"],
    )

    with pytest.raises(ValueError, match="目标字段"):
        run_supervised(config)


def test_algorithm_parameters_reject_unknown_and_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="不支持参数"):
        normalize_parameters("random_forest_classifier", {"unknown": 3})
    with pytest.raises(ValueError, match="不能小于"):
        normalize_parameters("xgboost_regressor", {"learning_rate": 0.0})


def test_training_worker_cli_dispatches_supervised_algorithm(tmp_path: Path) -> None:
    config, _frame = prepare_config(
        tmp_path,
        "classification_fixture.csv",
        "classification",
        "random_forest_classifier",
        "target_class",
        ["feature_x", "feature_y", "feature_sum", "channel"],
    )
    result_path = tmp_path / "models" / "random_forest_classifier" / "result.json"
    config["resultPath"] = str(result_path)
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    worker_path = Path(__file__).parents[1] / "app" / "training_worker.py"

    process = subprocess.run(
        [sys.executable, str(worker_path), str(config_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )

    assert process.returncode == 0, process.stderr
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "succeeded"
    assert result["algorithmId"] == "random_forest_classifier"
    assert (tmp_path / result["artifactRelativePath"]).is_file()
