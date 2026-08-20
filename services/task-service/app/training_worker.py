from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as parquet
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, mean_squared_error, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from algorithm_runners import (
    CLUSTERING_ALGORITHM_IDS,
    ANOVA_ALGORITHM_IDS,
    SEQUENCE_ALGORITHM_IDS,
    SUPERVISED_ALGORITHM_IDS,
    run_clustering,
    run_anova,
    run_sequence,
    run_supervised,
)


def write_result(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def numeric_matrix(frame: Any, excluded: str | None) -> tuple[np.ndarray, list[str]]:
    columns = [name for name in frame.columns if name != excluded and pd.api.types.is_numeric_dtype(frame[name])]
    if not columns:
        raise ValueError("数据集中没有可用于训练的数值特征")
    values = frame[columns].replace([np.inf, -np.inf], np.nan).fillna(0).to_numpy(dtype=np.float32)
    return values, columns


def run(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("algorithmId") in SUPERVISED_ALGORITHM_IDS:
        return run_supervised(config)
    if config.get("algorithmId") in CLUSTERING_ALGORITHM_IDS:
        return run_clustering(config)
    if config.get("algorithmId") in ANOVA_ALGORITHM_IDS:
        return run_anova(config)
    if config.get("algorithmId") in SEQUENCE_ALGORITHM_IDS:
        return run_sequence(config)

    dataset = parquet.read_table(config["datasetPath"]).to_pandas()
    method = config["method"]
    target = config.get("targetColumn")
    seed = int(config["randomSeed"])
    ratio = int(config["validationRatio"]) / 100
    artifact_directory = Path(config["artifactDirectory"])
    artifact_directory.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "jobId": config["jobId"],
        "method": method,
        "status": "succeeded",
        "targetColumn": target,
        "metrics": {},
    }

    if len(dataset) > 50000:
        dataset = dataset.sample(n=50000, random_state=seed)

    if method == "clustering":
        features, _columns = numeric_matrix(dataset, None)
        model = KMeans(n_clusters=min(3, max(2, len(features) // 100)), n_init="auto", random_state=seed)
        labels = model.fit_predict(features)
        result["metrics"] = {
            "samples": float(len(features)),
            "clusters": float(len(set(labels))),
            "silhouette": float(silhouette_score(features, labels)) if len(set(labels)) > 1 else 0.0,
        }
        artifact = artifact_directory / "model.joblib"
        joblib.dump(model, artifact)
    elif method == "anova":
        if not target or target not in dataset.columns:
            raise ValueError("方差分析需要选择分组字段")
        from scipy.stats import f_oneway

        value_columns = [name for name in dataset.columns if name != target and pd.api.types.is_numeric_dtype(dataset[name])]
        if not value_columns:
            raise ValueError("方差分析需要至少一个数值字段")
        groups = [group[value_columns[0]].dropna().to_numpy() for _, group in dataset.groupby(target) if len(group) > 1]
        statistic, p_value = f_oneway(*groups)
        result["metrics"] = {"f_statistic": float(statistic), "p_value": float(p_value), "groups": float(len(groups))}
        artifact = artifact_directory / "anova.json"
        artifact.write_text(json.dumps(result["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        if not target or target not in dataset.columns:
            raise ValueError("目标字段不存在于数据集")
        features, _columns = numeric_matrix(dataset, target)
        target_values = dataset[target].fillna(0).to_numpy()
        train_x, test_x, train_y, test_y = train_test_split(features, target_values, test_size=ratio, random_state=seed)
        if method == "classification":
            encoder = LabelEncoder()
            train_y = encoder.fit_transform(train_y.astype(str))
            test_y = encoder.transform(test_y.astype(str))
            model = RandomForestClassifier(n_estimators=120, random_state=seed, n_jobs=-1)
            model.fit(train_x, train_y)
            result["metrics"] = {"accuracy": float(accuracy_score(test_y, model.predict(test_x))), "samples": float(len(features))}
            artifact = artifact_directory / "model.joblib"
            joblib.dump({"model": model, "encoder": encoder}, artifact)
        elif method == "deep-learning":
            import torch
            from torch import nn

            use_gpu = config["computeMode"] == "gpu" or (config["computeMode"] == "auto" and torch.cuda.is_available())
            if config["computeMode"] == "gpu" and not torch.cuda.is_available():
                raise ValueError("已选择 GPU，但 PyTorch 没有检测到可用 CUDA 设备")
            device = torch.device("cuda" if use_gpu else "cpu")
            train_tensor = torch.tensor(train_x, device=device)
            target_tensor = torch.tensor(train_y.astype(np.float32), device=device).reshape(-1, 1)
            model = nn.Sequential(nn.Linear(train_x.shape[1], 32), nn.ReLU(), nn.Linear(32, 1)).to(device)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
            loss_fn = nn.MSELoss()
            for _epoch in range(40):
                optimizer.zero_grad()
                loss = loss_fn(model(train_tensor), target_tensor)
                loss.backward()
                optimizer.step()
            with torch.no_grad():
                prediction = model(torch.tensor(test_x, device=device)).cpu().numpy().reshape(-1)
            result["metrics"] = {"mae": float(mean_absolute_error(test_y, prediction)), "mse": float(mean_squared_error(test_y, prediction)), "samples": float(len(features))}
            artifact = artifact_directory / "model.pt"
            torch.save(model.state_dict(), artifact)
        else:
            model = RandomForestRegressor(n_estimators=120, random_state=seed, n_jobs=-1)
            model.fit(train_x, train_y.astype(np.float32))
            prediction = model.predict(test_x)
            result["metrics"] = {"mae": float(mean_absolute_error(test_y, prediction)), "mse": float(mean_squared_error(test_y, prediction)), "samples": float(len(features))}
            artifact = artifact_directory / "model.joblib"
            joblib.dump(model, artifact)

    result["artifactRelativePath"] = str(artifact.relative_to(config["projectRoot"])).replace("\\", "/")
    return result


def main() -> None:
    config_path = Path(sys.argv[1])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    result_path = Path(config["resultPath"])
    try:
        write_result(result_path, run(config))
    except Exception as error:
        write_result(result_path, {"jobId": config["jobId"], "method": config["method"], "taskType": config.get("taskType"), "algorithmId": config.get("algorithmId"), "status": "failed", "targetColumn": config.get("targetColumn"), "featureColumns": config.get("featureColumns", []), "parameters": config.get("parameters", {}), "errorType": type(error).__name__, "errorMessage": str(error)})
        raise


if __name__ == "__main__":
    main()
