from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "algorithms"


def read_rows(filename: str) -> list[dict[str, str]]:
    with (FIXTURE_DIRECTORY / filename).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_algorithm_fixture_manifest_matches_committed_files() -> None:
    manifest = json.loads((FIXTURE_DIRECTORY / "fixture_manifest.json").read_text(encoding="utf-8"))

    assert manifest["version"] == 1
    assert manifest["author"] == "Kuroneko"
    assert manifest["randomSeed"] == 20260819
    assert len(manifest["files"]) == 6
    for item in manifest["files"]:
        path = FIXTURE_DIRECTORY / item["filename"]
        assert path.is_file()
        assert item["encoding"] == "utf-8"
        assert item["license"] == "CC0-1.0"
        assert len(read_rows(item["filename"])) == item["rows"]
        assert file_sha256(path) == item["sha256"]


def test_classification_and_regression_fixtures_have_expected_signal() -> None:
    classification = read_rows("classification_fixture.csv")
    regression = read_rows("regression_fixture.csv")

    assert len(classification) == 240
    assert Counter(row["target_class"] for row in classification) == {
        "类别1": 80,
        "类别2": 80,
        "类别3": 80,
    }
    errors = []
    region_effects = {"华东": 4.0, "华南": -1.5, "华北": 2.0}
    for row in regression:
        expected = 3.2 * float(row["feature_x"]) - 1.7 * float(row["feature_y"]) + region_effects[row["region"]]
        errors.append(abs(float(row["target_value"]) - expected))
    assert len(regression) == 320
    assert sum(errors) / len(errors) < 1.0


def test_clustering_and_anova_fixtures_are_balanced() -> None:
    clustering = read_rows("clustering_fixture.csv")
    one_factor = read_rows("anova_one_factor.csv")
    multi_factor = read_rows("anova_multi_factor.csv")

    assert Counter(row["expected_cluster"] for row in clustering) == {"0": 120, "1": 120, "2": 120}
    one_factor_means: dict[str, list[float]] = defaultdict(list)
    for row in one_factor:
        one_factor_means[row["treatment"]].append(float(row["score"]))
    means = {name: sum(values) / len(values) for name, values in one_factor_means.items()}
    assert means["对照组"] < means["方案甲"] < means["方案乙"] < means["方案丙"]
    combinations = Counter((row["treatment"], row["region"]) for row in multi_factor)
    assert len(combinations) == 6
    assert set(combinations.values()) == {40}


def test_sequence_fixture_is_ordered_within_each_series() -> None:
    rows = read_rows("sequence_fixture.csv")
    by_series: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_series[row["series_id"]].append(row["timestamp"])

    assert len(rows) == 480
    assert set(by_series) == {"设备甲", "设备乙"}
    for timestamps in by_series.values():
        assert len(timestamps) == 240
        assert timestamps == sorted(timestamps)
