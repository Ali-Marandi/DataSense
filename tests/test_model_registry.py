from pathlib import Path

from core.model_registry import ModelRegistry


def test_registry_roundtrip_and_integrity(tmp_path: Path) -> None:
    artifact = tmp_path / "model.dsmodel"
    artifact.write_bytes(b"trusted artifact")
    registry = ModelRegistry(str(tmp_path / "registry.json"))
    record = registry.register(
        name="retail-model",
        version="1.0.0",
        task="regression",
        target="revenue",
        features=["units"],
        model_path=str(artifact),
        dataset_fingerprint="abc123",
    )
    assert registry.verify_artifact(record)
    approved = registry.approve("retail-model", "1.0.0")
    assert approved.status == "approved"
    registry2 = ModelRegistry(str(tmp_path / "registry.json"))
    assert registry2.latest("retail-model", approved_only=True) is not None


def test_registry_detects_tampered_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "model.dsmodel"
    artifact.write_bytes(b"original")
    registry = ModelRegistry(str(tmp_path / "registry.json"))
    record = registry.register(
        name="demo", version="1", task="regression", target="y", features=["x"],
        model_path=str(artifact), dataset_fingerprint="fp",
    )
    artifact.write_bytes(b"tampered")
    assert registry.verify_artifact(record) is False
