from __future__ import annotations

import pandas as pd
import pytest

from core.governance.contracts import DataContract, DataQualityRule


def test_starter_contract_approves_unique_populated_order_ids():
    frame = pd.DataFrame({"order_id": ["A-1", "A-2"], "value": [1, 2]})

    report = DataContract.default().evaluate(frame)

    assert report.approved
    assert report.summary() == {
        "status": "approved",
        "rules": 2,
        "failed_rules": 0,
        "blocking_failures": 0,
        "total_violations": 0,
    }


def test_starter_contract_blocks_duplicate_order_ids():
    frame = pd.DataFrame({"order_id": ["A-1", "A-1"], "value": [1, 2]})

    report = DataContract.default().evaluate(frame)

    assert not report.approved
    assert len(report.blocking_failures) == 1
    assert report.blocking_failures[0].rule.rule_type == "unique"
    assert report.total_violations == 2


def test_missing_required_column_blocks_and_explains_reason():
    report = DataContract.default().evaluate(pd.DataFrame({"invoice_id": ["I-1", "I-2"]}))

    assert not report.approved
    assert len(report.blocking_failures) == 2
    assert all(result.detail == "Required column is missing." for result in report.results)
    assert report.summary()["total_violations"] == 4


def test_nulls_fail_not_null_but_do_not_also_fail_unique_rule():
    frame = pd.DataFrame({"order_id": ["A-1", None, None], "value": [1, 2, 3]})

    report = DataContract.default().evaluate(frame)
    results = {result.rule.rule_type: result for result in report.results}

    assert not report.approved
    assert results["not_null"].violations == 2
    assert results["unique"].passed
    assert results["unique"].violations == 0


def test_medium_failure_is_reported_but_does_not_block_delivery():
    contract = DataContract(
        "Advisory contract",
        (DataQualityRule("unique", "order_id", "medium"),),
    )
    frame = pd.DataFrame({"order_id": ["A-1", "A-1"]})

    report = contract.evaluate(frame)

    assert report.approved
    assert len(report.failures) == 1
    assert not report.blocking_failures
    assert report.to_rows()[0]["status"] == "fail"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DataQualityRule("unknown", "order_id"),  # type: ignore[arg-type]
        lambda: DataQualityRule("unique", "order_id", "urgent"),  # type: ignore[arg-type]
        lambda: DataQualityRule("unique", "   "),
        lambda: DataContract("", ()),
        lambda: DataContract("Duplicate rule", (DataQualityRule("unique", "order_id"), DataQualityRule("unique", "order_id"))),
    ],
)
def test_contract_model_rejects_invalid_configuration(factory):
    with pytest.raises(ValueError):
        factory()


def test_contract_rejects_non_dataframe_input():
    with pytest.raises(TypeError, match="pandas DataFrame"):
        DataContract.default().evaluate({"order_id": ["A-1"]})  # type: ignore[arg-type]
