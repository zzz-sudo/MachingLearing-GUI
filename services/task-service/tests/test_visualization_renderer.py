from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as parquet

from app.visualization.renderer import render_chart


def make_config(tmp_path: Path, chart_type: str, y_columns: list[str]) -> dict[str, object]:
    dataset = tmp_path / "dataset.parquet"
    parquet.write_table(
        pa.Table.from_pandas(
            pd.DataFrame(
                {
                    "x": list(range(20)),
                    "a": [float(value) for value in range(20)],
                    "b": [float(value * 2 + 1) for value in range(20)],
                    "c": [float((value % 4) * 3) for value in range(20)],
                }
            )
        ),
        dataset,
    )
    artifact_directory = tmp_path / chart_type
    return {
        "name": chart_type,
        "chartType": chart_type,
        "datasetPath": str(dataset),
        "xColumn": "x",
        "yColumns": y_columns,
        "options": {"showLegend": True},
        "artifactDirectory": str(artifact_directory),
    }


def test_all_manual_chart_types_render_real_artifacts(tmp_path: Path) -> None:
    for chart_type in ["line", "bar", "scatter", "histogram", "boxplot", "heatmap"]:
        result = render_chart(make_config(tmp_path, chart_type, ["a", "b"]))
        assert result["status"] == "succeeded", chart_type
        artifact_directory = tmp_path / chart_type
        assert all((artifact_directory / name).is_file() for name in ["chart.json", "chart.html", "chart.png", "chart.svg", "chart.pdf"])
        option = json.loads((artifact_directory / "chart.json").read_text(encoding="utf-8"))
        assert option["series"], chart_type
