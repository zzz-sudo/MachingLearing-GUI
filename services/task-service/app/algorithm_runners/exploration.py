from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.manifold import TSNE

from .common import artifact_relative_path, load_dataset, model_environment

EXPLORATION_ALGORITHM_IDS = {"missing_value_profile", "correlation_profile", "pca", "tsne", "truncated_svd", "umap"}


def run_exploration(config: dict[str, Any]) -> dict[str, Any]:
    frame = load_dataset(config)
    algorithm_id = str(config["algorithmId"])
    numeric = frame.select_dtypes(include=["number"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if numeric.empty:
        raise ValueError("探索或降维算法需要至少一个数值字段")
    if algorithm_id == "missing_value_profile":
        rows = [{"column": str(column), "missing": int(frame[column].isna().sum()), "missingRatio": float(frame[column].isna().mean()), "rows": int(len(frame))} for column in frame.columns]
        tables = {"missingProfile": rows}
        metrics = {"columns": float(len(frame.columns)), "rows": float(len(frame))}
    elif algorithm_id == "correlation_profile":
        corr = numeric.corr().fillna(0.0)
        rows = [{"row": str(row), "column": str(column), "correlation": float(corr.loc[row, column])} for row in corr.index for column in corr.columns]
        tables = {"correlation": rows}
        metrics = {"columns": float(len(corr.columns)), "rows": float(len(frame))}
    else:
        values = numeric.to_numpy(dtype=np.float64)
        if algorithm_id == "pca":
            reducer = PCA(n_components=min(2, values.shape[1]), random_state=int(config["randomSeed"]))
            transformed = reducer.fit_transform(values)
            metrics = {"explainedVariance": float(reducer.explained_variance_ratio_.sum())}
        elif algorithm_id == "tsne":
            if len(values) < 5:
                raise ValueError("t-SNE 至少需要 5 条记录")
            reducer = TSNE(n_components=2, random_state=int(config["randomSeed"]), perplexity=min(30.0, max(2.0, (len(values) - 1) / 3)))
            transformed = reducer.fit_transform(values)
            metrics = {"klDivergence": float(reducer.kl_divergence_)}
        elif algorithm_id == "truncated_svd":
            reducer = TruncatedSVD(n_components=min(2, max(1, values.shape[1] - 1)), random_state=int(config["randomSeed"]))
            transformed = reducer.fit_transform(values)
            metrics = {"explainedVariance": float(reducer.explained_variance_ratio_.sum())}
        else:
            try:
                import umap
            except ImportError as error:
                raise ValueError("UMAPRuntimeError: 当前训练环境未安装 umap-learn") from error
            reducer = umap.UMAP(n_components=2, random_state=int(config["randomSeed"]))
            transformed = reducer.fit_transform(values)
            metrics = {}
        tables = {"embedding": [{"rowIndex": int(index), "component1": float(row[0]), "component2": float(row[1])} for index, row in enumerate(transformed[:2000])]}
        metrics.update({"samples": float(len(values)), "features": float(values.shape[1])})

    artifact_directory = Path(config["artifactDirectory"])
    artifact = artifact_directory / "exploration.json"
    artifact.write_text(json.dumps({"algorithmId": algorithm_id, "metrics": metrics, "tables": tables}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "jobId": config["jobId"], "method": "exploration", "taskType": "exploration", "algorithmId": algorithm_id, "status": "succeeded",
        "featureColumns": list(numeric.columns), "parameters": config.get("parameters") or {}, "metrics": metrics, "tables": tables,
        "artifacts": [{"kind": "report", "relativePath": artifact_relative_path(config, artifact), "mediaType": "application/json", "description": "探索或降维结果"}],
        "artifactRelativePath": artifact_relative_path(config, artifact), "environment": model_environment(),
    }
