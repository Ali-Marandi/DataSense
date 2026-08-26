from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.bootstrap import app_data_dir, configure_logging
from app.observability import Observability
from core.data.service import DataService
from core.delivery.signing import FileHmacSigningKeyProvider, SigningKeyProvider
from core.delivery.verified_export import VerifiedExportService
from core.governance.contracts import DataContract, QualityReport
from core.licensing.entitlement import FeatureGate, Entitlement
from core.projects.store import ProjectStore
from core.reporting.automated_report import AutomatedReportService
from core.telemetry.events import TelemetryQueue


@dataclass
class ApplicationState:
    frame: pd.DataFrame | None = None
    source_label: str = "No dataset loaded"
    contract: DataContract = field(default_factory=DataContract.default)
    quality_report: QualityReport | None = None


@dataclass
class Services:
    data: DataService
    delivery: VerifiedExportService
    reporting: AutomatedReportService
    signing_provider: SigningKeyProvider
    projects: ProjectStore
    feature_gate: FeatureGate
    telemetry: TelemetryQueue
    observability: Observability
    state: ApplicationState


def build_services(base_dir: Path | None = None) -> Services:
    data_dir = base_dir or app_data_dir()
    entitlement = Entitlement.plan("alpha", expires_in_days=30)
    observability = configure_logging(data_dir)
    return Services(
        data=DataService(),
        delivery=VerifiedExportService(),
        reporting=AutomatedReportService(),
        signing_provider=FileHmacSigningKeyProvider(data_dir / "signing" / "alpha-local-signing.key"),
        projects=ProjectStore(data_dir / "projects"),
        feature_gate=FeatureGate(entitlement),
        telemetry=TelemetryQueue(data_dir / "telemetry" / "events.jsonl"),
        observability=observability,
        state=ApplicationState(),
    )
