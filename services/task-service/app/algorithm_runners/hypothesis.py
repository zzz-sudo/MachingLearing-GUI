from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, ttest_1samp, ttest_ind, ttest_rel

from .common import artifact_relative_path, load_dataset, model_environment

HYPOTHESIS_ALGORITHM_IDS = {"one_sample_t_test", "independent_t_test", "paired_t_test", "chi_square_test"}


def run_hypothesis(config: dict[str, Any]) -> dict[str, Any]:
    frame = load_dataset(config)
    algorithm_id = str(config["algorithmId"])
    target = str(config.get("targetColumn") or "")
    factors = [str(value) for value in config.get("factorColumns") or []]
    if algorithm_id == "chi_square_test":
        if len(factors) != 2 or any(factor not in frame.columns for factor in factors):
            raise ValueError("卡方检验必须选择两个存在的分类字段")
        table = pd.crosstab(frame[factors[0]], frame[factors[1]])
        statistic, p_value, dof, expected = chi2_contingency(table)
        rows = [{"row": str(row), "column": str(column), "count": int(table.loc[row, column])} for row in table.index for column in table.columns]
        metrics = {"statistic": float(statistic), "p_value": float(p_value), "degrees_of_freedom": float(dof), "samples": float(table.values.sum())}
        tables = {"contingency": rows}
    else:
        if not target or target not in frame.columns:
            raise ValueError("t 检验需要选择数值目标字段")
        values = frame[target].dropna().to_numpy(dtype=float)
        parameters = config.get("parameters") or {}
        if algorithm_id == "one_sample_t_test":
            statistic, p_value = ttest_1samp(values, float(parameters.get("population_mean", 0.0)))
            groups = [target]
        elif algorithm_id == "independent_t_test":
            if len(factors) != 1 or factors[0] not in frame.columns:
                raise ValueError("独立样本 t 检验需要一个分组字段")
            grouped = [group[target].dropna().to_numpy(dtype=float) for _, group in frame.groupby(factors[0])]
            if len(grouped) != 2:
                raise ValueError("独立样本 t 检验必须正好包含两个分组")
            statistic, p_value = ttest_ind(grouped[0], grouped[1], equal_var=False)
            groups = [str(value) for value in frame[factors[0]].dropna().unique()]
        else:
            pair_columns = [target, *[str(value) for value in config.get("featureColumns") or []]]
            numeric_pairs = [column for column in pair_columns if column in frame.columns and pd.api.types.is_numeric_dtype(frame[column])]
            if len(numeric_pairs) >= 2:
                paired_frame = frame[numeric_pairs[:2]].dropna()
                statistic, p_value = ttest_rel(paired_frame.iloc[:, 0], paired_frame.iloc[:, 1], nan_policy="omit")
                groups = [str(value) for value in numeric_pairs[:2]]
            elif len(factors) == 1 and factors[0] in frame.columns:
                paired = frame[[factors[0], target]].dropna().pivot(columns=factors[0], values=target)
                if paired.shape[1] != 2:
                    raise ValueError("配对样本 t 检验必须正好包含两个配对值")
                statistic, p_value = ttest_rel(paired.iloc[:, 0], paired.iloc[:, 1], nan_policy="omit")
                groups = [str(value) for value in paired.columns]
            else:
                raise ValueError("配对样本 t 检验需要目标字段和另一个数值配对字段")
        metrics = {"statistic": float(statistic), "p_value": float(p_value), "samples": float(len(values))}
        tables = {"summary": [{"target": target, "groups": ", ".join(groups), "mean": float(np.mean(values)), "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0}]}

    artifact_directory = Path(config["artifactDirectory"])
    artifact = artifact_directory / "hypothesis.json"
    artifact.write_text(json.dumps({"algorithmId": algorithm_id, "metrics": metrics, "tables": tables}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "jobId": config["jobId"], "method": "hypothesis_test", "taskType": "hypothesis_test", "algorithmId": algorithm_id,
        "status": "succeeded", "targetColumn": target or None, "featureColumns": factors, "parameters": config.get("parameters") or {},
        "metrics": metrics, "tables": tables,
        "artifacts": [{"kind": "report", "relativePath": artifact_relative_path(config, artifact), "mediaType": "application/json", "description": "假设检验统计量和 p 值"}],
        "artifactRelativePath": artifact_relative_path(config, artifact), "environment": {**model_environment(), "scipy": __import__("scipy").__version__},
    }
