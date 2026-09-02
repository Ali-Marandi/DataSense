"""Descriptive and inferential statistics used by the Analysis workspace.

Results intentionally include practical uncertainty/effect-size context instead of
relying on p-values alone. All helpers are deterministic for the same input data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna().astype(float)


def _mean_ci(values: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if len(values) < 2:
        return float(values.mean()), float(values.mean())
    mean = float(values.mean())
    sem = float(stats.sem(values))
    margin = float(stats.t.ppf((1.0 + confidence) / 2.0, len(values) - 1) * sem)
    return mean - margin, mean + margin


def _cohens_d_independent(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    pooled_var = ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1)) / max(len(a) + len(b) - 2, 1)
    pooled_sd = float(np.sqrt(max(pooled_var, 0.0)))
    return float((np.mean(a) - np.mean(b)) / pooled_sd) if pooled_sd else 0.0


def _cohens_d_paired(differences: np.ndarray) -> float:
    sd = float(np.std(differences, ddof=1)) if len(differences) > 1 else 0.0
    return float(np.mean(differences) / sd) if sd else 0.0


def _bootstrap_ci(values: np.ndarray, statistic, confidence: float = 0.95, n_resamples: int = 2000, seed: int = 0) -> tuple[float, float]:
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if len(values) < 2:
        raise ValueError("At least two observations are required for bootstrap confidence intervals.")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(int(n_resamples), len(values)))
    samples = values[indices]
    estimates = np.array([statistic(sample) for sample in samples], dtype=float)
    alpha = (1.0 - confidence) / 2.0
    return float(np.quantile(estimates, alpha)), float(np.quantile(estimates, 1.0 - alpha))


def adjust_pvalues(p_values: list[float] | np.ndarray, method: str = "holm") -> np.ndarray:
    """Adjust multiple p-values using a standard deterministic correction."""
    p = np.asarray(p_values, dtype=float)
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("p_values must be finite values between 0 and 1")
    method = method.lower().strip()
    n = len(p)
    if n == 0:
        return p.copy()
    if method == "bonferroni":
        return np.minimum(p * n, 1.0)
    if method not in {"holm", "fdr_bh"}:
        raise ValueError("method must be one of: bonferroni, holm, fdr_bh")
    order = np.argsort(p)
    ranked = p[order]
    if method == "holm":
        adjusted_ranked = np.maximum.accumulate((n - np.arange(n)) * ranked)
    else:
        adjusted_ranked = np.minimum.accumulate((n / np.arange(n, 0, -1)) * ranked[::-1])[::-1]
    out = np.empty_like(p)
    out[order] = np.minimum(adjusted_ranked, 1.0)
    return out


def describe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    for col in columns:
        s = _clean_numeric(df[col])
        if s.empty:
            continue
        rows.append({
            "Column": col,
            "Count": int(s.size), "Mean": s.mean(), "Median": s.median(),
            "Std": s.std(), "Variance": s.var(), "Min": s.min(),
            "Q1": s.quantile(0.25), "Q3": s.quantile(0.75), "Max": s.max(),
            "IQR": s.quantile(0.75) - s.quantile(0.25),
            "Skewness": stats.skew(s, bias=False) if s.size > 2 else np.nan,
            "Kurtosis": stats.kurtosis(s, bias=False) if s.size > 3 else np.nan,
            "CV %": (s.std() / s.mean() * 100) if s.mean() else np.nan,
        })
    return pd.DataFrame(rows).round(4)


def correlation(df: pd.DataFrame, columns: list[str], method: str = "pearson") -> pd.DataFrame:
    if method not in {"pearson", "spearman", "kendall"}:
        raise ValueError("Unsupported correlation method")
    numeric = df[columns].apply(pd.to_numeric, errors="coerce")
    return numeric.corr(method=method).round(4)


def frequency(df: pd.DataFrame, column: str, top: int = 25) -> pd.DataFrame:
    counts = df[column].value_counts(dropna=False).head(top)
    out = counts.rename_axis(column).reset_index(name="Count")
    out["Percent"] = (out["Count"] / max(len(df), 1) * 100).round(2)
    return out


def normality(df: pd.DataFrame, column: str) -> dict[str, object]:
    s = _clean_numeric(df[column])
    if s.size < 3:
        return {"error": "At least 3 valid observations are required."}
    sample = s.sample(5000, random_state=0) if s.size > 5000 else s
    stat, p = stats.shapiro(sample)
    return {
        "test": "Shapiro-Wilk normality test", "n": int(s.size),
        "statistic": round(float(stat), 5), "p_value": round(float(p), 6),
        "conclusion": "Data looks normally distributed (p > 0.05)" if p > 0.05 else "Normality rejected (p <= 0.05)",
    }


def t_test(df: pd.DataFrame, a: str, b: str, paired: bool = False, confidence: float = 0.95) -> dict[str, object]:
    x = _clean_numeric(df[a])
    y = _clean_numeric(df[b])
    if not 0.0 < confidence < 1.0:
        return {"error": "confidence must be between 0 and 1"}
    if paired:
        joined = pd.concat([pd.to_numeric(df[a], errors="coerce"), pd.to_numeric(df[b], errors="coerce")], axis=1).dropna()
        if len(joined) < 2:
            return {"error": "At least 2 complete paired observations are required."}
        x_values, y_values = joined.iloc[:, 0].to_numpy(float), joined.iloc[:, 1].to_numpy(float)
        stat, p = stats.ttest_rel(x_values, y_values)
        diff = x_values - y_values
        low, high = _mean_ci(diff, confidence)
        effect = _cohens_d_paired(diff)
        name = "Paired t-test"
        n = len(diff)
    else:
        if len(x) < 2 or len(y) < 2:
            return {"error": "At least 2 observations per group are required."}
        stat, p = stats.ttest_ind(x, y, equal_var=False)
        diff = x.to_numpy() .mean() - y.to_numpy().mean()
        se = float(np.sqrt(np.var(x, ddof=1) / len(x) + np.var(y, ddof=1) / len(y)))
        df_welch = float((np.var(x, ddof=1) / len(x) + np.var(y, ddof=1) / len(y)) ** 2 / ((np.var(x, ddof=1) / len(x)) ** 2 / (len(x) - 1) + (np.var(y, ddof=1) / len(y)) ** 2 / (len(y) - 1)))
        margin = float(stats.t.ppf((1.0 + confidence) / 2.0, df_welch) * se)
        low, high = diff - margin, diff + margin
        effect = _cohens_d_independent(x.to_numpy(), y.to_numpy())
        name = "Welch two-sample t-test"
        n = min(len(x), len(y))
    return {
        "test": f"{name}: {a} vs {b}", "statistic": round(float(stat), 5),
        "p_value": round(float(p), 6), "effect_size_cohens_d": round(float(effect), 5),
        "mean_difference": round(float(diff if paired else x.mean() - y.mean()), 5),
        "confidence_level": confidence,
        "difference_ci_low": round(float(low), 5), "difference_ci_high": round(float(high), 5),
        "n": int(n),
        "conclusion": "Significant difference (p <= 0.05)" if p <= 0.05 else "No significant difference (p > 0.05)",
    }


def anova(df: pd.DataFrame, value: str, group: str) -> dict[str, object]:
    groups = [_clean_numeric(g[value]) for _, g in df.groupby(group, dropna=False, observed=False)]
    groups = [g for g in groups if g.size > 1]
    if len(groups) < 2:
        return {"error": "At least two groups with more than one observation are required."}
    stat, p = stats.f_oneway(*groups)
    all_values = np.concatenate([g.to_numpy() for g in groups])
    grand_mean = float(all_values.mean())
    between = float(sum(len(g) * (float(g.mean()) - grand_mean) ** 2 for g in groups))
    total = float(((all_values - grand_mean) ** 2).sum()) or 1.0
    eta_sq = between / total
    return {
        "test": f"One-way ANOVA: {value} by {group}", "groups": len(groups),
        "statistic": round(float(stat), 5), "p_value": round(float(p), 6),
        "eta_squared": round(float(eta_sq), 5),
        "conclusion": "Group means differ (p <= 0.05)" if p <= 0.05 else "No difference detected",
    }


def chi_square(df: pd.DataFrame, a: str, b: str) -> dict[str, object]:
    table = pd.crosstab(df[a], df[b])
    if table.size == 0:
        return {"error": "Contingency table is empty."}
    stat, p, dof, _ = stats.chi2_contingency(table)
    n = int(table.to_numpy().sum())
    phi2 = float(stat / n) if n else 0.0
    rows, cols = table.shape
    correction = min(rows - 1, cols - 1)
    cramers_v = float(np.sqrt(phi2 / correction)) if correction > 0 else 0.0
    return {
        "test": f"Chi-square test of independence: {a} vs {b}",
        "statistic": round(float(stat), 5), "dof": int(dof), "p_value": round(float(p), 6),
        "cramers_v": round(cramers_v, 5),
        "conclusion": "Variables are dependent (p <= 0.05)" if p <= 0.05 else "No dependence detected (p > 0.05)",
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
    coefficients = pd.DataFrame({"Term": ["Intercept"] + xs, "Coefficient": np.round(beta, 6)})
    return {
        "test": f"OLS regression: {y} ~ {' + '.join(xs)}",
        "observations": n, "r_squared": round(r2, 5), "adj_r_squared": round(adj, 5),
        "rmse": round(float(np.sqrt(ss_res / n)), 5), "coefficients": coefficients,
    }
