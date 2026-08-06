"""Descriptive and inferential statistics used by the Analysis workspace."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def describe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    for col in columns:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        rows.append(
            {
                "Column": col,
                "Count": int(s.size),
                "Mean": s.mean(),
                "Median": s.median(),
                "Std": s.std(),
                "Variance": s.var(),
                "Min": s.min(),
                "Q1": s.quantile(0.25),
                "Q3": s.quantile(0.75),
                "Max": s.max(),
                "IQR": s.quantile(0.75) - s.quantile(0.25),
                "Skewness": stats.skew(s, bias=False) if s.size > 2 else np.nan,
                "Kurtosis": stats.kurtosis(s, bias=False) if s.size > 3 else np.nan,
                "CV %": (s.std() / s.mean() * 100) if s.mean() else np.nan,
            }
        )
    return pd.DataFrame(rows).round(4)


def correlation(df: pd.DataFrame, columns: list[str], method: str = "pearson") -> pd.DataFrame:
    numeric = df[columns].apply(pd.to_numeric, errors="coerce")
    return numeric.corr(method=method).round(4)


def frequency(df: pd.DataFrame, column: str, top: int = 25) -> pd.DataFrame:
    counts = df[column].value_counts(dropna=False).head(top)
    out = counts.rename_axis(column).reset_index(name="Count")
    out["Percent"] = (out["Count"] / max(len(df), 1) * 100).round(2)
    return out


def normality(df: pd.DataFrame, column: str) -> dict[str, object]:
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    if s.size < 3:
        return {"error": "At least 3 valid observations are required."}
    stat, p = stats.shapiro(s.sample(5000, random_state=0) if s.size > 5000 else s)
    return {
        "test": "Shapiro-Wilk normality test",
        "n": int(s.size),
        "statistic": round(float(stat), 5),
        "p_value": round(float(p), 6),
        "conclusion": "Data looks normally distributed (p > 0.05)"
        if p > 0.05
        else "Normality rejected (p <= 0.05)",
    }


def t_test(df: pd.DataFrame, a: str, b: str, paired: bool = False) -> dict[str, object]:
    x = pd.to_numeric(df[a], errors="coerce")
    y = pd.to_numeric(df[b], errors="coerce")
    if paired:
        joined = pd.concat([x, y], axis=1).dropna()
        stat, p = stats.ttest_rel(joined.iloc[:, 0], joined.iloc[:, 1])
        name = "Paired t-test"
    else:
        stat, p = stats.ttest_ind(x.dropna(), y.dropna(), equal_var=False)
        name = "Welch two-sample t-test"
    return {
        "test": f"{name}: {a} vs {b}",
        "statistic": round(float(stat), 5),
        "p_value": round(float(p), 6),
        "conclusion": "Significant difference (p <= 0.05)"
        if p <= 0.05
        else "No significant difference (p > 0.05)",
    }


def anova(df: pd.DataFrame, value: str, group: str) -> dict[str, object]:
    groups = [
        pd.to_numeric(g[value], errors="coerce").dropna() for _, g in df.groupby(group)
    ]
    groups = [g for g in groups if g.size > 1]
    if len(groups) < 2:
        return {"error": "At least two groups with more than one observation are required."}
    stat, p = stats.f_oneway(*groups)
    return {
        "test": f"One-way ANOVA: {value} by {group}",
        "groups": len(groups),
        "statistic": round(float(stat), 5),
        "p_value": round(float(p), 6),
        "conclusion": "Group means differ (p <= 0.05)" if p <= 0.05 else "No difference detected",
    }


def chi_square(df: pd.DataFrame, a: str, b: str) -> dict[str, object]:
    table = pd.crosstab(df[a], df[b])
    if table.size == 0:
        return {"error": "Contingency table is empty."}
    stat, p, dof, _ = stats.chi2_contingency(table)
    return {
        "test": f"Chi-square test of independence: {a} vs {b}",
        "statistic": round(float(stat), 5),
        "dof": int(dof),
        "p_value": round(float(p), 6),
        "conclusion": "Variables are dependent (p <= 0.05)"
        if p <= 0.05
        else "No dependence detected (p > 0.05)",
    }


def linear_regression(df: pd.DataFrame, y: str, xs: list[str]) -> dict[str, object]:
    data = df[[y] + xs].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) <= len(xs) + 1:
        return {"error": "Not enough complete observations for this model."}
    X = np.column_stack([np.ones(len(data))] + [data[c].to_numpy() for c in xs])
    target = data[y].to_numpy()
    beta, *_ = np.linalg.lstsq(X, target, rcond=None)
    pred = X @ beta
    resid = target - pred
    ss_res = float(resid @ resid)
    ss_tot = float(((target - target.mean()) ** 2).sum()) or 1.0
    r2 = 1 - ss_res / ss_tot
    n, k = len(data), len(xs)
    adj = 1 - (1 - r2) * (n - 1) / max(n - k - 1, 1)
    coefficients = pd.DataFrame(
        {"Term": ["Intercept"] + xs, "Coefficient": np.round(beta, 6)}
    )
    return {
        "test": f"OLS regression: {y} ~ {' + '.join(xs)}",
        "observations": n,
        "r_squared": round(r2, 5),
        "adj_r_squared": round(adj, 5),
        "rmse": round(float(np.sqrt(ss_res / n)), 5),
        "coefficients": coefficients,
    }
