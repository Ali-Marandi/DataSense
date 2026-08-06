"""Machine learning workflows (regression, classification, clustering, PCA)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    silhouette_score,
)
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
    metrics: dict[str, float]
    table: pd.DataFrame | None = None
    note: str = ""
    predictions: pd.DataFrame | None = None


def _prepare(df: pd.DataFrame, target: str, features: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    data = df[features + [target]].copy()
    for col in features:
        if not pd.api.types.is_numeric_dtype(data[col]):
            data[col] = data[col].astype("category").cat.codes
    data = data.dropna()
    return data[features], data[target]


def train_regression(
    df: pd.DataFrame, target: str, features: list[str], model_name: str, test_size: float = 0.2
) -> ModelResult:
    X, y = _prepare(df, target, features)
    y = pd.to_numeric(y, errors="coerce")
    keep = y.notna()
    X, y = X[keep], y[keep]
    if len(X) < 10:
        raise ValueError("At least 10 complete rows are required to train a model.")
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=42)
    model = REGRESSORS[model_name]()
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    cv = cross_val_score(model, X, y, cv=min(5, max(2, len(X) // 5)), scoring="r2")
    table = None
    if hasattr(model, "feature_importances_"):
        table = pd.DataFrame(
            {"Feature": features, "Importance": np.round(model.feature_importances_, 5)}
        ).sort_values("Importance", ascending=False)
    elif hasattr(model, "coef_"):
        table = pd.DataFrame(
            {"Feature": features, "Coefficient": np.round(np.ravel(model.coef_), 5)}
        )
    return ModelResult(
        title=f"{model_name} - predicting {target}",
        metrics={
            "R2 (test)": round(float(r2_score(y_te, pred)), 5),
            "RMSE": round(float(np.sqrt(mean_squared_error(y_te, pred))), 5),
            "MAE": round(float(mean_absolute_error(y_te, pred)), 5),
            "CV R2 (mean)": round(float(cv.mean()), 5),
            "Train rows": len(X_tr),
            "Test rows": len(X_te),
        },
        table=table,
        predictions=pd.DataFrame({"Actual": y_te.to_numpy(), "Predicted": np.round(pred, 5)}),
    )


def train_classification(
    df: pd.DataFrame, target: str, features: list[str], model_name: str, test_size: float = 0.2
) -> ModelResult:
    X, y = _prepare(df, target, features)
    y = y.astype(str)
    if y.nunique() < 2:
        raise ValueError("The target column needs at least two classes.")
    if len(X) < 10:
        raise ValueError("At least 10 complete rows are required to train a model.")
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y if y.value_counts().min() > 1 else None
    )
    model = CLASSIFIERS[model_name](
        **({"max_iter": 1000} if model_name == "Logistic Regression" else {})
    )
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    cm = confusion_matrix(y_te, pred, labels=sorted(y.unique()))
    table = pd.DataFrame(cm, index=[f"true {c}" for c in sorted(y.unique())],
                         columns=[f"pred {c}" for c in sorted(y.unique())]).reset_index(
        names="Class"
    )
    return ModelResult(
        title=f"{model_name} - classifying {target}",
        metrics={
            "Accuracy": round(float(accuracy_score(y_te, pred)), 5),
            "Precision (weighted)": round(
                float(precision_score(y_te, pred, average="weighted", zero_division=0)), 5
            ),
            "Recall (weighted)": round(
                float(recall_score(y_te, pred, average="weighted", zero_division=0)), 5
            ),
            "F1 (weighted)": round(
                float(f1_score(y_te, pred, average="weighted", zero_division=0)), 5
            ),
            "Classes": int(y.nunique()),
            "Test rows": len(X_te),
        },
        table=table,
        note="Confusion matrix on the held-out test split.",
    )


def run_clustering(df: pd.DataFrame, features: list[str], k: int = 3) -> ModelResult:
    X = df[features].apply(pd.to_numeric, errors="coerce").dropna()
    if len(X) < k:
        raise ValueError("Fewer complete rows than requested clusters.")
    scaled = StandardScaler().fit_transform(X)
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(scaled)
    sil = silhouette_score(scaled, labels) if k > 1 and len(set(labels)) > 1 else float("nan")
    sizes = pd.Series(labels).value_counts().sort_index()
    table = pd.DataFrame({"Cluster": sizes.index, "Size": sizes.to_numpy()})
    centers = pd.DataFrame(model.cluster_centers_, columns=features).round(4)
    centers.insert(0, "Cluster", range(k))
    return ModelResult(
        title=f"K-Means clustering (k={k})",
        metrics={
            "Silhouette score": round(float(sil), 5) if sil == sil else "n/a",
            "Inertia": round(float(model.inertia_), 4),
            "Rows clustered": len(X),
        },
        table=centers,
        note="Cluster centroids in standardised feature space.",
        predictions=pd.concat(
            [X.reset_index(drop=True), pd.Series(labels, name="Cluster")], axis=1
        ),
    )


def run_pca(df: pd.DataFrame, features: list[str], components: int = 2) -> ModelResult:
    X = df[features].apply(pd.to_numeric, errors="coerce").dropna()
    components = min(components, len(features), max(len(X) - 1, 1))
    scaled = StandardScaler().fit_transform(X)
    pca = PCA(n_components=components)
    scores = pca.fit_transform(scaled)
    table = pd.DataFrame(
        {
            "Component": [f"PC{i + 1}" for i in range(components)],
            "Explained variance %": np.round(pca.explained_variance_ratio_ * 100, 3),
            "Cumulative %": np.round(np.cumsum(pca.explained_variance_ratio_) * 100, 3),
        }
    )
    return ModelResult(
        title=f"Principal component analysis ({components} components)",
        metrics={
            "Total variance explained %": round(
                float(pca.explained_variance_ratio_.sum() * 100), 3
            ),
            "Features": len(features),
            "Rows": len(X),
        },
        table=table,
        predictions=pd.DataFrame(
            scores, columns=[f"PC{i + 1}" for i in range(components)]
        ).round(5),
    )
