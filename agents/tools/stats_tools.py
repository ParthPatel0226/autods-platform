"""Statistical test functions called by agents. Each function is deterministic, independently testable, and returns structured dicts."""

import logging
import math
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from core.constants import VIF_THRESHOLD
from core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _interpret_p_value(p_value: float, alpha: float, test_name: str) -> str:
    """Return a human-readable interpretation of a p-value against a significance level.

    Args:
        p_value: The computed p-value from a statistical test.
        alpha: The significance threshold.
        test_name: Name of the test for contextual messaging.

    Returns:
        A plain-language interpretation string.
    """
    if p_value < 0.001:
        strength = "very strong"
    elif p_value < 0.01:
        strength = "strong"
    elif p_value < alpha:
        strength = "moderate"
    elif p_value < 0.1:
        strength = "weak (marginally non-significant)"
    else:
        strength = "no"

    if p_value < alpha:
        return (
            f"The {test_name} yielded a p-value of {p_value:.4g} (< {alpha}), "
            f"providing {strength} evidence against the null hypothesis. "
            f"The result is statistically significant at the {alpha} level."
        )
    return (
        f"The {test_name} yielded a p-value of {p_value:.4g} (>= {alpha}), "
        f"providing {strength} evidence against the null hypothesis. "
        f"The result is not statistically significant at the {alpha} level."
    )


# ---------------------------------------------------------------------------
# Two-sample tests
# ---------------------------------------------------------------------------

