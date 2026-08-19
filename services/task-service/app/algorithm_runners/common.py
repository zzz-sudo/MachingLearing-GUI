from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as parquet
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def load_dataset(config: dict[str, Any]) -> pd.DataFrame:
    dataset = parquet.read_table(config["datasetPath"]).to_pandas()
    if dataset.empty:
        raise ValueError("数据集为空，无法执行算法")
    return dataset


def select_feature_columns(
    dataset: pd.DataFrame,
    configured: list[str],
    excluded: set[str | None],
) -> list[str]:
    columns = configured or [name for name in dataset.columns if name not in excluded]
    missing = sorted(set(columns) - set(dataset.columns))
    if missing:
        raise ValueError(f"特征字段不存在: {', '.join(missing)}")
    if not columns:
        raise ValueError("没有可用于算法的特征字段")
    return columns


def build_preprocessor(frame: pd.DataFrame, feature_columns: list[str]) -> ColumnTransformer:
    numeric_columns = [name for name in feature_columns if pd.api.types.is_numeric_dtype(frame[name])]
    categorical_columns = [name for name in feature_columns if name not in numeric_columns]
    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical_columns,
            )
        )
    if not transformers:
        raise ValueError("没有可用于算法的数值或类别特征")
    return ColumnTransformer(transformers, verbose_feature_names_out=False)


def model_environment() -> dict[str, str]:
    import joblib
    import sklearn

    environment = {
        "python": __import__("platform").python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikitLearn": sklearn.__version__,
        "joblib": joblib.__version__,
    }
    return environment


def artifact_relative_path(config: dict[str, Any], artifact: Path) -> str:
    return str(artifact.relative_to(config["projectRoot"])).replace("\\", "/")
