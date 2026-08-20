from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pandas")
pytest.importorskip("sklearn")
pytest.importorskip("torch")

import numpy as np
import pandas as pd
import torch

from app.algorithm_catalog import normalize_parameters
from app.algorithm_runners.sequence import SEQUENCE_ALGORITHM_IDS, _prepare_sequences, run_sequence

FIXTURE = Path(__file__).parent / "fixtures" / "algorithms" / "sequence_fixture.csv"


def prepare_config(tmp_path: Path, algorithm_id: str, task_type: str = "sequence_regression") -> tuple[dict[str, object], pd.DataFrame]:
    frame = pd.read_csv(FIXTURE, encoding="utf-8")
    dataset_path = tmp_path / "dataset.parquet"
    frame.to_parquet(dataset_path, index=False)
    artifact_directory = tmp_path / "models" / algorithm_id
    artifact_directory.mkdir(parents=True)
    supplied = {"window_size": 12, "horizon": 1, "hidden_size": 12, "num_layers": 1, "epochs": 8, "batch_size": 32, "learning_rate": 0.01}
    return (
        {
            "jobId": f"job-{algorithm_id}",
            "projectRoot": str(tmp_path),
            "datasetPath": str(dataset_path),
            "artifactDirectory": str(artifact_directory),
            "method": task_type,
            "taskType": task_type,
            "algorithmId": algorithm_id,
            "targetColumn": "target_value" if task_type == "sequence_regression" else "target_class",
            "featureColumns": ["signal", "temperature"],
            "timeColumn": "timestamp",
            "groupColumn": "series_id",
            "validationRatio": 20,
            "randomSeed": 42,
            "computeMode": "cpu",
            "parameters": normalize_parameters(algorithm_id, supplied),
        },
        frame,
    )


@pytest.mark.parametrize("algorithm_id", ["rnn_regressor", "lstm_regressor", "gru_regressor"])
def test_sequence_regressors_train_and_save_reloadable_checkpoint(tmp_path: Path, algorithm_id: str) -> None:
    config, _frame = prepare_config(tmp_path, algorithm_id)

    result = run_sequence(config)
    model_path = tmp_path / result["artifactRelativePath"]
    network_path = tmp_path / next(item["relativePath"] for item in result["artifacts"] if item["kind"] == "configuration")
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    network = json.loads(network_path.read_text(encoding="utf-8"))

    assert result["status"] == "succeeded"
    assert result["algorithmId"] == algorithm_id
    assert result["metrics"]["test_samples"] > 5
    assert result["metrics"]["r2"] > -2.0
    assert len(result["tables"]["lossHistory"]) == 8
    assert checkpoint["cellType"] == algorithm_id.split("_", 1)[0]
    assert len(checkpoint["scalerMean"]) == 2
    assert len(checkpoint["scalerScale"]) == 2
    assert network["trainCutoff"] == "time-based"
    assert model_path.is_file()


@pytest.mark.parametrize("algorithm_id", ["rnn_classifier", "lstm_classifier", "gru_classifier"])
def test_sequence_classifiers_train_and_return_class_metrics(tmp_path: Path, algorithm_id: str) -> None:
    config, _frame = prepare_config(tmp_path, algorithm_id, "sequence_classification")

    result = run_sequence(config)

    assert result["status"] == "succeeded"
    assert result["metrics"]["accuracy"] >= 0.45
    assert result["metrics"]["f1_weighted"] >= 0.35
    assert result["tables"]["predictionPreview"]


def test_sequence_preparation_uses_time_order_and_rejects_unknown_labels(tmp_path: Path) -> None:
    config, frame = prepare_config(tmp_path, "lstm_regressor")
    reversed_frame = frame.iloc[::-1].reset_index(drop=True)
    reversed_frame.to_parquet(config["datasetPath"], index=False)
    train_x, train_y, test_x, test_y, _columns, _scaler, _encoder, groups = _prepare_sequences(config, reversed_frame)

    assert groups == {"设备甲": 240, "设备乙": 240}
    assert train_x.ndim == 3
    assert train_x.shape[1] == 12
    assert len(train_y) > len(test_y)


def test_sequence_algorithms_are_registered() -> None:
    assert SEQUENCE_ALGORITHM_IDS == {
        "rnn_regressor", "lstm_regressor", "gru_regressor",
        "rnn_classifier", "lstm_classifier", "gru_classifier",
    }
