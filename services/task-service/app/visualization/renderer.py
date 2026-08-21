from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any


def _load_frame(config: dict[str, Any]):
    import pandas as pd

    frame = pd.read_parquet(config["datasetPath"])
    columns = set(frame.columns)
    requested = [config.get("xColumn"), *config.get("yColumns", []), config.get("groupColumn")]
    missing = sorted({column for column in requested if column and column not in columns})
    if missing:
        raise ValueError(f"ChartSpecError: 图形字段不存在: {', '.join(missing)}")
    if not config.get("yColumns"):
        raise ValueError("ChartSpecError: 至少需要一个 Y 轴字段")
    return frame


def _option(config: dict[str, Any], frame) -> dict[str, Any]:
    chart_type = config["chartType"]
    x_column = config.get("xColumn")
    y_columns = config["yColumns"]
    x_values = frame[x_column].astype(str).tolist() if x_column else [str(index) for index in frame.index]
    series: list[dict[str, Any]] = []
    for column in y_columns:
        values = frame[column].tolist()
        if chart_type == "scatter":
            data = [[x, value] for x, value in zip(x_values, values, strict=True)]
        else:
            data = values
        series.append({"name": column, "type": "bar" if chart_type == "bar" else "line" if chart_type == "line" else "scatter", "data": data, "smooth": chart_type == "line"})
    if chart_type == "histogram":
        values = frame[y_columns[0]].dropna().tolist()
        counts, edges = _histogram(values)
        x_values = [round((edges[index] + edges[index + 1]) / 2, 6) for index in range(len(counts))]
        series = [{"name": y_columns[0], "type": "bar", "data": counts}]
    return {
        "title": {"text": config["name"]},
        "tooltip": {"trigger": "axis"},
        "legend": {"show": bool(config.get("options", {}).get("showLegend", True))},
        "xAxis": {"type": "category", "data": x_values},
        "yAxis": {"type": "value"},
        "series": series,
    }


def _histogram(values: list[float], bins: int = 12) -> tuple[list[int], list[float]]:
    import numpy as np

    counts, edges = np.histogram(values, bins=bins)
    return counts.astype(int).tolist(), edges.astype(float).tolist()


def _write_html(path: Path, option: dict[str, Any]) -> None:
    option_json = json.dumps(option, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>{option['title']['text']}</title>
<style>html,body,#chart{{width:100%;height:100%;margin:0}}body{{font-family:Segoe UI,Microsoft YaHei,sans-serif}}</style>
<script src=\"https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js\"></script></head>
<body><div id=\"chart\"></div><script>const option={option_json};const chart=echarts.init(document.getElementById('chart'));chart.setOption(option);window.addEventListener('resize',()=>chart.resize());</script></body></html>"""
    path.write_text(html, encoding="utf-8")


def _render_with_pyecharts(path: Path, config: dict[str, Any], frame) -> tuple[dict[str, Any], bool]:
    try:
        from pyecharts import options as opts
        from pyecharts.charts import Bar, Line, Scatter
    except ImportError:
        return _option(config, frame), False

    chart_type = config["chartType"]
    x_column = config.get("xColumn")
    x_values = frame[x_column].astype(str).tolist() if x_column else [str(index) for index in frame.index]
    y_columns = config["yColumns"]
    if chart_type == "scatter":
        chart = Scatter().add_xaxis(x_values)
        for column in y_columns:
            chart.add_yaxis(column, [[x, value] for x, value in zip(x_values, frame[column].tolist(), strict=True)])
    elif chart_type == "bar":
        chart = Bar().add_xaxis(x_values)
        for column in y_columns:
            chart.add_yaxis(column, frame[column].tolist())
    else:
        chart = Line().add_xaxis(x_values)
        for column in y_columns:
            chart.add_yaxis(column, frame[column].tolist(), is_smooth=chart_type == "line")
    chart.set_global_opts(title_opts=opts.TitleOpts(title=config["name"]), tooltip_opts=opts.TooltipOpts(trigger="axis"))
    chart.render(str(path))
    return json.loads(chart.dump_options()), True


def _write_static(path: Path, config: dict[str, Any], frame) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)
    chart_type = config["chartType"]
    x_column = config.get("xColumn")
    y_columns = config["yColumns"]
    x_values = frame[x_column].astype(str).tolist() if x_column else list(range(len(frame)))
    if chart_type == "histogram":
        axis.hist(frame[y_columns[0]].dropna(), bins=12, color="#4e8d80")
    elif chart_type == "boxplot":
        axis.boxplot([frame[column].dropna() for column in y_columns], labels=y_columns)
    elif chart_type == "scatter":
        for column in y_columns:
            axis.scatter(x_values, frame[column], label=column, s=18)
        axis.legend()
    elif chart_type == "bar":
        axis.bar(x_values, frame[y_columns[0]], color="#4e8d80")
    else:
        for column in y_columns:
            axis.plot(x_values, frame[column], label=column)
        axis.legend()
    axis.set_title(config["name"])
    axis.set_xlabel(x_column or "index")
    axis.set_ylabel(", ".join(y_columns))
    figure.savefig(path, dpi=150)
    figure.savefig(path.with_suffix(".svg"))
    plt.close(figure)


def render_chart(config: dict[str, Any]) -> dict[str, Any]:
    frame = _load_frame(config)
    artifact_directory = Path(config["artifactDirectory"])
    artifact_directory.mkdir(parents=True, exist_ok=True)
    option = _option(config, frame)
    chart_json = artifact_directory / "chart.json"
    chart_html = artifact_directory / "chart.html"
    chart_png = artifact_directory / "chart.png"
    rendered_option, pyecharts_used = _render_with_pyecharts(chart_html, config, frame)
    chart_json.write_text(json.dumps(rendered_option, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not pyecharts_used:
        _write_html(chart_html, option)
    _write_static(chart_png, config, frame)

    warnings: list[str] = []
    if not pyecharts_used:
        warnings.append("VisualizationDependencyWarning: 未安装 pyecharts，HTML 使用兼容的 ECharts 配置模板生成")
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "renderer": "pyecharts" if pyecharts_used else "echarts-option-fallback",
    }
    return {
        "status": "succeeded",
        "chartType": config["chartType"],
        "artifacts": [
            {"kind": "chart_spec", "relativePath": "chart.json", "mediaType": "application/json", "format": "json", "description": "可恢复的 ECharts 图形配置"},
            {"kind": "chart_html", "relativePath": "chart.html", "mediaType": "text/html", "format": "html", "description": "交互式图形页面"},
            {"kind": "chart_image", "relativePath": "chart.png", "mediaType": "image/png", "format": "png", "description": "静态图形导出"},
            {"kind": "chart_image", "relativePath": "chart.svg", "mediaType": "image/svg+xml", "format": "svg", "description": "矢量图形导出"},
        ],
        "warnings": warnings,
        "environment": environment,
    }
