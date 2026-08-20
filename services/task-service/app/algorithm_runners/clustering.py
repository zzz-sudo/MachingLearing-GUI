from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.cluster import (
    AgglomerativeClustering,
    Birch,
    DBSCAN,
    HDBSCAN,
    KMeans,
    MiniBatchKMeans,
)
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture

from .common import (
    artifact_relative_path,
    build_preprocessor,
    load_dataset,
    model_environment,
    select_feature_columns,
)

CLUSTERING_ALGORITHM_IDS = {
    "kmeans",
    "mini_batch_kmeans",
    "agglomerative",
    "dbscan",
    "hdbscan",
    "gaussian_mixture",
    "birch",
}


def _build_model(
    algorithm_id: str,
    parameters: dict[str, bool | int | float | str],
    seed: int,
) -> Any:
    if algorithm_id == "kmeans":
        return KMeans(n_clusters=int(parameters["n_clusters"]), n_init="auto", random_state=seed)
    if algorithm_id == "mini_batch_kmeans":
        return MiniBatchKMeans(n_clusters=int(parameters["n_clusters"]), n_init="auto", random_state=seed, batch_size=256)
    if algorithm_id == "agglomerative":
        return AgglomerativeClustering(n_clusters=int(parameters["n_clusters"]))
    if algorithm_id == "dbscan":
        return DBSCAN(eps=float(parameters["eps"]), min_samples=int(parameters["min_samples"]), n_jobs=-1)
    if algorithm_id == "hdbscan":
        return HDBSCAN(min_cluster_size=int(parameters["min_cluster_size"]), n_jobs=-1, copy=False)
    if algorithm_id == "gaussian_mixture":
        return GaussianMixture(n_components=int(parameters["n_components"]), random_state=seed, reg_covar=1e-6)
    if algorithm_id == "birch":
        return Birch(n_clusters=int(parameters["n_clusters"]))
    raise ValueError(f"聚类 Runner 不支持算法: {algorithm_id}")


def _cluster_metrics(values: np.ndarray, labels: np.ndarray) -> tuple[dict[str, float], list[str]]:
    warnings: list[str] = []
    non_noise_mask = labels != -1
    non_noise_labels = labels[non_noise_mask]
    unique_clusters = sorted(set(int(label) for label in non_noise_labels))
    metrics = {
        "samples": float(len(values)),
        "clusters": float(len(unique_clusters)),
        "noise_samples": float(np.count_nonzero(~non_noise_mask)),
        "noise_ratio": float(np.mean(~non_noise_mask)),
    }
    evaluation_values = values[non_noise_mask]
    if 1 < len(unique_clusters) < len(evaluation_values):
        metrics.update(
            {
                "silhouette": float(silhouette_score(evaluation_values, non_noise_labels)),
                "calinski_harabasz": float(calinski_harabasz_score(evaluation_values, non_noise_labels)),
                "davies_bouldin": float(davies_bouldin_score(evaluation_values, non_noise_labels)),
            }
        )
    else:
        warnings.append("有效聚类数量不足，无法计算聚类质量指标")
    return metrics, warnings


def run_clustering(config: dict[str, Any]) -> dict[str, Any]:
    dataset = load_dataset(config)
    algorithm_id = str(config["algorithmId"])
    if len(dataset) < 3:
        raise ValueError("聚类至少需要 3 条记录")
    feature_columns = select_feature_columns(
        dataset,
        list(config.get("featureColumns") or []),
        {config.get("targetColumn"), config.get("timeColumn"), config.get("groupColumn")},
    )
    preprocessor = build_preprocessor(dataset, feature_columns)
    values = np.asarray(preprocessor.fit_transform(dataset[feature_columns]), dtype=np.float64)
    parameters = dict(config.get("parameters") or {})
    requested_clusters = parameters.get("n_clusters", parameters.get("n_components"))
    if isinstance(requested_clusters, int) and requested_clusters >= len(values):
        raise ValueError("聚类数量必须小于样本数量")
    model = _build_model(algorithm_id, parameters, int(config["randomSeed"]))
    labels = np.asarray(model.fit_predict(values), dtype=np.int64)
    metrics, warnings = _cluster_metrics(values, labels)

    counts = Counter(int(label) for label in labels)
    cluster_summary = [
        {
            "cluster": label,
            "name": "噪声" if label == -1 else f"聚类 {label + 1}",
            "count": count,
            "ratio": count / len(labels),
        }
        for label, count in sorted(counts.items())
    ]
    sample_assignments = [
        {"rowIndex": index, "cluster": int(label)}
        for index, label in enumerate(labels[:500])
    ]

    artifact_directory = Path(config["artifactDirectory"])
    artifact = artifact_directory / "model.joblib"
    supports_prediction = hasattr(model, "predict")
    joblib.dump(
        {
            "algorithmId": algorithm_id,
            "taskType": "clustering",
            "featureColumns": feature_columns,
            "preprocessor": preprocessor,
            "model": model,
            "trainingLabels": labels,
            "supportsPrediction": supports_prediction,
        },
        artifact,
    )
    relative_path = artifact_relative_path(config, artifact)
    return {
        "jobId": config["jobId"],
        "method": "clustering",
        "taskType": "clustering",
        "algorithmId": algorithm_id,
        "status": "succeeded",
        "featureColumns": feature_columns,
        "parameters": parameters,
        "metrics": metrics,
        "tables": {
            "clusterSummary": cluster_summary,
            "sampleAssignments": sample_assignments,
        },
        "artifacts": [
            {
                "kind": "model",
                "relativePath": relative_path,
                "mediaType": "application/octet-stream",
                "description": "包含预处理器、聚类模型和训练标签的可重载产物",
            }
        ],
        "warnings": warnings,
        "artifactRelativePath": relative_path,
        "environment": model_environment(),
    }
