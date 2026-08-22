from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import (
    BaggingRegressor,
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import ElasticNet, HuberRegressor, Lasso, LinearRegression, LogisticRegression, PoissonRegressor, QuantileRegressor, Ridge
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis

from .common import (
    artifact_relative_path,
    build_preprocessor,
    load_dataset,
    model_environment,
    select_feature_columns,
)

CLASSIFICATION_ALGORITHMS = {
    "logistic_regression",
    "decision_tree_classifier",
    "random_forest_classifier",
    "extra_trees_classifier",
    "hist_gradient_boosting_classifier",
    "xgboost_classifier",
    "knn_classifier",
    "naive_bayes_classifier",
    "svm_classifier",
    "linear_discriminant_classifier",
    "quadratic_discriminant_classifier",
    "gradient_boosting_classifier",
}

REGRESSION_ALGORITHMS = {
    "linear_regression",
    "ridge_regression",
    "random_forest_regressor",
    "extra_trees_regressor",
    "hist_gradient_boosting_regressor",
    "xgboost_regressor",
    "elastic_net_regressor",
    "lasso_regressor",
    "huber_regressor",
    "svm_regressor",
    "decision_tree_regressor",
    "gradient_boosting_regressor",
    "knn_regressor",
    "bagging_regressor",
    "lightgbm_regressor",
    "poisson_regressor",
    "quantile_regressor",
}

SUPERVISED_ALGORITHM_IDS = CLASSIFICATION_ALGORITHMS | REGRESSION_ALGORITHMS


def _gpu_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def _xgboost_device(compute_mode: str) -> str:
    available = _gpu_available()
    if compute_mode == "gpu" and not available:
        raise ValueError("已选择 GPU，但训练环境没有检测到可用 CUDA 设备")
    return "cuda" if compute_mode == "gpu" or (compute_mode == "auto" and available) else "cpu"


def _build_estimator(
    algorithm_id: str,
    parameters: dict[str, bool | int | float | str],
    seed: int,
    compute_mode: str,
) -> Any:
    if algorithm_id == "logistic_regression":
        return LogisticRegression(max_iter=2000, random_state=seed)
    if algorithm_id == "decision_tree_classifier":
        return DecisionTreeClassifier(max_depth=int(parameters["max_depth"]), random_state=seed)
    if algorithm_id == "random_forest_classifier":
        return RandomForestClassifier(n_estimators=int(parameters["n_estimators"]), max_depth=int(parameters["max_depth"]), random_state=seed, n_jobs=-1)
    if algorithm_id == "extra_trees_classifier":
        return ExtraTreesClassifier(n_estimators=int(parameters["n_estimators"]), max_depth=int(parameters["max_depth"]), random_state=seed, n_jobs=-1)
    if algorithm_id == "hist_gradient_boosting_classifier":
        return HistGradientBoostingClassifier(random_state=seed)
    if algorithm_id == "knn_classifier":
        return KNeighborsClassifier(n_neighbors=5, n_jobs=-1)
    if algorithm_id == "naive_bayes_classifier":
        from sklearn.naive_bayes import GaussianNB

        return GaussianNB()
    if algorithm_id == "svm_classifier":
        return SVC(kernel="rbf", probability=True, random_state=seed)
    if algorithm_id == "linear_discriminant_classifier":
        return LinearDiscriminantAnalysis()
    if algorithm_id == "quadratic_discriminant_classifier":
        return QuadraticDiscriminantAnalysis(reg_param=0.05)
    if algorithm_id == "gradient_boosting_classifier":
        return GradientBoostingClassifier(random_state=seed)
    if algorithm_id == "linear_regression":
        return LinearRegression(n_jobs=-1)
    if algorithm_id == "ridge_regression":
        return Ridge(alpha=float(parameters["alpha"]), random_state=seed)
    if algorithm_id == "random_forest_regressor":
        return RandomForestRegressor(n_estimators=int(parameters["n_estimators"]), max_depth=int(parameters["max_depth"]), random_state=seed, n_jobs=-1)
    if algorithm_id == "extra_trees_regressor":
        return ExtraTreesRegressor(n_estimators=int(parameters["n_estimators"]), max_depth=int(parameters["max_depth"]), random_state=seed, n_jobs=-1)
    if algorithm_id == "hist_gradient_boosting_regressor":
        return HistGradientBoostingRegressor(random_state=seed)
    if algorithm_id == "elastic_net_regressor":
        return ElasticNet(alpha=float(parameters.get("alpha", 1.0)), l1_ratio=float(parameters.get("l1_ratio", 0.5)), random_state=seed)
    if algorithm_id == "lasso_regressor":
        return Lasso(alpha=float(parameters.get("alpha", 1.0)), random_state=seed)
    if algorithm_id == "huber_regressor":
        return HuberRegressor(epsilon=float(parameters.get("epsilon", 1.35)), max_iter=2000)
    if algorithm_id == "svm_regressor":
        return SVR(kernel="rbf")
    if algorithm_id == "decision_tree_regressor":
        return DecisionTreeRegressor(max_depth=int(parameters.get("max_depth", 8)), random_state=seed)
    if algorithm_id == "gradient_boosting_regressor":
        return GradientBoostingRegressor(random_state=seed)
    if algorithm_id == "knn_regressor":
        return KNeighborsRegressor(n_neighbors=5, n_jobs=-1)
    if algorithm_id == "bagging_regressor":
        return BaggingRegressor(estimator=DecisionTreeRegressor(max_depth=8, random_state=seed), n_estimators=100, random_state=seed, n_jobs=-1)
    if algorithm_id == "lightgbm_regressor":
        import lightgbm

        return lightgbm.LGBMRegressor(n_estimators=200, learning_rate=0.05, random_state=seed, verbosity=-1, n_jobs=-1)
    if algorithm_id == "poisson_regressor":
        return PoissonRegressor(alpha=float(parameters.get("alpha", 1.0)), max_iter=2000)
    if algorithm_id == "quantile_regressor":
        return QuantileRegressor(quantile=float(parameters.get("quantile", 0.5)), alpha=float(parameters.get("alpha", 1.0)), solver="highs")
    if algorithm_id in {"xgboost_classifier", "xgboost_regressor"}:
        import xgboost

        shared = {
            "n_estimators": int(parameters["n_estimators"]),
            "max_depth": int(parameters["max_depth"]),
            "learning_rate": float(parameters["learning_rate"]),
            "subsample": float(parameters["subsample"]),
            "tree_method": "hist",
            "device": _xgboost_device(compute_mode),
            "random_state": seed,
            "n_jobs": -1,
        }
        if algorithm_id == "xgboost_classifier":
            return xgboost.XGBClassifier(**shared)
        return xgboost.XGBRegressor(objective="reg:squarederror", **shared)
    raise ValueError(f"监督学习 Runner 不支持算法: {algorithm_id}")


def _feature_importance(pipeline: Pipeline) -> list[dict[str, object]]:
    estimator = pipeline.named_steps["estimator"]
    transformed_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    values: np.ndarray | None = None
    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(estimator.feature_importances_)
    elif hasattr(estimator, "coef_"):
        coefficients = np.asarray(estimator.coef_)
        values = np.mean(np.abs(coefficients), axis=0) if coefficients.ndim > 1 else np.abs(coefficients)
    if values is None or len(values) != len(transformed_names):
        return []
    ranked = sorted(zip(transformed_names, values, strict=True), key=lambda item: float(item[1]), reverse=True)
    return [{"feature": str(name), "importance": float(value)} for name, value in ranked[:100]]


def _classification_result(
    pipeline: Pipeline,
    test_x: Any,
    test_y: np.ndarray,
    encoder: LabelEncoder,
) -> tuple[dict[str, float], dict[str, list[dict[str, object]]]]:
    prediction = pipeline.predict(test_x)
    metrics = {
        "accuracy": float(accuracy_score(test_y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(test_y, prediction)),
        "precision_weighted": float(precision_score(test_y, prediction, average="weighted", zero_division=0)),
        "recall_weighted": float(recall_score(test_y, prediction, average="weighted", zero_division=0)),
        "f1_weighted": float(f1_score(test_y, prediction, average="weighted", zero_division=0)),
    }
    if hasattr(pipeline, "predict_proba"):
        metrics["log_loss"] = float(log_loss(test_y, pipeline.predict_proba(test_x), labels=np.arange(len(encoder.classes_))))
    matrix = confusion_matrix(test_y, prediction, labels=np.arange(len(encoder.classes_)))
    confusion_rows = []
    for actual_index, actual_name in enumerate(encoder.classes_):
        for predicted_index, predicted_name in enumerate(encoder.classes_):
            confusion_rows.append(
                {
                    "actual": str(actual_name),
                    "predicted": str(predicted_name),
                    "count": int(matrix[actual_index, predicted_index]),
                }
            )
    return metrics, {"confusionMatrix": confusion_rows, "featureImportance": _feature_importance(pipeline)}


def _regression_result(
    pipeline: Pipeline,
    test_x: Any,
    test_y: np.ndarray,
) -> tuple[dict[str, float], dict[str, list[dict[str, object]]]]:
    prediction = pipeline.predict(test_x)
    mse = float(mean_squared_error(test_y, prediction))
    residual_rows = [
        {"actual": float(actual), "predicted": float(predicted), "residual": float(actual - predicted)}
        for actual, predicted in zip(test_y[:500], prediction[:500], strict=True)
    ]
    return (
        {
            "mae": float(mean_absolute_error(test_y, prediction)),
            "mse": mse,
            "rmse": math.sqrt(mse),
            "r2": float(r2_score(test_y, prediction)),
        },
        {"residualPreview": residual_rows, "featureImportance": _feature_importance(pipeline)},
    )


def run_supervised(config: dict[str, Any]) -> dict[str, Any]:
    dataset = load_dataset(config)
    algorithm_id = str(config["algorithmId"])
    task_type = str(config["taskType"])
    target_column = config.get("targetColumn")
    if not target_column or target_column not in dataset.columns:
        raise ValueError("监督学习需要选择存在于数据集中的目标字段")
    dataset = dataset.loc[dataset[target_column].notna()].copy()
    if len(dataset) < 20:
        raise ValueError("监督学习至少需要 20 条目标值有效的记录")

    feature_columns = select_feature_columns(dataset, list(config.get("featureColumns") or []), {target_column, config.get("timeColumn"), config.get("groupColumn")})
    input_frame = dataset[feature_columns]
    seed = int(config["randomSeed"])
    test_size = int(config.get("validationRatio", 20)) / 100
    encoder: LabelEncoder | None = None
    if task_type == "classification":
        encoder = LabelEncoder()
        target = encoder.fit_transform(dataset[target_column].astype(str))
        if len(encoder.classes_) < 2:
            raise ValueError("分类目标至少需要两个类别")
        counts = np.bincount(target)
        stratify = target if counts.min() >= 2 else None
    else:
        target = dataset[target_column].to_numpy(dtype=np.float64)
        stratify = None

    train_x, test_x, train_y, test_y = train_test_split(
        input_frame,
        target,
        test_size=test_size,
        random_state=seed,
        stratify=stratify,
    )
    estimator = _build_estimator(algorithm_id, dict(config.get("parameters") or {}), seed, str(config["computeMode"]))
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor(train_x, feature_columns)),
            ("estimator", estimator),
        ]
    )
    pipeline.fit(train_x, train_y)

    if task_type == "classification" and encoder is not None:
        metrics, tables = _classification_result(pipeline, test_x, test_y, encoder)
    else:
        metrics, tables = _regression_result(pipeline, test_x, test_y)
    metrics.update({"samples": float(len(dataset)), "train_samples": float(len(train_x)), "test_samples": float(len(test_x))})

    artifact_directory = Path(config["artifactDirectory"])
    artifact = artifact_directory / "model.joblib"
    joblib.dump(
        {
            "algorithmId": algorithm_id,
            "taskType": task_type,
            "featureColumns": feature_columns,
            "targetColumn": target_column,
            "pipeline": pipeline,
            "targetEncoder": encoder,
        },
        artifact,
    )
    relative_path = artifact_relative_path(config, artifact)
    environment = model_environment()
    if algorithm_id.startswith("xgboost"):
        import xgboost

        environment["xgboost"] = xgboost.__version__
    return {
        "jobId": config["jobId"],
        "method": task_type,
        "taskType": task_type,
        "algorithmId": algorithm_id,
        "status": "succeeded",
        "targetColumn": target_column,
        "featureColumns": feature_columns,
        "parameters": config.get("parameters") or {},
        "metrics": metrics,
        "tables": tables,
        "artifacts": [
            {
                "kind": "model",
                "relativePath": relative_path,
                "mediaType": "application/octet-stream",
                "description": "包含预处理、估计器和目标编码器的可重载模型",
            }
        ],
        "artifactRelativePath": relative_path,
        "environment": environment,
    }
