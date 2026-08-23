"""训练结果到诊断图规格的稳定映射。

该模块只负责把已完成任务中的结构化表格转换为可持久化的 ChartSpecCreate，
不启动渲染进程。这样训练、存储和图形渲染仍然通过领域对象连接，前端或
后续自动化流程都可以复用同一套诊断图规格。
"""

from __future__ import annotations

from app.models import ChartSpecCreate, TrainingResult


def _spec(
    result: TrainingResult,
    name: str,
    chart_type: str,
    table_name: str,
) -> ChartSpecCreate:
    return ChartSpecCreate(
        name=name,
        chart_type=chart_type,
        dataset_id=result.dataset_id or "",
        model_run_id=result.job_id,
        options={"diagnosticTable": table_name, "source": "training_result"},
    )


def _dataset_spec(
    result: TrainingResult,
    name: str,
    chart_type: str,
    x_column: str | None = None,
    y_columns: list[str] | None = None,
) -> ChartSpecCreate:
    """Create a chart that reads the persisted dataset instead of a result table."""

    return ChartSpecCreate(
        name=name,
        chart_type=chart_type,
        dataset_id=result.dataset_id or "",
        model_run_id=result.job_id,
        x_column=x_column,
        y_columns=y_columns or [],
        options={"source": "training_dataset"},
    )


def build_diagnostic_specs(result: TrainingResult) -> list[ChartSpecCreate]:
    """根据算法结果中实际存在的表格创建诊断图规格。"""

    if result.status != "succeeded" or not result.dataset_id:
        return []
    tables = result.tables
    specs: list[ChartSpecCreate] = []
    if tables.get("confusionMatrix"):
        specs.append(_spec(result, "混淆矩阵", "confusion_matrix", "confusionMatrix"))
    if tables.get("featureImportance"):
        specs.append(_spec(result, "特征重要性", "feature_importance", "featureImportance"))
    if tables.get("residualPreview"):
        specs.append(_spec(result, "残差诊断", "residual", "residualPreview"))
        if result.target_column and result.feature_columns:
            specs.append(_dataset_spec(result, "预测值与真实值", "scatter", result.feature_columns[0], [result.target_column]))
    if tables.get("sampleAssignments"):
        specs.append(_spec(result, "聚类样本分布", "cluster_scatter", "sampleAssignments"))
        if len(result.feature_columns) >= 2:
            specs.append(_dataset_spec(result, "聚类特征相关性", "heatmap", result.feature_columns[0], result.feature_columns[:8]))
    if tables.get("anova"):
        specs.append(_spec(result, "方差分析效应", "anova_effect", "anova"))
        if result.target_column and result.feature_columns:
            specs.append(_dataset_spec(result, "因素分组箱线图", "boxplot", result.feature_columns[0], [result.target_column]))
    return specs
