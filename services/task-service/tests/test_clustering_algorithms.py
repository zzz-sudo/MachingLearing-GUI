from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("joblib")
pytest.importorskip("sklearn")

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

from app.algorithm_catalog import normalize_parameters
from app.algorithm_runners.clustering import run_clustering

FIXTURE = Path(__file__).parent / "fixtures" / "algorithms" / "clustering_fixture.csv"

ALGORITHMS = [
    "kmeans",
    "mini_batch_kmeans",
    "agglomerative",
    "dbscan",
    "hdbscan",
    "gaussian_mixture",
    "birch",
]


def prepare_config(tmp_path: Path, algorithm_id: str) -> tuple[dict[str, object], pd.DataFrame]:
    frame = pd.read_csv(FIXTURE, encoding="utf-8")
    dataset_path = tmp_path / "dataset.parquet"
    frame.to_parquet(dataset_path, index=False)
    artifact_directory = tmp_path / "models" / algorithm_id
    artifact_directory.mkdir(parents=True)
    supplied: dict[str, bool | int | float | str] = {}
    if algorithm_id in {"kmeans", "mini_batch_kmeans", "agglomerative", "birch"}:
        supplied = {"n_clusters": 3}
    elif algorithm_id == "gaussian_mixture":
        supplied = {"n_components": 3}
    elif algorithm_id == "dbscan":
        supplied = {"eps": 0.65, "min_samples": 5}
    elif algorithm_id == "hdbscan":
        supplied = {"min_cluster_size": 12}
    return (
        {
            "jobId": f"job-{algorithm_id}",
            "projectRoot": str(tmp_path),
            "datasetPath": str(dataset_path),
            "artifactDirectory": str(artifact_directory),
            "method": "clustering",
            "taskType": "clustering",
            "algorithmId": algorithm_id,
            "targetColumn": None,
            "featureColumns": ["feature_x", "feature_y"],
            "timeColumn": None,
            "groupColumn": None,
            "randomSeed": 42,
            "computeMode": "cpu",
            "parameters": normalize_parameters(algorithm_id, supplied),
        },
        frame,
    )


@pytest.mark.parametrize("algorithm_id", ALGORITHMS)
def test_clustering_algorithms_train_score_and_reload(tmp_path: Path, algorithm_id: str) -> None:
    config, frame = prepare_config(tmp_path, algorithm_id)

    result = run_clustering(config)
    model_path = tmp_path / result["artifactRelativePath"]
    bundle = joblib.load(model_path)
    labels = np.asarray(bundle["trainingLabels"])
    score = adjusted_rand_score(frame["expected_cluster"].to_numpy(), labels)

    assert result["status"] == "succeeded"
    assert result["algorithmId"] == algorithm_id
    assert result["metrics"]["clusters"] == 3
    assert result["metrics"]["silhouette"] > 0.70
    assert score > 0.90
    assert sum(item["count"] for item in result["tables"]["clusterSummary"]) == len(frame)
    assert bundle["featureColumns"] == ["feature_x", "feature_y"]
    assert len(labels) == len(frame)
    assert model_path.is_file()


def test_clustering_rejects_cluster_count_not_smaller_than_dataset(tmp_path: Path) -> None:
    config, _frame = prepare_config(tmp_path, "kmeans")
    config["parameters"] = {"n_clusters": 360}

    with pytest.raises(ValueError, match="小于样本数量"):
        run_clustering(config)
