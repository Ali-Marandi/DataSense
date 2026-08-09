"""Regression tests for the v2.1 engines and the DataManager API contract."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import insights, model_store, sql, timeseries
from core.dashboard import build_dashboard
from core.data_manager import DataManager, optimise_frame


@pytest.fixture()
def frame():
    rng = np.random.default_rng(3)
    n = 240
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="D"),
            "value": rng.normal(100, 12, n).round(2),
            "units": rng.integers(1, 40, n),
            "region": rng.choice(["North", "South", "East"], n),
        }
    )


@pytest.fixture()
def manager(frame, tmp_path):
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    m = DataManager()
    ok, _ = m.load(str(path))
    assert ok
    return m


# ------------------------------------------------------------ DataManager API
REQUIRED_ATTRS = [
    "loaded", "columns", "numeric_columns", "categorical_columns", "can_undo",
    "can_redo", "set_frame", "undo", "redo", "export", "profile", "query",
    "memory_usage_mb", "drop_columns", "rename_column", "cast_column",
    "drop_duplicates", "drop_missing", "fill_missing", "remove_outliers",
    "scale_columns", "add_computed_column", "group_aggregate", "pivot",
    "get_columns", "get_summary", "save_version", "load_version", "clean_data",
]


@pytest.mark.parametrize("attr", REQUIRED_ATTRS)
def test_manager_exposes_api(manager, attr):
    assert hasattr(manager, attr), f"DataManager is missing '{attr}'"


def test_loaded_flag():
    empty = DataManager()
    assert empty.loaded is False
    empty.df = pd.DataFrame({"a": [1]})
    assert empty.loaded is True


def test_undo_redo(manager):
    original = len(manager.df)
    manager.drop_duplicates()
    manager.set_frame(manager.df.head(10), "trim")
    assert manager.can_undo
    manager.undo()
    assert len(manager.df) >= 10
    manager.redo()
    assert len(manager.df) == 10
    assert original >= 10


def test_profile_and_memory(manager):
    profile = manager.profile()
    assert not profile.empty
    assert {"column", "dtype", "missing"} <= set(profile.columns)
    assert manager.memory_usage_mb() > 0


def test_optimise_memory(manager):
    ok, message = manager.optimise_memory()
    assert ok and "MB" in message


def test_optimise_frame_downcasts():
    df = pd.DataFrame({"i": np.arange(100, dtype="int64"), "s": ["a"] * 100})
    out = optimise_frame(df)
    assert out["i"].dtype != np.int64
    assert str(out["s"].dtype) == "category"


def test_transformations(manager):
    assert manager.add_computed_column("total", "value * units")[0]
    assert "total" in manager.columns
    assert manager.rename_column("total", "revenue")[0]
    assert manager.scale_columns(["value"], "minmax")[0]
    assert manager.group_aggregate(["region"], "units", "sum")[0]


def test_query_filter(manager):
    ok, _ = manager.query("units > 5")
    assert ok
    assert (manager.df["units"] > 5).all()


# ------------------------------------------------------------------- insights
def test_health_score_range(frame):
    assert 0 <= insights.health_score(frame) <= 100


def test_insights_detect_missing_and_duplicates(frame):
    dirty = frame.copy()
    dirty.loc[:100, "value"] = np.nan
    dirty = pd.concat([dirty, dirty.head(30)], ignore_index=True)
    found = insights.generate_insights(dirty)
    titles = " ".join(i.title for i in found)
    assert "Duplicate rows detected" in titles
    assert "value" in titles
    assert insights.health_score(dirty) < insights.health_score(frame)


def test_insights_frame_columns(frame):
    out = insights.insights_frame(frame)
    assert list(out.columns) == ["severity", "category", "title", "detail"]


def test_summary_metrics(frame):
    metrics = insights.summary_metrics(frame)
    assert metrics["Rows"] == "240"
    assert "Health score" in metrics


# ------------------------------------------------------------------------ SQL
def test_sql_select(frame):
    result = sql.run_query(frame, "SELECT region, COUNT(*) AS n FROM data GROUP BY region")
    assert result.ok and result.frame is not None
    assert set(result.frame["region"]) == {"North", "South", "East"}


def test_sql_rejects_dangerous_statements(frame):
    result = sql.run_query(frame, "PRAGMA table_info(data)")
    assert not result.ok


def test_sql_engine_tables(frame):
    engine = sql.SQLEngine()
    engine.register("data", frame)
    engine.register("copy", frame.head(5))
    assert set(engine.list_tables()) == {"data", "copy"}
    assert not engine.schema("data").empty
    engine.close()


# ---------------------------------------------------------------- time series
def test_build_series(frame):
    series = timeseries.build_series(frame, "date", "value", "D", "sum")
    assert len(series) == len(frame)


def test_decompose(frame):
    series = timeseries.build_series(frame, "date", "value", "D", "sum")
    parts = timeseries.decompose(series, period=7)
    assert {"observed", "trend", "seasonal", "residual"} <= set(parts.columns)


@pytest.mark.parametrize("model", timeseries.MODELS)
def test_forecast_models(frame, model):
    series = timeseries.build_series(frame, "date", "value", "D", "sum")
    result = timeseries.forecast(series, 10, model)
    assert len(result.forecast) == 10
    assert set(result.metrics) == {"MAE", "RMSE", "MAPE"}
    assert not timeseries.forecast_frame(result).empty


# --------------------------------------------------------------- model store
def test_model_roundtrip(frame, tmp_path):
    from sklearn.linear_model import LinearRegression

    features = ["units"]
    est = LinearRegression().fit(frame[features], frame["value"])
    bundle = model_store.ModelBundle(est, "regression", "value", features, {"r2": 0.1}, "test")
    path = str(tmp_path / "m")
    ok, _ = model_store.save_model(path, bundle)
    assert ok
    loaded, _ = model_store.load_model(path + model_store.MODEL_EXTENSION)
    assert loaded is not None and loaded.target == "value"
    assert not loaded.describe().empty
    scored, message = model_store.score(loaded, frame)
    assert scored is not None and "prediction" in scored.columns


def test_score_reports_missing_features(frame, tmp_path):
    from sklearn.linear_model import LinearRegression

    est = LinearRegression().fit(frame[["units"]], frame["value"])
    bundle = model_store.ModelBundle(est, "regression", "value", ["units"])
    out, message = model_store.score(bundle, frame.drop(columns=["units"]))
    assert out is None and "missing" in message.lower()


# ------------------------------------------------------------------ dashboard
def test_dashboard_export(frame, tmp_path):
    path = tmp_path / "dash.html"
    ok, message = build_dashboard(frame, str(path))
    assert ok, message
    html = path.read_text(encoding="utf-8")
    assert "Plotly.newPlot" in html
    assert "Automatic insights" in html


def test_dashboard_requires_data(tmp_path):
    ok, _ = build_dashboard(pd.DataFrame(), str(tmp_path / "x.html"))
    assert not ok
