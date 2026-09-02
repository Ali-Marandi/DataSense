import pandas as pd

from core.governance import DataContract, DataQualityRule


def _run(rule, frame):
    report = DataContract(name="cross-column", rules=[rule]).execute(frame)
    return report.results[0]


def test_less_than_or_equal_and_greater_than_or_equal() -> None:
    frame = pd.DataFrame({"start": [1, 2, 5], "end": [1, 3, 4]})
    assert _run(DataQualityRule("less_than_or_equal", "start", {"other_column": "end"}), frame).violations == 1
    assert _run(DataQualityRule("greater_than_or_equal", "end", {"other_column": "start"}), frame).violations == 1


def test_equal_supports_numeric_tolerance() -> None:
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [1.001, 2.2, 3.0]})
    result = _run(DataQualityRule("equal", "a", {"other_column": "b", "tolerance": 0.01}), frame)
    assert result.status == "fail"
    assert result.violations == 1


def test_conditional_required() -> None:
    frame = pd.DataFrame({"status": ["active", "inactive", "active"], "email": ["a@example.com", None, None]})
    result = _run(DataQualityRule("conditional_required", "email", {"when_column": "status", "when_values": ["active"]}), frame)
    assert result.violations == 1


def test_date_order_allows_equal_by_default() -> None:
    frame = pd.DataFrame({"opened": ["2026-01-01", "2026-02-03"], "closed": ["2026-01-01", "2026-02-02"]})
    result = _run(DataQualityRule("date_order", "opened", {"end_column": "closed"}), frame)
    assert result.violations == 1


def test_sum_to_and_unique_combination() -> None:
    frame = pd.DataFrame({"a": [0.2, 0.5, 0.4], "b": [0.8, 0.5, 0.7], "region": ["N", "N", "N"], "year": [2026, 2026, 2027]})
    assert _run(DataQualityRule("sum_to", "", {"columns": ["a", "b"], "target": 1.0, "tolerance": 1e-9}), frame).status == "fail"
    assert _run(DataQualityRule("unique_combination", "", {"columns": ["region", "year"]}), frame).violations == 1


def test_cross_column_configuration_errors_are_explicit() -> None:
    frame = pd.DataFrame({"a": [1], "b": [2]})
    result = _run(DataQualityRule("sum_to", "", {"columns": ["a"], "target": 1}), frame)
    assert result.status == "pass"
    bad = _run(DataQualityRule("unique_combination", "", {"columns": ["a"]}), frame)
    assert bad.status == "error"


def test_cross_column_rules_do_not_mutate_frame() -> None:
    frame = pd.DataFrame({"a": [1.0, 2.0], "b": [1.0, 3.0]})
    before = frame.copy(deep=True)
    _run(DataQualityRule("equal", "a", {"other_column": "b"}), frame)
    pd.testing.assert_frame_equal(frame, before)


def test_contract_round_trip_preserves_cross_column_rule() -> None:
    contract = DataContract(
        name="round-trip",
        rules=[DataQualityRule("date_order", "opened", {"end_column": "closed", "allow_equal": False}, severity="high", name="Open precedes close")],
    )
    restored = DataContract.from_dict(contract.to_dict())
    assert restored.to_dict() == contract.to_dict()
