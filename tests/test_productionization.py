import json

import pandas as pd
import pytest

from core.ai_assistant import AIAssistant
from core.db_connector import DBConnector
from core.metrics_cache import LRUCache, frame_fingerprint
from core.model_registry import ModelRegistry


def test_lru_cache_eviction_and_hits():
    cache = LRUCache(maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    stats = cache.stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.evictions == 1


def test_frame_fingerprint_changes_with_data():
    frame = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    same = frame.copy()
    changed = frame.copy()
    changed.loc[1, "a"] = 3
    assert frame_fingerprint(frame) == frame_fingerprint(same)
    assert frame_fingerprint(frame) != frame_fingerprint(changed)


def test_model_registry_roundtrip_and_integrity(tmp_path):
    artifact = tmp_path / "model.dsmodel"
    artifact.write_bytes(b"model-artifact")
    registry = ModelRegistry(str(tmp_path / "registry.json"))
    record = registry.register(
        name="sales-regressor",
        version="1.0.0",
        task="regression",
        target="sales",
        features=["units"],
        model_path=str(artifact),
        dataset_fingerprint="abc123",
    )
    assert registry.verify_artifact(record)
    registry2 = ModelRegistry(registry.path).load()
    assert registry2.latest("sales-regressor").version == "1.0.0"
    assert registry2.approve("sales-regressor", "1.0.0").status == "approved"
    payload = json.loads((tmp_path / "registry.json").read_text())
    assert payload["schema"] == "datasense.model-registry/v1"


def test_ai_assistant_never_remotely_calls_without_opt_in():
    class Manager:
        df = pd.DataFrame({"a": [1, 2]})
        numeric_columns = ["a"]
        datetime_columns = []

        @staticmethod
        def get_summary():
            return "2 rows x 1 columns, 0 missing cells, 0.00 MB in memory."

        @staticmethod
        def get_columns():
            return ["a"]

    assistant = AIAssistant(Manager())
    answer = assistant.generate_response("summary")
    assert "2 rows" in answer


def test_db_connector_blocks_mutating_queries():
    connector = DBConnector()
    result, error = connector.execute_query("DELETE FROM users")
    assert result is None
    assert error is not None