def t_test_independent(
    df: pd.DataFrame,
    numeric_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> dict:
    """Perform an independent two-sample t-test.

    Compares the means of a numeric column across two groups defined by
    a binary grouping column.

    Args:
        df: Input dataframe.
        numeric_col: Column containing the numeric measurements.
        group_col: Column identifying the two groups.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: statistic, p_value, effect_size, ci_lower, ci_upper,
        significant, interpretation.
    """
    try:
        clean = df[[numeric_col, group_col]].dropna()
        groups = clean[group_col].unique()
        if len(groups) != 2:
            raise ToolExecutionError(
                f"Expected exactly 2 groups in '{group_col}', found {len(groups)}."
            )

        g1 = clean.loc[clean[group_col] == groups[0], numeric_col].values
        g2 = clean.loc[clean[group_col] == groups[1], numeric_col].values

        if len(g1) < 2 or len(g2) < 2:
            raise ToolExecutionError(
                "Each group must have at least 2 observations for a t-test."
            )

        t_stat, p_value = stats.ttest_ind(g1, g2, equal_var=False)

        # Cohen's d = (mean1 - mean2) / pooled_std
        n1, n2 = len(g1), len(g2)
        pooled_std = math.sqrt(
            ((n1 - 1) * g1.std(ddof=1) ** 2 + (n2 - 1) * g2.std(ddof=1) ** 2)
            / (n1 + n2 - 2)
        )
        cohens_d = float((g1.mean() - g2.mean()) / pooled_std) if pooled_std > 0 else 0.0

        # CI for the difference in means (Welch)
        mean_diff = float(g1.mean() - g2.mean())
        se_diff = math.sqrt(g1.var(ddof=1) / n1 + g2.var(ddof=1) / n2)
        if se_diff == 0:
            ci_lower = mean_diff
            ci_upper = mean_diff
        else:
            df_welch = (g1.var(ddof=1) / n1 + g2.var(ddof=1) / n2) ** 2 / (
                (g1.var(ddof=1) / n1) ** 2 / (n1 - 1)
                + (g2.var(ddof=1) / n2) ** 2 / (n2 - 1)
            )
            t_crit = stats.t.ppf(1 - alpha / 2, df_welch)
            ci_lower = mean_diff - t_crit * se_diff
            ci_upper = mean_diff + t_crit * se_diff

        significant = bool(p_value < alpha)
        interpretation = _interpret_p_value(p_value, alpha, "independent t-test")

        logger.info(
            "Independent t-test: %s by %s | t=%.4f p=%.4g d=%.3f",
            numeric_col, group_col, t_stat, p_value, cohens_d,
        )

        return {
            "statistic": float(t_stat),
            "p_value": float(p_value),
            "effect_size": cohens_d,
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "significant": significant,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Independent t-test failed: %s", exc)
        raise ToolExecutionError(f"Independent t-test failed: {exc}") from exc


def t_test_paired(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    alpha: float = 0.05,
) -> dict:
    """Perform a paired-sample t-test on two related columns.

    Tests whether the mean difference between paired observations is
    significantly different from zero.

    Args:
        df: Input dataframe.
        col1: First measurement column.
        col2: Second measurement column.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: statistic, p_value, effect_size, mean_diff,
        ci_lower, ci_upper, significant, interpretation.
    """
    try:
        clean = df[[col1, col2]].dropna()
        if len(clean) < 2:
            raise ToolExecutionError(
                "At least 2 complete paired observations are required."
            )

        a = clean[col1].values
        b = clean[col2].values
        diffs = a - b

        # If all differences are zero, ttest_rel returns nan; handle explicitly
        if np.all(diffs == 0):
            t_stat = 0.0
            p_value = 1.0
        else:
            t_stat, p_value = stats.ttest_rel(a, b)

        mean_diff = float(diffs.mean())
        std_diff = float(diffs.std(ddof=1))
        n = len(diffs)

        # Cohen's d for paired design
        cohens_d = mean_diff / std_diff if std_diff > 0 else 0.0

        # CI for mean difference
        se = std_diff / math.sqrt(n)
        t_crit = stats.t.ppf(1 - alpha / 2, n - 1)
        ci_lower = mean_diff - t_crit * se
        ci_upper = mean_diff + t_crit * se

        significant = bool(p_value < alpha)
        interpretation = _interpret_p_value(p_value, alpha, "paired t-test")

        logger.info(
            "Paired t-test: %s vs %s | t=%.4f p=%.4g d=%.3f",
            col1, col2, t_stat, p_value, cohens_d,
        )

        return {
            "statistic": float(t_stat),
            "p_value": float(p_value),
            "effect_size": float(cohens_d),
            "mean_diff": mean_diff,
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "significant": significant,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Paired t-test failed: %s", exc)
        raise ToolExecutionError(f"Paired t-test failed: {exc}") from exc


def mann_whitney_u(
    df: pd.DataFrame,
    numeric_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> dict:
    """Perform a Mann-Whitney U (Wilcoxon rank-sum) test.

    Non-parametric alternative to the independent t-test. Compares the
    distribution of a numeric variable across two groups.

    Args:
        df: Input dataframe.
        numeric_col: Column containing the numeric measurements.
        group_col: Column identifying the two groups.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: statistic, p_value, effect_size, significant,
        interpretation.
    """
    try:
        clean = df[[numeric_col, group_col]].dropna()
        groups = clean[group_col].unique()
        if len(groups) != 2:
            raise ToolExecutionError(
                f"Expected exactly 2 groups in '{group_col}', found {len(groups)}."
            )

        g1 = clean.loc[clean[group_col] == groups[0], numeric_col].values
        g2 = clean.loc[clean[group_col] == groups[1], numeric_col].values

        if len(g1) < 1 or len(g2) < 1:
            raise ToolExecutionError("Each group must have at least 1 observation.")

        u_stat, p_value = stats.mannwhitneyu(g1, g2, alternative="two-sided")

        # Rank-biserial correlation: r = 1 - (2*U) / (n1*n2)
        n1, n2 = len(g1), len(g2)
        rank_biserial = 1.0 - (2.0 * u_stat) / (n1 * n2)

        significant = bool(p_value < alpha)
        interpretation = _interpret_p_value(p_value, alpha, "Mann-Whitney U test")

        logger.info(
            "Mann-Whitney U: %s by %s | U=%.4f p=%.4g r_rb=%.3f",
            numeric_col, group_col, u_stat, p_value, rank_biserial,
        )

        return {
            "statistic": float(u_stat),
            "p_value": float(p_value),
            "effect_size": float(rank_biserial),
            "significant": significant,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Mann-Whitney U test failed: %s", exc)
        raise ToolExecutionError(f"Mann-Whitney U test failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Categorical tests
# ---------------------------------------------------------------------------

def chi_square_test(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    alpha: float = 0.05,
) -> dict:
    """Perform a chi-square test of independence on two categorical columns.

    Tests whether the distribution of one categorical variable is
    independent of another.

    Args:
        df: Input dataframe.
        col1: First categorical column.
        col2: Second categorical column.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: statistic, p_value, dof, expected_frequencies,
        cramers_v, significant, interpretation.
    """
    try:
        clean = df[[col1, col2]].dropna()
        if len(clean) == 0:
            raise ToolExecutionError("No non-null observations for chi-square test.")

        contingency = pd.crosstab(clean[col1], clean[col2])
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

        # Cramer's V = sqrt(chi2 / (n * min(r-1, c-1)))
        n = contingency.values.sum()
        r, c = contingency.shape
        min_dim = min(r - 1, c - 1)
        cramers_v = math.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else 0.0

        significant = bool(p_value < alpha)
        interpretation = _interpret_p_value(p_value, alpha, "chi-square test")

        logger.info(
            "Chi-square test: %s x %s | chi2=%.4f p=%.4g V=%.3f",
            col1, col2, chi2, p_value, cramers_v,
        )

        return {
            "statistic": float(chi2),
            "p_value": float(p_value),
            "dof": int(dof),
            "expected_frequencies": expected.tolist(),
            "cramers_v": float(cramers_v),
            "significant": significant,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Chi-square test failed: %s", exc)
        raise ToolExecutionError(f"Chi-square test failed: {exc}") from exc


def fisher_exact_test(
    df: pd.DataFrame,
    col1: str,
    col2: str,
    alpha: float = 0.05,
) -> dict:
    """Perform Fisher's exact test on a 2x2 contingency table.

    Preferred over chi-square when sample sizes are small or expected
    frequencies are below 5.

    Args:
        df: Input dataframe.
        col1: First categorical column.
        col2: Second categorical column.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: odds_ratio, p_value, significant, interpretation.
    """
    try:
        clean = df[[col1, col2]].dropna()
        contingency = pd.crosstab(clean[col1], clean[col2])

        if contingency.shape != (2, 2):
            raise ToolExecutionError(
                f"Fisher's exact test requires a 2x2 table, got {contingency.shape}."
            )

        odds_ratio, p_value = stats.fisher_exact(contingency.values)

        significant = bool(p_value < alpha)
        interpretation = _interpret_p_value(p_value, alpha, "Fisher's exact test")

        logger.info(
            "Fisher's exact: %s x %s | OR=%.4f p=%.4g",
            col1, col2, odds_ratio, p_value,
        )

        return {
            "odds_ratio": float(odds_ratio),
            "p_value": float(p_value),
            "significant": significant,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Fisher's exact test failed: %s", exc)
        raise ToolExecutionError(f"Fisher's exact test failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Multi-group tests
# ---------------------------------------------------------------------------

def anova_oneway(
    df: pd.DataFrame,
    numeric_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> dict:
    """Perform a one-way ANOVA test.

    Tests whether the means of a numeric variable differ across three
    or more groups.

    Args:
        df: Input dataframe.
        numeric_col: Column containing the numeric measurements.
        group_col: Column identifying the groups (two or more).
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: f_statistic, p_value, eta_squared, group_means,
        significant, interpretation.
    """
    try:
        clean = df[[numeric_col, group_col]].dropna()
        groups = clean[group_col].unique()
        if len(groups) < 2:
            raise ToolExecutionError(
                f"ANOVA requires at least 2 groups, found {len(groups)}."
            )

        samples = [
            clean.loc[clean[group_col] == g, numeric_col].values for g in groups
        ]

        for i, s in enumerate(samples):
            if len(s) < 2:
                raise ToolExecutionError(
                    f"Group '{groups[i]}' has fewer than 2 observations."
                )

        f_stat, p_value = stats.f_oneway(*samples)

        # Eta-squared = SS_between / SS_total
        grand_mean = clean[numeric_col].mean()
        ss_total = float(((clean[numeric_col] - grand_mean) ** 2).sum())
        ss_between = float(
            sum(len(s) * (s.mean() - grand_mean) ** 2 for s in samples)
        )
        eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

        group_means = {
            str(g): float(clean.loc[clean[group_col] == g, numeric_col].mean())
            for g in groups
        }

        significant = bool(p_value < alpha)
        interpretation = _interpret_p_value(p_value, alpha, "one-way ANOVA")

        logger.info(
            "ANOVA: %s by %s | F=%.4f p=%.4g eta2=%.3f",
            numeric_col, group_col, f_stat, p_value, eta_squared,
        )

        return {
            "f_statistic": float(f_stat),
            "p_value": float(p_value),
            "eta_squared": float(eta_squared),
            "group_means": group_means,
            "significant": significant,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("One-way ANOVA failed: %s", exc)
        raise ToolExecutionError(f"One-way ANOVA failed: {exc}") from exc


def kruskal_wallis(
    df: pd.DataFrame,
    numeric_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> dict:
    """Perform a Kruskal-Wallis H-test for independent samples.

    Non-parametric alternative to one-way ANOVA. Tests whether the
    distribution of a numeric variable differs across groups.

    Args:
        df: Input dataframe.
        numeric_col: Column containing the numeric measurements.
        group_col: Column identifying the groups.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: h_statistic, p_value, epsilon_squared, significant,
        interpretation.
    """
    try:
        clean = df[[numeric_col, group_col]].dropna()
        groups = clean[group_col].unique()
        if len(groups) < 2:
            raise ToolExecutionError(
                f"Kruskal-Wallis requires at least 2 groups, found {len(groups)}."
            )

        samples = [
            clean.loc[clean[group_col] == g, numeric_col].values for g in groups
        ]

        h_stat, p_value = stats.kruskal(*samples)

        # Epsilon-squared = H / ((n^2 - 1) / (n + 1))
        n = len(clean)
        epsilon_squared = float(h_stat / ((n ** 2 - 1) / (n + 1))) if n > 1 else 0.0

        significant = bool(p_value < alpha)
        interpretation = _interpret_p_value(p_value, alpha, "Kruskal-Wallis test")

        logger.info(
            "Kruskal-Wallis: %s by %s | H=%.4f p=%.4g eps2=%.3f",
            numeric_col, group_col, h_stat, p_value, epsilon_squared,
        )

        return {
            "h_statistic": float(h_stat),
            "p_value": float(p_value),
            "epsilon_squared": epsilon_squared,
            "significant": significant,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Kruskal-Wallis test failed: %s", exc)
        raise ToolExecutionError(f"Kruskal-Wallis test failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Normality and variance tests
# ---------------------------------------------------------------------------

def shapiro_wilk(
    df: pd.DataFrame,
    column: str,
    alpha: float = 0.05,
) -> dict:
    """Perform a Shapiro-Wilk test for normality.

    Tests the null hypothesis that the data in the given column was
    drawn from a normal distribution.

    Args:
        df: Input dataframe.
        column: Column to test for normality.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: statistic, p_value, is_normal, interpretation.
    """
    try:
        data = df[column].dropna().values
        if len(data) < 3:
            raise ToolExecutionError(
                "Shapiro-Wilk test requires at least 3 observations."
            )

        # scipy caps at 5000; sample if larger
        if len(data) > 5000:
            logger.warning(
                "Column '%s' has %d rows; sampling 5000 for Shapiro-Wilk.",
                column, len(data),
            )
            rng = np.random.default_rng(42)
            data = rng.choice(data, size=5000, replace=False)

        w_stat, p_value = stats.shapiro(data)

        is_normal = bool(p_value >= alpha)
        interpretation = _interpret_p_value(p_value, alpha, "Shapiro-Wilk test")
        if is_normal:
            interpretation += " The data appears consistent with a normal distribution."
        else:
            interpretation += " The data deviates significantly from normality."

        logger.info(
            "Shapiro-Wilk: %s | W=%.4f p=%.4g normal=%s",
            column, w_stat, p_value, is_normal,
        )

        return {
            "statistic": float(w_stat),
            "p_value": float(p_value),
            "is_normal": is_normal,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Shapiro-Wilk test failed: %s", exc)
        raise ToolExecutionError(f"Shapiro-Wilk test failed: {exc}") from exc


def levene_test(
    df: pd.DataFrame,
    numeric_col: str,
    group_col: str,
    alpha: float = 0.05,
) -> dict:
    """Perform Levene's test for equality of variances.

    Tests the null hypothesis that all groups have equal variances.

    Args:
        df: Input dataframe.
        numeric_col: Column containing the numeric measurements.
        group_col: Column identifying the groups.
        alpha: Significance level, by default 0.05.

    Returns:
        Dict with keys: statistic, p_value, equal_variance, interpretation.
    """
    try:
        clean = df[[numeric_col, group_col]].dropna()
        groups = clean[group_col].unique()
        if len(groups) < 2:
            raise ToolExecutionError(
                f"Levene's test requires at least 2 groups, found {len(groups)}."
            )

        samples = [
            clean.loc[clean[group_col] == g, numeric_col].values for g in groups
        ]

        lev_stat, p_value = stats.levene(*samples)

        equal_variance = bool(p_value >= alpha)
        interpretation = _interpret_p_value(p_value, alpha, "Levene's test")
        if equal_variance:
            interpretation += " The assumption of equal variances is supported."
        else:
            interpretation += " The variances differ significantly across groups."

        logger.info(
            "Levene's test: %s by %s | W=%.4f p=%.4g equal=%s",
            numeric_col, group_col, lev_stat, p_value, equal_variance,
        )

        return {
            "statistic": float(lev_stat),
            "p_value": float(p_value),
            "equal_variance": equal_variance,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Levene's test failed: %s", exc)
        raise ToolExecutionError(f"Levene's test failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Correlation tests
# ---------------------------------------------------------------------------

def correlation_pearson(
    df: pd.DataFrame,
    col1: str,
    col2: str,
) -> dict:
    """Compute the Pearson correlation coefficient between two columns.

    Measures linear association between two numeric variables.

    Args:
        df: Input dataframe.
        col1: First numeric column.
        col2: Second numeric column.

    Returns:
        Dict with keys: coefficient, p_value, interpretation.
    """
    try:
        clean = df[[col1, col2]].dropna()
        if len(clean) < 3:
            raise ToolExecutionError(
                "Pearson correlation requires at least 3 observations."
            )

        r, p_value = stats.pearsonr(clean[col1].values, clean[col2].values)

        abs_r = abs(r)
        if abs_r >= 0.8:
            strength = "very strong"
        elif abs_r >= 0.6:
            strength = "strong"
        elif abs_r >= 0.4:
            strength = "moderate"
        elif abs_r >= 0.2:
            strength = "weak"
        else:
            strength = "negligible"

        direction = "positive" if r >= 0 else "negative"
        interpretation = (
            f"Pearson r = {r:.4f} (p = {p_value:.4g}) indicates a "
            f"{strength} {direction} linear relationship between "
            f"'{col1}' and '{col2}'."
        )

        logger.info(
            "Pearson: %s vs %s | r=%.4f p=%.4g", col1, col2, r, p_value
        )

        return {
            "coefficient": float(r),
            "p_value": float(p_value),
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Pearson correlation failed: %s", exc)
        raise ToolExecutionError(f"Pearson correlation failed: {exc}") from exc


def correlation_spearman(
    df: pd.DataFrame,
    col1: str,
    col2: str,
) -> dict:
    """Compute the Spearman rank correlation coefficient between two columns.

    Measures monotonic association between two variables using ranks.

    Args:
        df: Input dataframe.
        col1: First numeric column.
        col2: Second numeric column.

    Returns:
        Dict with keys: coefficient, p_value, interpretation.
    """
    try:
        clean = df[[col1, col2]].dropna()
        if len(clean) < 3:
            raise ToolExecutionError(
                "Spearman correlation requires at least 3 observations."
            )

        rho, p_value = stats.spearmanr(clean[col1].values, clean[col2].values)

        abs_rho = abs(rho)
        if abs_rho >= 0.8:
            strength = "very strong"
        elif abs_rho >= 0.6:
            strength = "strong"
        elif abs_rho >= 0.4:
            strength = "moderate"
        elif abs_rho >= 0.2:
            strength = "weak"
        else:
            strength = "negligible"

        direction = "positive" if rho >= 0 else "negative"
        interpretation = (
            f"Spearman rho = {rho:.4f} (p = {p_value:.4g}) indicates a "
            f"{strength} {direction} monotonic relationship between "
            f"'{col1}' and '{col2}'."
        )

        logger.info(
            "Spearman: %s vs %s | rho=%.4f p=%.4g", col1, col2, rho, p_value
        )

        return {
            "coefficient": float(rho),
            "p_value": float(p_value),
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Spearman correlation failed: %s", exc)
        raise ToolExecutionError(f"Spearman correlation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Distribution tests
# ---------------------------------------------------------------------------

def ks_test(
    df: pd.DataFrame,
    column: str,
    reference_dist: str = "norm",
) -> dict:
    """Perform a one-sample Kolmogorov-Smirnov test against a reference distribution.

    Tests whether the data in the given column follows the specified
    reference distribution.

    Args:
        df: Input dataframe.
        column: Column to test.
        reference_dist: Name of the scipy reference distribution
            (e.g. "norm", "expon"), by default "norm".

    Returns:
        Dict with keys: ks_statistic, p_value, reference_dist, interpretation.
    """
    try:
        data = df[column].dropna().values
        if len(data) < 2:
            raise ToolExecutionError(
                "KS test requires at least 2 observations."
            )

        dist_obj = getattr(stats, reference_dist, None)
        if dist_obj is None:
            raise ToolExecutionError(
                f"Unknown reference distribution: '{reference_dist}'."
            )

        params = dist_obj.fit(data)
        ks_stat, p_value = stats.kstest(data, reference_dist, args=params)

        follows = "consistent with" if p_value >= 0.05 else "not consistent with"
        interpretation = (
            f"KS statistic = {ks_stat:.4f} (p = {p_value:.4g}). "
            f"The data in '{column}' is {follows} a {reference_dist} distribution."
        )

        logger.info(
            "KS test: %s vs %s | D=%.4f p=%.4g",
            column, reference_dist, ks_stat, p_value,
        )

        return {
            "ks_statistic": float(ks_stat),
            "p_value": float(p_value),
            "reference_dist": reference_dist,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("KS test failed: %s", exc)
        raise ToolExecutionError(f"KS test failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Multicollinearity
# ---------------------------------------------------------------------------

def vif_analysis(
    df: pd.DataFrame,
    columns: list[str],
) -> dict:
    """Compute Variance Inflation Factor for each specified column.

    Detects multicollinearity among numeric predictors.

    Args:
        df: Input dataframe.
        columns: List of numeric columns to evaluate for multicollinearity.

    Returns:
        Dict with keys: vif_scores (dict of column -> VIF), high_vif_columns,
        interpretation.
    """
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        from statsmodels.tools import add_constant

        if len(columns) < 2:
            raise ToolExecutionError(
                "VIF analysis requires at least 2 numeric columns."
            )

        clean = df[columns].dropna()
        if len(clean) < len(columns) + 1:
            raise ToolExecutionError(
                "Insufficient observations for VIF analysis "
                f"(need > {len(columns)}, have {len(clean)})."
            )

        X = add_constant(clean.values.astype(float))

        vif_scores: dict[str, float] = {}
        for i, col_name in enumerate(columns):
            try:
                vif_val = variance_inflation_factor(X, i + 1)  # +1 to skip constant
                vif_scores[col_name] = round(float(vif_val), 2)
            except (np.linalg.LinAlgError, Exception):
                logger.warning("VIF calculation failed for '%s' (singular matrix); returning inf", col_name)
                vif_scores[col_name] = float("inf")

        high_vif = [col for col, v in vif_scores.items() if v > VIF_THRESHOLD]

        if high_vif:
            interpretation = (
                f"Columns with VIF > {VIF_THRESHOLD} (high multicollinearity): {high_vif}. "
                "Consider removing or combining these features."
            )
        else:
            interpretation = (
                f"No columns exceed a VIF of {VIF_THRESHOLD}. "
                "Multicollinearity is not a major concern."
            )

        logger.info(
            "VIF analysis on %d columns, %d high VIF", len(columns), len(high_vif)
        )

        return {
            "vif_scores": vif_scores,
            "high_vif_columns": high_vif,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("VIF analysis failed: %s", exc)
        raise ToolExecutionError(f"VIF analysis failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Survival analysis
# ---------------------------------------------------------------------------

def kaplan_meier(
    df: pd.DataFrame,
    duration_col: str,
    event_col: str,
    group_col: Optional[str] = None,
) -> dict:
    """Estimate Kaplan-Meier survival curves.

    Computes non-parametric survival function estimates, optionally
    stratified by group with a log-rank test.

    Args:
        df: Input dataframe.
        duration_col: Column with time-to-event durations.
        event_col: Column indicating whether the event was observed (1)
            or censored (0).
        group_col: Column to stratify survival curves by group,
            by default None.

    Returns:
        Dict with keys: survival_table, median_survival, and optionally
        log_rank_statistic, log_rank_p_value when group_col is provided.
    """
    try:
        from lifelines import KaplanMeierFitter

        required = [duration_col, event_col]
        if group_col is not None:
            required.append(group_col)

        clean = df[required].dropna()
        if len(clean) < 2:
            raise ToolExecutionError(
                "Kaplan-Meier estimation requires at least 2 observations."
            )

        durations = clean[duration_col].values
        events = clean[event_col].values.astype(int)

        result: dict = {}

        if group_col is None:
            kmf = KaplanMeierFitter()
            kmf.fit(durations, event_observed=events)

            surv_table = kmf.survival_function_.reset_index()
            surv_table.columns = ["timeline", "survival_probability"]
            result["survival_table"] = surv_table.to_dict(orient="records")
            result["median_survival"] = (
                float(kmf.median_survival_time_)
                if np.isfinite(kmf.median_survival_time_)
                else None
            )
        else:
            from lifelines.statistics import logrank_test

            groups = clean[group_col].unique()
            survival_tables: dict[str, list] = {}
            medians: dict[str, Optional[float]] = {}

            for g in groups:
                mask = clean[group_col] == g
                kmf = KaplanMeierFitter()
                kmf.fit(
                    clean.loc[mask, duration_col].values,
                    event_observed=clean.loc[mask, event_col].values.astype(int),
                    label=str(g),
                )
                st = kmf.survival_function_.reset_index()
                st.columns = ["timeline", "survival_probability"]
                survival_tables[str(g)] = st.to_dict(orient="records")
                med = kmf.median_survival_time_
                medians[str(g)] = float(med) if np.isfinite(med) else None

            result["survival_table"] = survival_tables
            result["median_survival"] = medians

            if len(groups) == 2:
                g1_mask = clean[group_col] == groups[0]
                lr = logrank_test(
                    clean.loc[g1_mask, duration_col],
                    clean.loc[~g1_mask, duration_col],
                    event_observed_A=clean.loc[g1_mask, event_col].astype(int),
                    event_observed_B=clean.loc[~g1_mask, event_col].astype(int),
                )
                result["log_rank_statistic"] = float(lr.test_statistic)
                result["log_rank_p_value"] = float(lr.p_value)
            elif len(groups) > 2:
                from lifelines.statistics import multivariate_logrank_test

                lr = multivariate_logrank_test(
                    clean[duration_col],
                    clean[group_col],
                    clean[event_col].astype(int),
                )
                result["log_rank_statistic"] = float(lr.test_statistic)
                result["log_rank_p_value"] = float(lr.p_value)

        logger.info(
            "Kaplan-Meier: duration=%s event=%s group=%s",
            duration_col, event_col, group_col,
        )

        return result
    except ToolExecutionError:
        raise
    except ImportError as exc:
        logger.error("lifelines not installed: %s", exc)
        raise ToolExecutionError(
            "lifelines package is required for Kaplan-Meier analysis. "
            "Install with: pip install lifelines"
        ) from exc
    except Exception as exc:
        logger.error("Kaplan-Meier estimation failed: %s", exc)
        raise ToolExecutionError(
            f"Kaplan-Meier estimation failed: {exc}"
        ) from exc


def cox_ph(
    df: pd.DataFrame,
    duration_col: str,
    event_col: str,
    covariates: list[str],
) -> dict:
    """Fit a Cox proportional-hazards model.

    Estimates hazard ratios for the given covariates with respect to
    a survival outcome.

    Args:
        df: Input dataframe.
        duration_col: Column with time-to-event durations.
        event_col: Column indicating whether the event was observed (1)
            or censored (0).
        covariates: List of covariate columns to include in the model.

    Returns:
        Dict with keys: hazard_ratios, confidence_intervals, p_values,
        concordance_index, interpretation.
    """
    try:
        from lifelines import CoxPHFitter

        required = [duration_col, event_col] + list(covariates)
        clean = df[required].dropna()
        if len(clean) <= len(covariates) + 2:
            raise ToolExecutionError(
                "Insufficient observations for Cox PH model."
            )

        cph = CoxPHFitter()
        cph.fit(clean, duration_col=duration_col, event_col=event_col)

        summary = cph.summary

        hazard_ratios = {
            col: round(float(summary.loc[col, "exp(coef)"]), 4)
            for col in covariates
        }
        confidence_intervals = {
            col: [
                round(float(summary.loc[col, "exp(coef) lower 95%"]), 4),
                round(float(summary.loc[col, "exp(coef) upper 95%"]), 4),
            ]
            for col in covariates
        }
        p_values = {
            col: float(summary.loc[col, "p"])
            for col in covariates
        }
        concordance = float(cph.concordance_index_)

        sig_covs = [c for c, p in p_values.items() if p < 0.05]
        if sig_covs:
            interpretation = (
                f"Cox PH model (C-index={concordance:.3f}). "
                f"Significant predictors (p<0.05): {sig_covs}."
            )
        else:
            interpretation = (
                f"Cox PH model (C-index={concordance:.3f}). "
                "No covariates reached significance at the 0.05 level."
            )

        logger.info(
            "Cox PH: %d covariates, C-index=%.3f", len(covariates), concordance
        )

        return {
            "hazard_ratios": hazard_ratios,
            "confidence_intervals": confidence_intervals,
            "p_values": p_values,
            "concordance_index": concordance,
            "interpretation": interpretation,
        }
    except ToolExecutionError:
        raise
    except ImportError as exc:
        logger.error("lifelines not installed: %s", exc)
        raise ToolExecutionError(
            "lifelines package is required for Cox PH analysis. "
            "Install with: pip install lifelines"
        ) from exc
    except Exception as exc:
        logger.error("Cox PH model failed: %s", exc)
        raise ToolExecutionError(f"Cox PH model failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

def correlation_matrix(
    df: pd.DataFrame,
    columns: Optional[list[str]] = None,
    method: str = "pearson",
) -> dict:
    """Compute a correlation matrix for the specified columns.

    Args:
        df: Input dataframe.
        columns: Columns to include. If None, all numeric columns are used.
        method: Correlation method ("pearson", "spearman", or "kendall"),
            by default "pearson".

    Returns:
        Dict with keys: matrix (nested dict), highly_correlated_pairs
        (list of tuples above 0.8 threshold), method.
    """
    try:
        if method not in ("pearson", "spearman", "kendall"):
            raise ToolExecutionError(
                f"Unsupported method '{method}'. "
                "Use 'pearson', 'spearman', or 'kendall'."
            )

        if columns is not None:
            numeric_df = df[columns].select_dtypes(include="number")
        else:
            numeric_df = df.select_dtypes(include="number")

        if numeric_df.shape[1] < 2:
            raise ToolExecutionError(
                "Correlation matrix requires at least 2 numeric columns."
            )

        corr = numeric_df.corr(method=method)

        # Find highly correlated pairs (|r| > 0.8, excluding self-correlation)
        highly_correlated: list[dict] = []
        cols = corr.columns.tolist()
        seen: set[tuple[str, str]] = set()
        for i, c1 in enumerate(cols):
            for j, c2 in enumerate(cols):
                if i >= j:
                    continue
                val = corr.iloc[i, j]
                if abs(val) > 0.8 and (c1, c2) not in seen:
                    seen.add((c1, c2))
                    highly_correlated.append({
                        "col1": c1,
                        "col2": c2,
                        "correlation": round(float(val), 4),
                    })

        highly_correlated.sort(
            key=lambda x: abs(x["correlation"]), reverse=True
        )

        logger.info(
            "Correlation matrix (%s): %d columns, %d high pairs",
            method, len(cols), len(highly_correlated),
        )

        return {
            "matrix": corr.round(4).to_dict(),
            "highly_correlated_pairs": highly_correlated,
            "method": method,
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.error("Correlation matrix failed: %s", exc)
        raise ToolExecutionError(
            f"Correlation matrix failed: {exc}"
        ) from exc
