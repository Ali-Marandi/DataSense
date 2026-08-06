"""Project files (.dsproj) storing the dataset plus the mutation history."""
from __future__ import annotations

import json
import zipfile

import pandas as pd

from .data_manager import DataManager, HistoryStep
from .version import APP_VERSION

MANIFEST = "datasense.json"
DATA_ENTRY = "dataset.parquet"


def save_project(manager: DataManager, path: str) -> tuple[bool, str]:
    if not manager.loaded:
        return False, "There is no dataset to save."
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                MANIFEST,
                json.dumps(
                    {
                        "version": APP_VERSION,
                        "source": manager.source,
                        "rows": int(len(manager.df)),
                        "columns": manager.columns(),
                        "history": [step.label for step in manager.history],
                    },
                    indent=2,
                ),
            )
            archive.writestr(DATA_ENTRY, manager.df.to_parquet(index=False))
    except Exception as exc:
        return False, str(exc)
    return True, "Project saved"


def load_project(manager: DataManager, path: str) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read(MANIFEST))
            frame = pd.read_parquet(__import__("io").BytesIO(archive.read(DATA_ENTRY)))
    except Exception as exc:
        return False, str(exc)
    manager.df = frame
    manager.source = manifest.get("source")
    manager.history = [HistoryStep("Opened project", frame.copy())]
    return True, f"Project restored ({len(frame):,} rows)"
