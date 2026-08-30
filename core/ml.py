"""Machine learning workflows (regression, classification, clustering, PCA).

The core keeps train/evaluation semantics explicit and exposes reproducibility metadata
without persisting dataset values. Time-aware evaluation is opt-in and never silently
falls back to random shuffling.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, silhouette_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

REGRESSORS = {
    "Linear Regression": LinearRegression,
    "Ridge Regression": Ridge,
    "Decision Tree": DecisionTreeRegressor,
    "Random Forest": RandomForestRegressor,
    "Gradient Boosting": GradientBoostingRegressor,
    "Support Vector Machine": SVR,
}

CLASSIFIERS = {
    "Logistic Regression": LogisticRegression,
    "Decision Tree": DecisionTreeClassifier,
    "Random Forest": RandomForestClassifier,
    "Gradient Boosting": GradientBoostingClassifier,
    "Support Vector Machine": SVC,
}


@dataclass
class ModelResult:
    title: str
    metrics: dict[str, float | int | str]
    table: pd.DataFrame | None = None
    note: str = ""
    predictions: pd.DataFrame | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def dataset_fingerprint(df: pd.DataFrame, target: str, features: list[str]) -> str:
    """Stable schema/shape fingerprint without serialising cell values."""
    payload = {"rows": int(len(df)), "columns": [(str(c), str(df[c].dtype)) for c in df.columns], "target": target, "features": list(features)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def detect_leakage_risks(df: pd.DataFrame, target: str, features: list[str], time_column: str | None = None) -> list[str]:
    """Return conservative leakage warnings rather than silently removing features."""
    warnings: list[str] = []
    target_tokens = {token for token in target.lower().replace("-", "_").split("_") if len(token) >= 3}
    for feature in features:
        if feature == target:
            warnings.append(f"Feature '{feature}' is also the target.")
            continue
        normalized = feature.lower().replace("-", "_")
        feature_tokens = set(normalized.split("_"))
        if target_tokens and target_tokens.intersection(feature_tokens) and any(token in normalized for token in ("future", "outcome", "result", "post", "label")):
            warnings.append(f"Feature '{feature}' may encode post-target information.")
    if time_column and time_column in features:
        warnings.append(f"Time column '{time_column}' is included as a predictor; verify that it is available at prediction time.")
    return warnings


def _prepare(df: pd.DataFrame, target: str, features: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    if target not in df.columns or any(feature not in df.columns for feature in features):
        raise ValueError("Target and all selected features must exist in the dataset.")
    data = df[features + [target]].copy()
    for col in features:
        if not pd.api.types.is_numeric_dtype(data[col]):
            data[col] = data[col].astype("category").cat.codes
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    return data[features], data[target]


def _split_data(X: pd.DataFrame, y: pd.Series, *, test_size: float, random_state: int, time_values: pd.Series | None = None):
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1")
    if time_values is not None:
        timestamps = pd.to_datetime(time_values, errors="coerce", utc=True)
        valid = timestamps.notna()
        X, y, timestamps = X.loc[valid], y.loc[valid], timestamps.loc[valid]
        order = timestamps.sort_values(kind="stable").index
        X, y = X.loc[order], y.loc[order]
        split = max(1, int(len(X) * (1.0 - test_size)))
        if split >= len(X):
            split = len(X) - 1
        return X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:], "chronological"
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=random_state)
    return X_tr, X_te, y_tr, y_te, "random_seeded"


def _cv_folds(n_rows: int) -> int:
    return min(5, max(2, n_rows // 5)) if n_rows >= 10 else 2


def train_regression(df: pd.DataFrame, target: str, features: list[str], model_name: str, test_size: float = 0.2, time_column: str | None = None) -> ModelResult:
    X, y = _prepare(df, target, features)
    y = pd.to_numeric(y, errors="coerce")
    keep = y.notna()
    X, y = X[keep], y[keep]
    if len(X) < 10:
        raise ValueError("At least 10 complete rows are required to train a model.")
    if model_name not in REGRESSORS:
        raise ValueError(f"Unsupported regression model: {model_name}")
    time_values = df.loc[X.index, time_column] if time_column else None
    X_tr, X_te, y_tr, y_te, split_strategy = _split_data(X, y, test_size=test_size, random_state=42, time_values=time_values)
    model = REGRESSORS[model_name](random_state=42) if model_name in {"Decision Tree", "Random Forest", "Gradient Boosting"} else REGRESSORS[model_name]()
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    cv = cross_val_score(model, X, y, cv=_cv_folds(len(X)), scoring="r2")
    baseline_prediction = np.repeat(float(y_tr.mean()), len(y_te))
    warnings = detect_leakage_risks(df, target, features, time_column)
    table = None
    if hasattr(model, "feature_importances_"):
        table = pd.DataFrame({"Feature": features, "Importance": np.round(model.feature_importances_, 5)}).sort_values("Importance", ascending=False)
    elif hasattr(model, "coef_"):
        table = pd.DataFrame({"Feature": features, "Coefficient": np.round(np.ravel(model.coef_), 5)})
    return ModelResult(
        title=f"{model_name} - predicting {target}",
        metrics={"R2 (test)": round(float(r2_score(y_te, pred)), 5), "RMSE": round(float(np.sqrt(mean_squared_error(y_te, pred))), 5), "MAE": round(float(mean_absolute_error(y_te, pred)), 5), "Baseline RMSE": round(float(np.sqrt(mean_squared_error(y_te, baseline_prediction))), 5), "CV R2 (mean)": round(float(cv.mean()), 5), "CV R2 (std)": round(float(cv.std()), 5), "Train rows": len(X_tr), "Test rows": len(X_te)},
        table=table,
        note=("Chronological split used; test data is later than training data. " if split_strategy == "chronological" else "Random split uses a fixed seed. ") + ("Leakage review: " + " | ".join(warnings) if warnings else "No automatic leakage warning was triggered."),
        predictions=pd.DataFrame({"Actual": y_te.to_numpy(), "Predicted": np.round(pred, 5)}),
        metadata={"dataset_fingerprint": dataset_fingerprint(df, target, features), "target": target, "features": list(features), "split_strategy": split_strategy, "test_size": test_size, "random_state": 42, "prediction_index": [int(i) if isinstance(i, (int, np.integer)) else str(i) for i in y_te.index], "leakage_warnings": warnings},
    )


def train_classification(df: pd.DataFrame, target: str, features: list[str], model_name: str, test_size: float = 0.2, time_column: str | None = None) -> ModelResult:
    X, y = _prepare(df, target, features)
    y = y.astype(str)
    if model_name not in CLASSIFIERS:
        raise ValueError(f"Unsupported classification model: {model_name}")
    if y.nunique() < 2:
        raise ValueError("The target column needs at least two classes.")
    if len(X) < 10:
        raise ValueError("At least 10 complete rows are required to train a model.")
    time_values = df.loc[X.index, time_column] if time_column else None
    X_tr, X_te, y_tr, y_te, split_strategy = _split_data(X, y, test_size=test_size, random_state=42, time_values=time_values)
    if y_tr.nunique() < 2:
        raise ValueError("The training split must contain at least two target classes.")
    kwargs: dict[str, object] = {}
    if model_name == "Logistic Regression": kwargs["max_iter"] = 1000
    if model_name in {"Decision Tree", "Random Forest", "Gradient Boosting"}: kwargs["random_state"] = 42
    model = CLASSIFIERS[model_name](**kwargs)
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    labels = sorted(y.unique())
    cm = confusion_matrix(y_te, pred, labels=labels)
    table = pd.DataFrame(cm, index=[f"true {c}" for c in labels], columns=[f"pred {c}" for c in labels]).reset_index(names="Class")
    warnings = detect_leakage_risks(df, target, features, time_column)
    metrics: dict[str, float | int | str] = {"Accuracy": round(float(accuracy_score(y_te, pred)), 5), "Precision (weighted)": round(float(precision_score(y_te, pred, average="weighted", zero_division=0)), 5), "Recall (weighted)": round(float(recall_score(y_te, pred, average="weighted", zero_division=0)), 5), "F1 (weighted)": round(float(f1_score(y_te, pred, average="weighted", zero_division=0)), 5), "Classes": int(y.nunique()), "Train rows": len(X_tr), "Test rows": len(X_te)}
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X_te)
        metrics["Max probability mean"] = round(float(np.max(probabilities, axis=1).mean()), 5)
    return ModelResult(
        title=f"{model_name} - classifying {target}", metrics=metrics, table=table,
        note=("Chronological split used. " if split_strategy == "chronological" else "Random split uses a fixed seed. ") + ("Leakage review: " + " | ".join(warnings) if warnings else "No automatic leakage warning was triggered."),
        predictions=pd.DataFrame({"Actual": y_te.to_numpy(), "Predicted": pred}),
        metadata={"dataset_fingerprint": dataset_fingerprint(df, target, features), "target": target, "features": list(features), "split_strategy": split_strategy, "test_size": test_size, "random_state": 42, "prediction_index": [int(i) if isinstance(i, (int, np.integer)) else str(i) for i in y_te.index], "leakage_warnings": warnings},
    )


def run_clustering(df: pd.DataFrame, features: list[str], k: int = 3) -> ModelResult:
    if k < 2: raise ValueError("k must be at least 2")
    X = df[features].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(X) < k: raise ValueError("Fewer complete rows than requested clusters.")
    scaled = StandardScaler().fit_transform(X)
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(scaled)
    sil = silhouette_score(scaled, labels) if k > 1 and len(set(labels)) > 1 else float("nan")
    sizes = pd.Series(labels).value_counts().sort_index()
    centers = pd.DataFrame(model.cluster_centers_, columns=features).round(4)
    centers.insert(0, "Cluster", range(k))
    return ModelResult(title=f"K-Means clustering (k={k})", metrics={"Silhouette score": round(float(sil), 5) if sil == sil else "n/a", "Inertia": round(float(model.inertia_), 4), "Rows clustered": len(X)}, table=centers, note="Cluster centroids in standardised feature space; k-means uses a fixed seed.", predictions=pd.concat([X.reset_index(drop=True), pd.Series(labels, name="Cluster")], axis=1), metadata={"features": list(features), "k": k, "random_state": 42})


def run_pca(df: pd.DataFrame, features: list[str], components: int = 2) -> ModelResult:
    X = df[features].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if X.empty: raise ValueError("No complete numeric rows are available for PCA.")
    if components < 1: raise ValueError("components must be at least 1")
    components = min(components, len(features), max(len(X) - 1, 1))
    scaled = StandardScaler().fit_transform(X)
    pca = PCA(n_components=components)
    scores = pca.fit_transform(scaled)
    table = pd.DataFrame({"Component": [f"PC{i + 1}" for i in range(components)], "Explained variance %": np.round(pca.explained_variance_ratio_ * 100, 3), "Cumulative %": np.round(np.cumsum(pca.explained_variance_ratio_) * 100, 3)})
    loadings = pd.DataFrame(pca.components_.T, index=features, columns=[f"PC{i + 1}" for i in range(components)]).reset_index(names="Feature").round(5)
    return ModelResult(title=f"Principal component analysis ({components} components)", metrics={"Total variance explained %": round(float(pca.explained_variance_ratio_.sum() * 100), 3), "Features": len(features), "Rows": len(X)}, table=table, note="Explained variance is computed after standardising the selected numeric features.", predictions=pd.DataFrame(scores, columns=[f"PC{i + 1}" for i in range(components)]).round(5), metadata={"features": list(features), "components": components, "loadings": loadings.to_dict(orient="records")})
