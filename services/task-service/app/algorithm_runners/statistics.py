from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import levene, shapiro
from statsmodels.stats.multicomp import pairwise_tukeyhsd

from .common import artifact_relative_path, load_dataset, model_environment

ANOVA_ALGORITHM_IDS = {"one_way_anova", "factorial_anova"}
SAFE_NAME_PATTERN = re.compile(r"[^0-9a-zA-Z_]")


def _safe_names(columns: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    source_to_safe: dict[str, str] = {}
    safe_to_source: dict[str, str] = {}
    for index, source in enumerate(columns):
        candidate = SAFE_NAME_PATTERN.sub("_", source).strip("_") or f"column_{index + 1}"
        if candidate[0].isdigit():
            candidate = f"column_{candidate}"
        base = candidate
        suffix = 2
        while candidate in safe_to_source:
            candidate = f"{base}_{suffix}"
            suffix += 1
        source_to_safe[source] = candidate
        safe_to_source[candidate] = source
    return source_to_safe, safe_to_source


def _float(value: Any) -> float | None:
    return None if pd.isna(value) else float(value)


def _anova_rows(table: pd.DataFrame, safe_to_source: dict[str, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    total_sum = float(table["sum_sq"].dropna().sum())
    residual_sum = float(table.loc[table.index.astype(str).str.lower().str.contains("residual"), "sum_sq"].iloc[0]) if any(table.index.astype(str).str.lower().str.contains("residual")) else 0.0
    for term, values in table.iterrows():
        source_term = str(term)
        for safe, source in safe_to_source.items():
            source_term = source_term.replace(f"C({safe})", f"C({source})").replace(safe, source)
        sum_sq = _float(values.get("sum_sq"))
        rows.append(
            {
                "term": source_term,
                "df": _float(values.get("df")),
                "sumSq": sum_sq,
                "f": _float(values.get("F")),
                "pValue": _float(values.get("PR(>F)")),
                "etaSquared": None if not sum_sq or not total_sum else sum_sq / total_sum,
                "partialEtaSquared": None if not sum_sq or not (sum_sq + residual_sum) else sum_sq / (sum_sq + residual_sum),
            }
        )
    return rows


def _assumption_tests(frame: pd.DataFrame, target: str, factors: list[str]) -> dict[str, object]:
    grouping = frame[factors].astype(str).agg(" | ".join, axis=1)
    groups = [frame.loc[grouping == name, target].to_numpy(dtype=float) for name in grouping.unique()]
    groups = [values for values in groups if len(values) >= 2]
    output: dict[str, object] = {"groupCount": len(groups)}
    if len(groups) >= 2:
        statistic, p_value = levene(*groups, center="median")
        output["levene"] = {"statistic": float(statistic), "pValue": float(p_value)}
    if 3 <= len(frame) <= 5000:
        statistic, p_value = shapiro(frame[target].to_numpy(dtype=float))
        output["shapiro"] = {"statistic": float(statistic), "pValue": float(p_value)}
    return output


def _tukey_table(frame: pd.DataFrame, target: str, factor: str) -> list[dict[str, object]]:
    result = pairwise_tukeyhsd(endog=frame[target], groups=frame[factor].astype(str), alpha=0.05)
    rows: list[dict[str, object]] = []
    for values in result.summary().data[1:]:
        rows.append(
            {
                "groupA": str(values[0]),
                "groupB": str(values[1]),
                "meanDifference": float(values[2]),
                "pAdjusted": float(values[3]),
                "lower": float(values[4]),
                "upper": float(values[5]),
                "reject": bool(values[6]),
            }
        )
    return rows


def run_anova(config: dict[str, Any]) -> dict[str, Any]:
    dataset = load_dataset(config)
    algorithm_id = str(config["algorithmId"])
    target = str(config.get("targetColumn") or "")
    factors = [str(value) for value in config.get("factorColumns") or []]
    if not target or target not in dataset.columns:
        raise ValueError("方差分析需要选择存在于数据集中的连续目标字段")
    if not pd.api.types.is_numeric_dtype(dataset[target]):
        raise ValueError("方差分析目标字段必须是数值类型")
    if algorithm_id == "one_way_anova" and len(factors) != 1:
        raise ValueError("单因素方差分析必须选择一个因素字段")
    if algorithm_id == "factorial_anova" and len(factors) < 2:
        raise ValueError("多因素方差分析至少需要选择两个因素字段")
    missing = sorted(set(factors) - set(dataset.columns))
    if missing:
        raise ValueError(f"因素字段不存在: {', '.join(missing)}")

    selected = [target, *factors]
    frame = dataset[selected].dropna().copy()
    if len(frame) < max(20, len(factors) * 8):
        raise ValueError("有效记录数量不足，无法进行可靠的方差分析")
    source_to_safe, safe_to_source = _safe_names(selected)
    safe_frame = frame.rename(columns=source_to_safe)
    safe_target = source_to_safe[target]
    safe_factors = [source_to_safe[factor] for factor in factors]
    factor_terms = [f"C({factor})" for factor in safe_factors]
    include_interactions = bool((config.get("parameters") or {}).get("include_interactions", True))
    if algorithm_id == "one_way_anova":
        formula = f"{safe_target} ~ {factor_terms[0]}"
    elif include_interactions:
        formula = f"{safe_target} ~ {' * '.join(factor_terms)}"
    else:
        formula = f"{safe_target} ~ {' + '.join(factor_terms)}"
    model = smf.ols(formula=formula, data=safe_frame).fit()
    sum_type = str((config.get("parameters") or {}).get("sum_squares_type", "2"))
    if sum_type not in {"1", "2", "3"}:
        raise ValueError("平方和类型必须是 1、2 或 3")
    table = sm.stats.anova_lm(model, typ=int(sum_type))
    rows = _anova_rows(table, safe_to_source)
    assumptions = _assumption_tests(frame, target, factors)
    tables: dict[str, list[dict[str, object]]] = {"anova": rows}
    if algorithm_id == "one_way_anova":
        tables["tukey"] = _tukey_table(frame, target, factors[0])

    artifact_directory = Path(config["artifactDirectory"])
    artifact = artifact_directory / "anova.json"
    payload = {
        "algorithmId": algorithm_id,
        "formula": formula,
        "sourceFormula": formula,
        "targetColumn": target,
        "factorColumns": factors,
        "rows": rows,
        "assumptions": assumptions,
    }
    artifact.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    model_path = artifact_directory / "model.joblib"
    joblib.dump({"algorithmId": algorithm_id, "formula": formula, "model": model, "targetColumn": target, "factorColumns": factors}, model_path)
    relative_path = artifact_relative_path(config, artifact)
    model_relative_path = artifact_relative_path(config, model_path)
    metrics = {
        "samples": float(len(frame)),
        "r2": float(model.rsquared),
        "adj_r2": float(model.rsquared_adj),
        "f_statistic": float(model.fvalue),
        "model_p_value": float(model.f_pvalue),
    }
    return {
        "jobId": config["jobId"],
        "method": "anova",
        "taskType": "anova",
        "algorithmId": algorithm_id,
        "status": "succeeded",
        "targetColumn": target,
        "featureColumns": factors,
        "parameters": config.get("parameters") or {},
        "metrics": metrics,
        "tables": {**tables, "assumptions": [assumptions]},
        "artifacts": [
            {"kind": "report", "relativePath": relative_path, "mediaType": "application/json", "description": "ANOVA 表、效应量和假设检验结果"},
            {"kind": "model", "relativePath": model_relative_path, "mediaType": "application/octet-stream", "description": "可重新加载的 statsmodels 公式模型"},
        ],
        "artifactRelativePath": relative_path,
        "environment": {**model_environment(), "statsmodels": sm.__version__},
    }
