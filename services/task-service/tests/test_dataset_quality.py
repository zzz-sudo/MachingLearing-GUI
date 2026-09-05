from app.datasets import DatasetService
from app.models import DatasetColumnSpec


def test_missing_values_can_be_filled_with_median_and_mode() -> None:
    columns = [
        DatasetColumnSpec(name="数值", data_type="number"),
        DatasetColumnSpec(name="类别", data_type="text"),
    ]
    records = [
        {"数值": 1.0, "类别": "甲"},
        {"数值": None, "类别": "乙"},
        {"数值": 5.0, "类别": "乙"},
    ]
    result = DatasetService._fill_missing(records, columns, "median")
    assert result[1]["数值"] == 3.0
    assert result[1]["类别"] == "乙"


def test_missing_value_keep_does_not_mutate_records() -> None:
    records = [{"数值": None}]
    columns = [DatasetColumnSpec(name="数值", data_type="number")]
    assert DatasetService._fill_missing(records, columns, "keep") is records
    assert records[0]["数值"] is None
