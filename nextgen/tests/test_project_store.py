from __future__ import annotations

import io
import json
import zipfile

import pandas as pd
import pytest

from core.governance.contracts import DataContract, DataQualityRule
from core.projects.store import ProjectStore, ProjectStoreError


def _contract() -> DataContract:
    return DataContract("Project contract", (DataQualityRule("not_null", "order_id", "critical"),))


def test_project_round_trip_preserves_data_contract_and_metadata(tmp_path):
    store = ProjectStore(tmp_path / "projects")
    frame = pd.DataFrame({"order_id": ["SO-1", "SO-2"], "revenue": [100.0, 200.0]})

    path = store.save("monthly-close", frame, _contract(), project_id="project-123", app_version="0.1.0", locale="fa-IR")
    snapshot = store.load(path)

    assert path.name == "monthly-close.dsproj"
    assert snapshot.project_id == "project-123"
    assert snapshot.app_version == "0.1.0"
    assert snapshot.locale == "fa-IR"
    assert snapshot.frame.to_dict(orient="list") == frame.to_dict(orient="list")
    assert snapshot.contract.name == "Project contract"
    assert snapshot.contract.rules[0].column == "order_id"
    assert snapshot.schema_version == 2


def test_project_overwrite_creates_backup_with_previous_revision(tmp_path):
    store = ProjectStore(tmp_path)
    first = pd.DataFrame({"order_id": ["SO-1"], "revenue": [100.0]})
    second = pd.DataFrame({"order_id": ["SO-2", "SO-3"], "revenue": [200.0, 300.0]})

    path = store.save("project", first, _contract(), project_id="stable-id")
    store.save(path, second, _contract())

    assert store.backup_path(path).exists()
    assert store.load(path).frame.to_dict(orient="list") == second.to_dict(orient="list")
    assert store.load(store.backup_path(path)).frame.to_dict(orient="list") == first.to_dict(orient="list")
    assert store.load(path).project_id == "stable-id"


def test_project_rejects_empty_dataset_and_invalid_archive(tmp_path):
    store = ProjectStore(tmp_path)

    with pytest.raises(ProjectStoreError, match="empty dataset"):
        store.save("empty", pd.DataFrame(columns=["order_id"]), _contract())

    invalid = tmp_path / "broken.dsproj"
    invalid.write_text("not-a-zip", encoding="utf-8")
    with pytest.raises(ProjectStoreError, match="could not be read"):
        store.load(invalid)


def test_project_load_migrates_v1_manifest(tmp_path):
    store = ProjectStore(tmp_path)
    frame = pd.DataFrame({"order_id": ["SO-1"], "revenue": [100.0]})
    parquet_buffer = io.BytesIO()
    frame.to_parquet(parquet_buffer, index=False)
    path = tmp_path / "legacy.dsproj"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("dataset/data.parquet", parquet_buffer.getvalue())
        archive.writestr(
            "manifest.json",
            json.dumps({"schema_version": 1, "contract_name": "Legacy operations", "project_id": "legacy-1"}),
        )

    snapshot = store.load(path)

    assert snapshot.project_id == "legacy-1"
    assert snapshot.contract.name == "Legacy operations"
    assert snapshot.contract.rules == ()
    assert snapshot.schema_version == 1


def test_project_rejects_archive_above_local_limit(tmp_path):
    path = tmp_path / "oversized.dsproj"
    path.write_bytes(b"x" * 40)
    store = ProjectStore(tmp_path, max_archive_bytes=32)

    with pytest.raises(ProjectStoreError, match="size limit"):
        store.load(path)
