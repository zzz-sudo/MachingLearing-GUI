from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .common import artifact_relative_path, load_dataset, model_environment

SEQUENCE_ALGORITHM_IDS = {
    "rnn_regressor",
    "lstm_regressor",
    "gru_regressor",
    "rnn_classifier",
    "lstm_classifier",
    "gru_classifier",
}


class SequenceNetwork(nn.Module):
    def __init__(self, cell_type: str, input_size: int, hidden_size: int, num_layers: int, output_size: int) -> None:
        super().__init__()
        recurrent = {"rnn": nn.RNN, "lstm": nn.LSTM, "gru": nn.GRU}[cell_type]
        self.recurrent = recurrent(input_size, hidden_size, num_layers=num_layers, batch_first=True)
        self.output = nn.Linear(hidden_size, output_size)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        sequence_output = self.recurrent(values)[0]
        return self.output(sequence_output[:, -1, :])


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _device(compute_mode: str) -> torch.device:
    available = torch.cuda.is_available()
    if compute_mode == "gpu" and not available:
        raise ValueError("已选择 GPU，但 PyTorch 没有检测到可用 CUDA 设备")
    return torch.device("cuda" if compute_mode == "gpu" or (compute_mode == "auto" and available) else "cpu")


def _prepare_sequences(config: dict[str, Any], dataset: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], StandardScaler, LabelEncoder | None, dict[str, int]]:
    algorithm_id = str(config["algorithmId"])
    task_type = str(config["taskType"])
    target_column = str(config.get("targetColumn") or "")
    time_column = str(config.get("timeColumn") or "")
    group_column = str(config.get("groupColumn") or "")
    if not target_column or target_column not in dataset.columns:
        raise ValueError("序列算法需要选择存在于数据集中的目标字段")
    if not time_column or time_column not in dataset.columns:
        raise ValueError("序列算法需要选择存在于数据集中的时间字段")
    feature_columns = [str(value) for value in config.get("featureColumns") or []]
    if not feature_columns:
        feature_columns = [name for name in dataset.columns if name not in {target_column, time_column, group_column}]
    missing = sorted(set(feature_columns) - set(dataset.columns))
    if missing:
        raise ValueError(f"序列特征字段不存在: {', '.join(missing)}")
    if not feature_columns:
        raise ValueError("序列算法至少需要一个特征字段")
    if any(not pd.api.types.is_numeric_dtype(dataset[name]) for name in feature_columns):
        raise ValueError("序列特征字段必须全部是数值类型")

    frame = dataset.copy()
    frame["__sequence_time"] = pd.to_datetime(frame[time_column], errors="coerce")
    if frame["__sequence_time"].isna().any():
        raise ValueError("时间字段包含无法解析的值")
    frame = frame.dropna(subset=[*feature_columns, target_column]).copy()
    group_values = frame[group_column].astype(str) if group_column else pd.Series("__all__", index=frame.index)
    frame["__sequence_group"] = group_values
    frame = frame.sort_values(["__sequence_group", "__sequence_time"], kind="mergesort").reset_index(drop=True)
    parameters = config.get("parameters") or {}
    window_size = int(parameters["window_size"])
    horizon = int(parameters["horizon"])
    split_ratio = int(config.get("validationRatio", 20)) / 100
    cutoff = frame["__sequence_time"].quantile(1.0 - split_ratio)
    train_frame = frame[frame["__sequence_time"] <= cutoff]
    if train_frame.empty or len(train_frame) >= len(frame):
        raise ValueError("按时间切分后没有同时得到训练区间和测试区间")

    feature_scaler = StandardScaler()
    feature_scaler.fit(train_frame[feature_columns].to_numpy(dtype=np.float32))
    scaled_features = feature_scaler.transform(frame[feature_columns].to_numpy(dtype=np.float32))
    label_encoder: LabelEncoder | None = None
    if task_type == "sequence_classification":
        label_encoder = LabelEncoder()
        label_encoder.fit(train_frame[target_column].astype(str))
        if len(label_encoder.classes_) < 2:
            raise ValueError("序列分类目标至少需要两个训练类别")
        encoded_target = np.full(len(frame), -1, dtype=np.int64)
        train_target = frame[target_column].astype(str)
        known_mask = train_target.isin(label_encoder.classes_)
        encoded_target[known_mask.to_numpy()] = label_encoder.transform(train_target[known_mask])
    else:
        encoded_target = frame[target_column].to_numpy(dtype=np.float32)

    train_values: list[np.ndarray] = []
    train_targets: list[Any] = []
    test_values: list[np.ndarray] = []
    test_targets: list[Any] = []
    group_counts: dict[str, int] = {}
    for group_name, group_indices in frame.groupby("__sequence_group", sort=False).groups.items():
        indices = np.asarray(list(group_indices), dtype=np.int64)
        group_counts[str(group_name)] = int(len(indices))
        for end in range(window_size, len(indices) - horizon + 1):
            target_index = indices[end + horizon - 1]
            window = scaled_features[indices[end - window_size : end]]
            target_value = encoded_target[target_index]
            if isinstance(target_value, (int, np.integer)) and target_value < 0:
                continue
            if frame.iloc[target_index]["__sequence_time"] <= cutoff:
                train_values.append(window)
                train_targets.append(target_value)
            else:
                test_values.append(window)
                test_targets.append(target_value)
    if len(train_values) < 10 or len(test_values) < 5:
        raise ValueError("序列窗口数量不足，请减小窗口长度或增加数据量")
    return (
        np.asarray(train_values, dtype=np.float32),
        np.asarray(train_targets),
        np.asarray(test_values, dtype=np.float32),
        np.asarray(test_targets),
        feature_columns,
        feature_scaler,
        label_encoder,
        group_counts,
    )


