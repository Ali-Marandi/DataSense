"""Trust Center workspace for local data quality and sensitive-data controls."""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.evidence import read_signing_key, write_evidence_bundle
from core.governance import (
    DataContract,
    DataQualityRule,
    classifications_frame,
    recommended_rules,
    scan_sensitive_data,
)


RULE_HELP = {
    "not_null": "No parameters needed.",
    "unique": "No parameters needed.",
    "range": 'Example: {"min": 0, "max": 100}',
    "allowed_values": 'Example: {"values": ["North", "South"]}',
    "regex": 'Example: {"pattern": "[A-Z]{2}-[0-9]{4}"}',
    "freshness": 'Example: {"max_age_days": 7}',
}


class TrustCenterTab(QWidget):
    """A review-first UI; it never mutates the dataset while running checks."""

    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        text = QVBoxLayout()
        title = QLabel("Trust Center")
        title.setStyleSheet("font-size:20px;font-weight:700;")
        subtitle = QLabel(
            "Validate data contracts locally, review sensitive-data signals, and export portable audit evidence."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("opacity:.8;")
        text.addWidget(title)
        text.addWidget(subtitle)
        header.addLayout(text, 1)
        self.scan_button = QPushButton("Scan sensitive data")
        self.scan_button.clicked.connect(self.scan_sensitive_data)
        self.run_button = QPushButton("Run quality checks")
        self.run_button.clicked.connect(self.run_checks)
        self.schema_baseline_button = QPushButton("Approve current schema")
        self.schema_baseline_button.setToolTip("Create a schema-only baseline; no dataset values are retained.")
        self.schema_baseline_button.clicked.connect(self.approve_schema_baseline)
        self.schema_check_button = QPushButton("Check schema drift")
        self.schema_check_button.clicked.connect(self.check_schema_drift)
        self.lineage_button = QPushButton("View lineage")
        self.lineage_button.setToolTip("Review privacy-preserving transformation history for this project.")
        self.lineage_button.clicked.connect(self.show_lineage)
        header.addWidget(self.scan_button)
        header.addWidget(self.run_button)
        header.addWidget(self.schema_baseline_button)
        header.addWidget(self.schema_check_button)
        header.addWidget(self.lineage_button)
        root.addLayout(header)

        self.summary_grid = QGridLayout()
        self.summary_grid.setSpacing(10)
        self.summary: dict[str, QLabel] = {}
        for index, caption in enumerate(["Trust status", "Quality score", "Release gate", "Quality trend", "Schema guard", "Failed checks"]):
            card = QGroupBox(caption.upper())
            layout = QVBoxLayout(card)
            value = QLabel("—")
            value.setStyleSheet("font-size:20px;font-weight:650;")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(value)
            self.summary[caption] = value
            self.summary_grid.addWidget(card, 0, index)
        root.addLayout(self.summary_grid)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._contract_editor())
        splitter.addWidget(self._audit_evidence())
        splitter.setSizes([340, 420])
        root.addWidget(splitter, 1)

    def _contract_editor(self) -> QWidget:
        box = QGroupBox("Data contract")
        root = QVBoxLayout(box)

        contract_row = QHBoxLayout()
        contract_row.addWidget(QLabel("Contract name"))
        self.contract_name = QLineEdit()
        self.contract_name.setPlaceholderText("e.g. Monthly sales acceptance contract")
        contract_row.addWidget(self.contract_name, 1)
        self.recommend_button = QPushButton("Add recommended rules")
        self.recommend_button.setToolTip("Adds reviewable starter rules; it never changes your data.")
        self.recommend_button.clicked.connect(self.add_recommended_rules)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self.remove_selected_rule)
        contract_row.addWidget(self.recommend_button)
        contract_row.addWidget(self.remove_button)
        root.addLayout(contract_row)

        builder = QHBoxLayout()
        form = QFormLayout()
        self.rule_type = QComboBox()
        self.rule_type.addItems(list(RULE_HELP))
        self.rule_type.currentTextChanged.connect(self._set_rule_help)
        self.rule_column = QComboBox()
        self.rule_severity = QComboBox()
        self.rule_severity.addItems(["critical", "high", "medium", "low"])
        self.rule_params = QTextEdit()
        self.rule_params.setFixedHeight(58)
        self.rule_params.setPlaceholderText(RULE_HELP["not_null"])
        form.addRow("Rule type", self.rule_type)
        form.addRow("Column", self.rule_column)
        form.addRow("Severity", self.rule_severity)
        form.addRow("Parameters (JSON)", self.rule_params)
        self.add_rule_button = QPushButton("Add rule")
        self.add_rule_button.clicked.connect(self.add_rule)
        form.addRow("", self.add_rule_button)
        builder.addLayout(form, 0)

        self.rules_table = QTableWidget(0, 5)
        self.rules_table.setHorizontalHeaderLabels(["Severity", "Rule", "Column", "Parameters", "Name"])
        self.rules_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rules_table.setMinimumHeight(155)
        builder.addWidget(self.rules_table, 1)
        root.addLayout(builder, 1)
        return box

    def _audit_evidence(self) -> QWidget:
        box = QGroupBox("Audit evidence")
        root = QVBoxLayout(box)

        top = QHBoxLayout()
        top.addWidget(QLabel("Sensitive-data signals (detection is local and values are not retained)"), 1)
        self.export_button = QPushButton("Export audit JSON")
        self.export_button.clicked.connect(self.export_audit)
        top.addWidget(self.export_button)
        self.signed_export_button = QPushButton("Export signed evidence bundle")
        self.signed_export_button.setToolTip("Signs metadata-only evidence with a local HMAC key file; the key is never included in the bundle.")
        self.signed_export_button.clicked.connect(self.export_signed_evidence)
        top.addWidget(self.signed_export_button)
        root.addLayout(top)

        self.pii_table = QTableWidget(0, 6)
        self.pii_table.setHorizontalHeaderLabels(
            ["Column", "Classification", "Sensitivity", "Confidence", "Evidence", "Recommendation"]
        )
        self.pii_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pii_table.setAlternatingRowColors(True)
        self.pii_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.pii_table, 1)

        root.addWidget(QLabel("Quality-check results"))
        self.results_table = QTableWidget(0, 8)
        self.results_table.setHorizontalHeaderLabels(
            ["Status", "Severity", "Rule", "Column", "Observed", "Expected", "Violations", "Detail"]
        )
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.results_table, 1)
        return box

    def _set_rule_help(self, rule_type: str) -> None:
        self.rule_params.setPlaceholderText(RULE_HELP.get(rule_type, "Optional JSON parameters"))

    def _require_dataset(self) -> bool:
        if self.manager.loaded:
            return True
        QMessageBox.information(self, "No dataset", "Import a dataset before using Trust Center.")
        return False

    def _current_contract(self) -> DataContract:
        name = self.contract_name.text().strip() or "DataSense data contract"
        contract = self.manager.governance_contract
        if contract.name != name:
            contract = DataContract(name=name, rules=list(contract.rules))
            self.manager.set_governance_contract(contract)
        return contract

    def _set_contract(self, rules: list[DataQualityRule]) -> None:
        name = self.contract_name.text().strip() or "DataSense data contract"
        self.manager.set_governance_contract(DataContract(name=name, rules=rules))
        self.refresh()

    def add_rule(self) -> None:
        if not self._require_dataset():
            return
        column = self.rule_column.currentText()
        if not column:
            return
        params_text = self.rule_params.toPlainText().strip()
        try:
            params = json.loads(params_text) if params_text else {}
            if not isinstance(params, dict):
                raise ValueError("Parameters must be a JSON object.")
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Invalid parameters", str(exc))
            return
        rule = DataQualityRule(
            rule_type=self.rule_type.currentText(),
            column=column,
            params=params,
            severity=self.rule_severity.currentText(),
        )
        self._set_contract([*self._current_contract().rules, rule])
        self.rule_params.clear()

    def add_recommended_rules(self) -> None:
        if not self._require_dataset():
            return
        current = self._current_contract().rules
        existing = {(rule.rule_type, rule.column, json.dumps(rule.params, sort_keys=True, default=str)) for rule in current}
        additions = [
            rule
            for rule in recommended_rules(self.manager.df)
            if (rule.rule_type, rule.column, json.dumps(rule.params, sort_keys=True, default=str)) not in existing
        ]
        self._set_contract([*current, *additions])
        QMessageBox.information(
            self,
            "Recommended rules added",
            f"Added {len(additions)} reviewable rule(s). Review each rule before relying on it.",
        )

    def remove_selected_rule(self) -> None:
        rows = sorted({item.row() for item in self.rules_table.selectedItems()}, reverse=True)
        if not rows:
            return
        rules = list(self._current_contract().rules)
        for row in rows:
            if 0 <= row < len(rules):
                rules.pop(row)
        self._set_contract(rules)

    def scan_sensitive_data(self) -> None:
        if not self._require_dataset():
            return
        frame = classifications_frame(scan_sensitive_data(self.manager.df))
        self._populate_table(self.pii_table, frame)
        message = "No supported sensitive-data patterns were detected." if frame.empty else f"Found {len(frame)} sensitive-data signal(s). Review them before sharing data."
        QMessageBox.information(self, "Sensitive-data scan complete", message)

    def run_checks(self) -> None:
        if not self._require_dataset():
            return
        self._current_contract()
        report = self.manager.run_governance_checks()
        self._render_report(report)
        self.refresh()

    def approve_schema_baseline(self) -> None:
        if not self._require_dataset():
            return
        baseline = self.manager.set_schema_baseline()
        self.refresh()
        QMessageBox.information(
            self,
            "Schema baseline approved",
            f"Stored a schema-only baseline for {len(baseline.columns)} column(s).\nFingerprint: {baseline.fingerprint[:16]}…",
        )

    def check_schema_drift(self) -> None:
        if not self._require_dataset():
            return
        report = self.manager.check_schema_drift()
        self.refresh()
        details = "\n".join(report.reasons)
        message = f"Decision: {report.decision.title()}\n\n{details}"
        if report.decision == "blocked":
            QMessageBox.warning(self, "Schema drift blocked", message)
        else:
            QMessageBox.information(self, "Schema drift check", message)

    def show_lineage(self) -> None:
        events = self.manager.lineage.events
        if not events:
            QMessageBox.information(self, "Transformation lineage", "No lineage events are available for this project yet.")
            return
        lines: list[str] = []
        for event in events[-15:]:
            changes: list[str] = []
            if event.added_columns:
                changes.append(f"added: {', '.join(event.added_columns)}")
            if event.removed_columns:
                changes.append(f"removed: {', '.join(event.removed_columns)}")
            if event.dtype_changes:
                changes.append(f"types: {', '.join(event.dtype_changes)}")
            summary = "; ".join(changes) if changes else "schema unchanged"
            lines.append(
                f"#{event.sequence} — {event.operation}\n"
                f"{event.occurred_at} | rows {event.input_rows if event.input_rows is not None else '—'} → {event.output_rows if event.output_rows is not None else '—'} | {summary}"
            )
        QMessageBox.information(self, "Transformation lineage", "\n\n".join(lines))

    def export_audit(self) -> None:
        report = self.manager.governance_report
        if report is None:
            QMessageBox.information(self, "Run checks first", "Run quality checks before exporting an audit report.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export audit report",
            "datasense-audit.json",
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            evidence = {
                "report": report.to_dict(),
                "quality_gate_policy": self.manager.quality_gate_policy.to_dict(),
                "quality_gate_decision": report.gate_decision(self.manager.quality_gate_policy).to_dict(),
                "quality_history": self.manager.quality_history.to_dict(),
                "schema_baseline": self.manager.schema_baseline.to_dict() if self.manager.schema_baseline else None,
                "schema_drift_policy": self.manager.schema_drift_policy.to_dict(),
                "schema_drift_report": self.manager.check_schema_drift().to_dict(),
                "lineage": self.manager.lineage.to_dict(),
            }
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(evidence, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Audit exported", f"Audit evidence was saved to:\n{path}")

    def export_signed_evidence(self) -> None:
        if self.manager.governance_report is None:
            QMessageBox.information(self, "Run checks first", "Run quality checks before creating signed evidence.")
            return
        key_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose HMAC signing key file",
            "",
            "Key files (*.key *.secret *.txt);;All files (*)",
        )
        if not key_path:
            return
        bundle_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export signed evidence bundle",
            "datasense-evidence.signed.json",
            "JSON files (*.json)",
        )
        if not bundle_path:
            return
        try:
            key = read_signing_key(key_path)
            bundle = self.manager.signed_evidence_bundle(key, Path(key_path).stem)
            write_evidence_bundle(bundle_path, bundle)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Signed export failed", str(exc))
            return
        signature = bundle["signature"]
        QMessageBox.information(
            self,
            "Signed evidence exported",
            "Metadata-only evidence was signed and saved to:\n"
            f"{bundle_path}\n\nAlgorithm: {signature['algorithm']}\nKey ID: {signature['key_id']}\n"
            "Keep the signing key outside source control. Verification is available through core.evidence.",
        )

    def _populate_table(self, widget: QTableWidget, frame) -> None:
        widget.setRowCount(len(frame))
        for row_index, row in frame.iterrows():
            for col_index, value in enumerate(row.tolist()):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                widget.setItem(row_index, col_index, item)
        widget.resizeColumnsToContents()

    def _render_rules(self) -> None:
        rules = self.manager.governance_contract.rules
        self.rules_table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            values = [
                rule.severity,
                rule.rule_type,
                rule.column,
                json.dumps(rule.params, ensure_ascii=False, default=str),
                rule.display_name(),
            ]
            for col, value in enumerate(values):
                self.rules_table.setItem(row, col, QTableWidgetItem(value))
        self.rules_table.resizeColumnsToContents()

    def _render_report(self, report) -> None:
        self._populate_table(self.results_table, report.to_frame())
        self.summary["Trust status"].setText(report.status.title())
        self.summary["Quality score"].setText("Not configured" if report.score is None else f"{report.score:.1f}%")
        gate = report.gate_decision(self.manager.quality_gate_policy)
        self.summary["Release gate"].setText(gate.decision.title())
        self.summary["Quality trend"].setText(self.manager.quality_history.trend().title())
        self.summary["Schema guard"].setText(self.manager.check_schema_drift().decision.title())
        self.summary["Failed checks"].setText(str(sum(result.status == "fail" for result in report.results)))

    def refresh(self) -> None:
        has_data = self.manager.loaded
        self.scan_button.setEnabled(has_data)
        self.run_button.setEnabled(has_data)
        self.schema_baseline_button.setEnabled(has_data)
        self.schema_check_button.setEnabled(has_data)
        self.lineage_button.setEnabled(has_data)
        self.recommend_button.setEnabled(has_data)
        self.add_rule_button.setEnabled(has_data)
        self.rule_column.clear()
        self.rule_column.addItems(self.manager.columns)
        self.contract_name.setText(self.manager.governance_contract.name)
        self._render_rules()
        report = self.manager.governance_report
        if report is not None:
            self._render_report(report)
        else:
            self.results_table.setRowCount(0)
            self.summary["Trust status"].setText("Not configured" if not self.manager.governance_contract.rules else "Not run")
            self.summary["Quality score"].setText("—")
            self.summary["Release gate"].setText("Not run")
            self.summary["Quality trend"].setText(self.manager.quality_history.trend().title())
            self.summary["Schema guard"].setText(self.manager.check_schema_drift().decision.title() if has_data else "Not configured")
            self.summary["Failed checks"].setText("—")
        if not has_data:
            self.pii_table.setRowCount(0)
