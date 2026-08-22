from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as parquet

from app.algorithm_runners.clustering import run_clustering
from app.algorithm_runners.exploration import run_exploration
from app.algorithm_runners.hypothesis import run_hypothesis
from app.algorithm_runners.supervised import run_supervised


def write_dataset(root: Path) -> Path:
    frame = pd.DataFrame(
        {
            "x": [float(index) for index in range(40)],
            "y": [float((index * 3) % 11) for index in range(40)],
            "group": ["a" if index % 2 else "b" for index in range(40)],
            "target": ["yes" if index % 3 else "no" for index in range(40)],
            "value": [float(index * 0.8 + (index % 5)) for index in range(40)],
        }
    )
    path = root / "dataset.parquet"
    parquet.write_table(__import__("pyarrow").Table.from_pandas(frame), path)
    return path


def config(root: Path, dataset: Path, algorithm_id: str, task_type: str, **values: object) -> dict[str, object]:
    artifact = root / algorithm_id
    artifact.mkdir(parents=True, exist_ok=True)
    return {
        "jobId": algorithm_id,
        "projectRoot": str(root),
        "datasetPath": str(dataset),
        "algorithmId": algorithm_id,
        "taskType": task_type,
        "randomSeed": 42,
        "computeMode": "cpu",
        "artifactDirectory": str(artifact),
        "featureColumns": ["x", "y", "group"],
        "targetColumn": "target",
        "factorColumns": ["group"],
        "parameters": {},
        **values,
    }


def test_extended_supervised_algorithms_execute(tmp_path: Path) -> None:
    dataset = write_dataset(tmp_path)
    classifiers = ["knn_classifier", "naive_bayes_classifier", "svm_classifier", "linear_discriminant_classifier", "quadratic_discriminant_classifier", "gradient_boosting_classifier"]
    regressors = ["elastic_net_regressor", "lasso_regressor", "huber_regressor", "svm_regressor", "decision_tree_regressor", "gradient_boosting_regressor", "knn_regressor", "bagging_regressor", "lightgbm_regressor", "poisson_regressor", "quantile_regressor"]
    for algorithm_id in classifiers:
        result = run_supervised(config(tmp_path, dataset, algorithm_id, "classification", targetColumn="target"))
        assert result["status"] == "succeeded", algorithm_id
    for algorithm_id in regressors:
        result = run_supervised(config(tmp_path, dataset, algorithm_id, "regression", targetColumn="value", featureColumns=["x", "y", "group"]))
        assert result["status"] == "succeeded", algorithm_id


def test_extended_clustering_and_statistics_execute(tmp_path: Path) -> None:
    dataset = write_dataset(tmp_path)
    for algorithm_id in ["optics", "spectral_clustering", "kmedoids", "fuzzy_cmeans"]:
        result = run_clustering(config(tmp_path, dataset, algorithm_id, "clustering", featureColumns=["x", "y"], parameters={"n_clusters": 3, "min_samples": 3}))
        assert result["status"] == "succeeded", algorithm_id
    one_sample = run_hypothesis(config(tmp_path, dataset, "one_sample_t_test", "hypothesis_test", targetColumn="value", parameters={"population_mean": 0}))
    paired = run_hypothesis(config(tmp_path, dataset, "paired_t_test", "hypothesis_test", targetColumn="value", featureColumns=["x"]))
    chi_square = run_hypothesis(config(tmp_path, dataset, "chi_square_test", "hypothesis_test", factorColumns=["group", "target"]))
    assert one_sample["status"] == "succeeded"
    assert paired["status"] == "succeeded"
    assert chi_square["status"] == "succeeded"


def test_reduction_and_exploration_execute(tmp_path: Path) -> None:
    dataset = write_dataset(tmp_path)
    for algorithm_id in ["pca", "tsne", "truncated_svd", "umap", "missing_value_profile", "correlation_profile"]:
        result = run_exploration(config(tmp_path, dataset, algorithm_id, "exploration", featureColumns=["x", "y"]))
        assert result["status"] == "succeeded", algorithm_id