def run_sequence(config: dict[str, Any]) -> dict[str, Any]:
    _seed_everything(int(config["randomSeed"]))
    dataset = load_dataset(config)
    algorithm_id = str(config["algorithmId"])
    task_type = str(config["taskType"])
    parameters = dict(config.get("parameters") or {})
    train_x, train_y, test_x, test_y, feature_columns, feature_scaler, label_encoder, group_counts = _prepare_sequences(config, dataset)
    hidden_size = int(parameters["hidden_size"])
    num_layers = int(parameters["num_layers"])
    epochs = int(parameters["epochs"])
    batch_size = int(parameters["batch_size"])
    learning_rate = float(parameters["learning_rate"])
    cell_type = algorithm_id.split("_", 1)[0]
    device = _device(str(config["computeMode"]))
    output_size = len(label_encoder.classes_) if label_encoder is not None else 1
    model = SequenceNetwork(cell_type, train_x.shape[2], hidden_size, num_layers, output_size).to(device)
    train_dataset = TensorDataset(torch.from_numpy(train_x), torch.from_numpy(train_y.astype(np.int64 if label_encoder is not None else np.float32)))
    loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn: nn.Module = nn.CrossEntropyLoss() if label_encoder is not None else nn.MSELoss()
    history: list[dict[str, float]] = []
    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad()
            output = model(batch_x)
            loss = loss_fn(output, batch_y if label_encoder is not None else batch_y.reshape(-1, 1))
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().cpu()) * len(batch_x)
        history.append({"epoch": float(epoch + 1), "loss": total_loss / len(train_dataset)})

    model.eval()
    with torch.no_grad():
        prediction = model(torch.from_numpy(test_x).to(device)).cpu().numpy()
    if label_encoder is not None:
        predicted_labels = prediction.argmax(axis=1)
        metrics = {
            "accuracy": float(accuracy_score(test_y, predicted_labels)),
            "f1_weighted": float(f1_score(test_y, predicted_labels, average="weighted", zero_division=0)),
            "samples": float(len(test_y)),
            "train_samples": float(len(train_y)),
            "test_samples": float(len(test_y)),
        }
        preview = [
            {"actual": str(label_encoder.inverse_transform([int(actual)])[0]), "predicted": str(label_encoder.inverse_transform([int(predicted)])[0])}
            for actual, predicted in zip(test_y[:200], predicted_labels[:200], strict=True)
        ]
    else:
        predicted_values = prediction.reshape(-1)
        metrics = {
            "mae": float(mean_absolute_error(test_y, predicted_values)),
            "mse": float(mean_squared_error(test_y, predicted_values)),
            "r2": float(r2_score(test_y, predicted_values)),
            "samples": float(len(test_y)),
            "train_samples": float(len(train_y)),
            "test_samples": float(len(test_y)),
        }
        preview = [
            {"actual": float(actual), "predicted": float(predicted)}
            for actual, predicted in zip(test_y[:200], predicted_values[:200], strict=True)
        ]

    artifact_directory = Path(config["artifactDirectory"])
    model_path = artifact_directory / "model.pt"
    config_path = artifact_directory / "network.json"
    checkpoint = {
        "algorithmId": algorithm_id,
        "taskType": task_type,
        "featureColumns": feature_columns,
        "targetColumn": config["targetColumn"],
        "timeColumn": config["timeColumn"],
        "groupColumn": config.get("groupColumn"),
        "inputSize": train_x.shape[2],
        "hiddenSize": hidden_size,
        "numLayers": num_layers,
        "outputSize": output_size,
        "cellType": cell_type,
        "classes": label_encoder.classes_.tolist() if label_encoder is not None else [],
        "scalerMean": feature_scaler.mean_.tolist(),
        "scalerScale": feature_scaler.scale_.tolist(),
        "stateDict": model.state_dict(),
    }
    torch.save(checkpoint, model_path)
    config_path.write_text(
        json.dumps(
            {
                "algorithmId": algorithm_id,
                "taskType": task_type,
                "featureColumns": feature_columns,
                "targetColumn": config["targetColumn"],
                "timeColumn": config["timeColumn"],
                "groupColumn": config.get("groupColumn"),
                "parameters": parameters,
                "device": str(device),
                "trainCutoff": "time-based",
                "groups": group_counts,
                "history": history,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    model_relative_path = artifact_relative_path(config, model_path)
    config_relative_path = artifact_relative_path(config, config_path)
    return {
        "jobId": config["jobId"],
        "method": task_type,
        "taskType": task_type,
        "algorithmId": algorithm_id,
        "status": "succeeded",
        "targetColumn": config["targetColumn"],
        "featureColumns": feature_columns,
        "parameters": parameters,
        "metrics": metrics,
        "tables": {"predictionPreview": preview, "lossHistory": history},
        "artifacts": [
            {"kind": "model", "relativePath": model_relative_path, "mediaType": "application/octet-stream", "description": "PyTorch 序列模型权重和结构信息"},
            {"kind": "configuration", "relativePath": config_relative_path, "mediaType": "application/json", "description": "序列字段、窗口、训练历史和设备配置"},
        ],
        "warnings": ["Scaler 只使用时间切分前的训练区间拟合", "测试窗口的目标时刻不会参与训练"],
        "artifactRelativePath": model_relative_path,
        "environment": {**model_environment(), "torch": torch.__version__, "device": str(device)},
    }
