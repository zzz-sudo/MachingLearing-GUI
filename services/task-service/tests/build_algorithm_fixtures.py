from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Iterable

OUTPUT_DIRECTORY = Path(__file__).parent / "fixtures" / "algorithms"
RANDOM_SEED = 20260819


def write_csv(filename: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> int:
    output_path = OUTPUT_DIRECTORY / filename
    materialized = list(rows)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def build_classification(random_source: random.Random) -> int:
    rows: list[dict[str, object]] = []
    centers = [(-3.0, -1.5, "零售"), (0.5, 3.0, "企业"), (3.5, -1.0, "线上")]
    for class_id, (center_x, center_y, channel) in enumerate(centers):
        for _index in range(80):
            feature_x = random_source.gauss(center_x, 0.75)
            feature_y = random_source.gauss(center_y, 0.85)
            rows.append(
                {
                    "feature_x": f"{feature_x:.6f}",
                    "feature_y": f"{feature_y:.6f}",
                    "feature_sum": f"{feature_x + feature_y:.6f}",
                    "channel": channel,
                    "target_class": f"类别{class_id + 1}",
                }
            )
    random_source.shuffle(rows)
    return write_csv(
        "classification_fixture.csv",
        ["feature_x", "feature_y", "feature_sum", "channel", "target_class"],
        rows,
    )


def build_regression(random_source: random.Random) -> int:
    rows: list[dict[str, object]] = []
    region_effects = {"华东": 4.0, "华南": -1.5, "华北": 2.0}
    for index in range(320):
        feature_x = random_source.uniform(-8.0, 8.0)
        feature_y = random_source.uniform(-5.0, 5.0)
        region = list(region_effects)[index % len(region_effects)]
        target = 3.2 * feature_x - 1.7 * feature_y + region_effects[region] + random_source.gauss(0.0, 0.8)
        rows.append(
            {
                "feature_x": f"{feature_x:.6f}",
                "feature_y": f"{feature_y:.6f}",
                "region": region,
                "target_value": f"{target:.6f}",
            }
        )
    return write_csv(
        "regression_fixture.csv",
        ["feature_x", "feature_y", "region", "target_value"],
        rows,
    )


def build_clustering(random_source: random.Random) -> int:
    rows: list[dict[str, object]] = []
    centers = [(-5.0, -4.0), (0.0, 5.0), (5.0, -2.0)]
    for cluster_id, (center_x, center_y) in enumerate(centers):
        for _index in range(120):
            feature_x = random_source.gauss(center_x, 0.6)
            feature_y = random_source.gauss(center_y, 0.6)
            rows.append(
                {
                    "feature_x": f"{feature_x:.6f}",
                    "feature_y": f"{feature_y:.6f}",
                    "radius": f"{math.hypot(feature_x, feature_y):.6f}",
                    "expected_cluster": cluster_id,
                }
            )
    random_source.shuffle(rows)
    return write_csv(
        "clustering_fixture.csv",
        ["feature_x", "feature_y", "radius", "expected_cluster"],
        rows,
    )


def build_one_factor_anova(random_source: random.Random) -> int:
    rows: list[dict[str, object]] = []
    means = {"对照组": 10.0, "方案甲": 12.5, "方案乙": 15.0, "方案丙": 18.0}
    for group, mean in means.items():
        for _index in range(30):
            rows.append({"treatment": group, "score": f"{random_source.gauss(mean, 1.1):.6f}"})
    return write_csv("anova_one_factor.csv", ["treatment", "score"], rows)


def build_multi_factor_anova(random_source: random.Random) -> int:
    rows: list[dict[str, object]] = []
    treatment_effects = {"对照": 0.0, "方法甲": 3.0, "方法乙": 6.0}
    region_effects = {"北区": 0.0, "南区": 2.5}
    for treatment, treatment_effect in treatment_effects.items():
        for region, region_effect in region_effects.items():
            interaction = 3.5 if treatment == "方法甲" and region == "南区" else 0.0
            for replicate in range(40):
                score = 20.0 + treatment_effect + region_effect + interaction + random_source.gauss(0.0, 1.4)
                rows.append(
                    {
                        "treatment": treatment,
                        "region": region,
                        "replicate": replicate + 1,
                        "score": f"{score:.6f}",
                    }
                )
    return write_csv(
        "anova_multi_factor.csv",
        ["treatment", "region", "replicate", "score"],
        rows,
    )


def build_sequence(random_source: random.Random) -> int:
    rows: list[dict[str, object]] = []
    for series_index, series_id in enumerate(("设备甲", "设备乙")):
        phase = series_index * 0.7
        previous = 0.0
        for time_index in range(240):
            signal = math.sin(time_index / 12.0 + phase) + 0.3 * math.sin(time_index / 3.5)
            temperature = 22.0 + 4.0 * math.cos(time_index / 24.0 + phase) + random_source.gauss(0.0, 0.15)
            target = 2.2 * signal + 0.08 * temperature + random_source.gauss(0.0, 0.05)
            target_class = "上升" if target >= previous else "下降"
            day = 1 + time_index // 24
            hour = time_index % 24
            rows.append(
                {
                    "timestamp": f"2026-01-{day:02d}T{hour:02d}:00:00",
                    "series_id": series_id,
                    "signal": f"{signal:.6f}",
                    "temperature": f"{temperature:.6f}",
                    "target_value": f"{target:.6f}",
                    "target_class": target_class,
                }
            )
            previous = target
    return write_csv(
        "sequence_fixture.csv",
        ["timestamp", "series_id", "signal", "temperature", "target_value", "target_class"],
        rows,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    random_source = random.Random(RANDOM_SEED)
    definitions = [
        ("classification_fixture.csv", "classification", build_classification),
        ("regression_fixture.csv", "regression", build_regression),
        ("clustering_fixture.csv", "clustering", build_clustering),
        ("anova_one_factor.csv", "one_way_anova", build_one_factor_anova),
        ("anova_multi_factor.csv", "factorial_anova", build_multi_factor_anova),
        ("sequence_fixture.csv", "sequence", build_sequence),
    ]
    files = []
    for filename, task, builder in definitions:
        row_count = builder(random_source)
        files.append(
            {
                "filename": filename,
                "task": task,
                "rows": row_count,
                "encoding": "utf-8",
                "sha256": sha256(OUTPUT_DIRECTORY / filename),
                "license": "CC0-1.0",
                "provenance": "Deterministic synthetic fixture generated by this repository",
            }
        )
    manifest = {
        "version": 1,
        "author": "Kuroneko",
        "randomSeed": RANDOM_SEED,
        "generatedBy": "tests/build_algorithm_fixtures.py",
        "files": files,
    }
    (OUTPUT_DIRECTORY / "fixture_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
