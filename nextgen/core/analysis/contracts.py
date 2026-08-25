from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True)
class ProcessingContext:
    project_id: str = "local-unsaved-project"
    locale: str = "en-US"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessingResult:
    module_id: str
    summary: dict[str, int | float | str | bool]
    warnings: tuple[str, ...] = ()
    artifact_references: tuple[str, ...] = ()


class ProcessingModule(Protocol):
    """Contract for deterministic, local data processing modules."""

    module_id: str

    def process(self, frame: pd.DataFrame, context: ProcessingContext) -> ProcessingResult: ...
