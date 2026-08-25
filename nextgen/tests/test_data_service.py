from __future__ import annotations

import pandas as pd
import pytest

from core.data.service import DataService, DatasetLoadError


def test_load_csv_and_profile_expose_only_aggregate_metrics(tmp_path):
    source = tmp_path / "orders.csv"
    source.write_text(
        "order_id,region,revenue\nSO-1,North,100\nSO-2,,120\nSO-2,,120\n",
        encoding="utf-8",
    )

    service = DataService()
    frame = service.load_csv(source)
    profile = service.profile(frame)

    assert profile.rows == 3
    assert profile.columns == 3
    assert profile.missing_cells == 2
    assert profile.duplicate_rows == 1
    assert profile.column("order_id").unique == 2
    assert profile.column("region").missing == 2
    assert "SO-1" not in str(profile.to_dict())


def test_load_tsv_uses_tab_delimiter_automatically(tmp_path):
    source = tmp_path / "orders.tsv"
    source.write_text("order_id\trevenue\nSO-1\t100\n", encoding="utf-8")

    frame = DataService().load_csv(source)

    assert list(frame.columns) == ["order_id", "revenue"]
    assert frame.loc[0, "order_id"] == "SO-1"


def test_load_delimited_text_accepts_explicit_delimiter(tmp_path):
    source = tmp_path / "orders.txt"
    source.write_text("order_id;revenue\nSO-1;100\n", encoding="utf-8")

    frame = DataService().load_csv(source, delimiter=";")

    assert list(frame.columns) == ["order_id", "revenue"]


@pytest.mark.parametrize(
    ("path_name", "content", "expected_message"),
    [
        ("empty.csv", "", "contains no tabular data"),
        ("unsupported.xlsx", "not,really,xlsx\n", "Supported starter formats"),
    ],
)
def test_load_csv_rejects_invalid_inputs(tmp_path, path_name, content, expected_message):
    source = tmp_path / path_name
    source.write_text(content, encoding="utf-8")

    with pytest.raises(DatasetLoadError, match=expected_message):
        DataService().load_csv(source)


def test_load_csv_rejects_missing_file_and_folder(tmp_path):
    service = DataService()

    with pytest.raises(DatasetLoadError, match="Dataset not found"):
        service.load_csv(tmp_path / "missing.csv")
    with pytest.raises(DatasetLoadError, match="not a folder"):
        service.load_csv(tmp_path)


def test_profile_rejects_duplicate_column_names_and_empty_frames():
    service = DataService()
    duplicate_columns = pd.DataFrame([["SO-1", "North"]], columns=["order_id", "order_id"])

    with pytest.raises(DatasetLoadError, match="column names must be unique"):
        service.profile(duplicate_columns)
    with pytest.raises(DatasetLoadError, match="contains no rows"):
        service.profile(pd.DataFrame(columns=["order_id"]))


def test_profile_returns_copy_safe_aggregate_output():
    frame = pd.DataFrame({"order_id": ["SO-1"], "revenue": [100]})
    service = DataService()

    profile = service.profile(frame)
    frame.loc[0, "order_id"] = "changed-after-profile"

    assert profile.column("order_id").unique == 1
    assert profile.summary()["Rows"] == "1"
