"""Feature engineering tools. All functions return NEW DataFrames (immutable pattern)."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Encoding (7)
# ---------------------------------------------------------------------------


def one_hot_encode(
    df: pd.DataFrame,
    columns: list[str],
    drop_first: bool = True,
    max_categories: int = 20,
) -> pd.DataFrame:
    """One-hot encode categorical columns.

    Creates binary indicator columns for each category. Columns exceeding
    *max_categories* unique values are skipped with a warning.

    Args:
        df: Input DataFrame (not mutated).
        columns: Categorical columns to encode.
        drop_first: Drop the first category to avoid multicollinearity.
        max_categories: Skip columns with more unique values than this.

    Returns:
        New DataFrame with encoded columns replacing originals.
    """
    result = df.copy()
    cols_to_encode: list[str] = []

    for col in columns:
        n_unique = result[col].nunique()
        if n_unique > max_categories:
            logger.warning(
                "Skipping one-hot encoding for '%s': %d unique values exceeds max_categories=%d",
                col, n_unique, max_categories,
            )
            continue
        cols_to_encode.append(col)

    if not cols_to_encode:
        logger.info("No columns eligible for one-hot encoding")
        return result

    result = pd.get_dummies(result, columns=cols_to_encode, drop_first=drop_first, dtype=int)
    logger.info("One-hot encoded %d columns: %s", len(cols_to_encode), cols_to_encode)
    return result


def target_encode(
    df: pd.DataFrame,
    columns: list[str],
    target_col: str,
    smoothing: int = 10,
) -> pd.DataFrame:
    """Target (mean) encode categorical columns with Bayesian smoothing.

    Replaces each category with the smoothed mean of the target variable for
    that category, blending the category mean with the global mean.

    Args:
        df: Input DataFrame (not mutated).
        columns: Categorical columns to encode.
        target_col: Name of the target column.
        smoothing: Smoothing factor (higher = more regularisation).

    Returns:
        New DataFrame with target-encoded columns.
    """
    result = df.copy()
    global_mean = result[target_col].mean()

    for col in columns:
        stats = result.groupby(col)[target_col].agg(["mean", "count"])
        smoother = (
            stats["count"] * stats["mean"] + smoothing * global_mean
        ) / (stats["count"] + smoothing)
        result[col] = result[col].map(smoother).astype(float)
        logger.info(
            "Target-encoded '%s' (global_mean=%.4f, smoothing=%d)",
            col, global_mean, smoothing,
        )

    return result


def ordinal_encode(
    df: pd.DataFrame,
    columns: list[str],
    order_map: dict | None = None,
) -> pd.DataFrame:
    """Ordinal encode categorical columns preserving a meaningful order.

    If *order_map* is ``None``, categories are sorted alphabetically and
    assigned integers starting from 0.

    Args:
        df: Input DataFrame (not mutated).
        columns: Categorical columns to encode.
        order_map: Optional ``{column: [ordered_categories]}`` mapping.

    Returns:
        New DataFrame with ordinal-encoded columns.
    """
    result = df.copy()

    for col in columns:
        if order_map and col in order_map:
            ordered_cats = order_map[col]
        else:
            ordered_cats = sorted(result[col].dropna().unique())

        cat_to_int = {cat: idx for idx, cat in enumerate(ordered_cats)}
        result[col] = result[col].map(cat_to_int)
        logger.info("Ordinal-encoded '%s' with %d categories", col, len(cat_to_int))

    return result


def binary_encode(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Binary encode categorical columns using binary digit representation.

    Each category is assigned an integer and that integer is represented in
    binary, producing ``ceil(log2(n_categories))`` new columns per input column.

    Args:
        df: Input DataFrame (not mutated).
        columns: Categorical columns to encode.

    Returns:
        New DataFrame with binary-encoded columns replacing originals.
    """
    result = df.copy()

    for col in columns:
        unique_vals = result[col].dropna().unique()
        n_cats = len(unique_vals)
        if n_cats == 0:
            logger.warning("Column '%s' has no non-null values, skipping binary encoding", col)
            continue

        n_bits = max(1, math.ceil(math.log2(n_cats + 1)))
        cat_to_int = {cat: idx + 1 for idx, cat in enumerate(sorted(unique_vals, key=str))}

        codes = result[col].map(cat_to_int).fillna(0).astype(int)

        for bit in range(n_bits):
            bit_col_name = f"{col}_bin_{bit}"
            result[bit_col_name] = codes.apply(lambda x, b=bit: (x >> b) & 1)

        result = result.drop(columns=[col])
        logger.info("Binary-encoded '%s' into %d bit columns", col, n_bits)

    return result


def frequency_encode(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Frequency encode categorical columns.

    Replaces each category with its relative frequency in the column.

    Args:
        df: Input DataFrame (not mutated).
        columns: Categorical columns to encode.

    Returns:
        New DataFrame with frequency-encoded columns.
    """
    result = df.copy()

    for col in columns:
        freq = result[col].value_counts(normalize=True)
        result[col] = result[col].map(freq).astype(float)
        logger.info("Frequency-encoded '%s' (%d categories)", col, len(freq))

    return result


def woe_encode(
    df: pd.DataFrame,
    columns: list[str],
    target_col: str,
) -> pd.DataFrame:
    """Weight of Evidence encode categorical columns.

    Computes WoE for each category using the binary target:
    ``WoE = ln(Distribution of Events / Distribution of Non-Events)``.

    Args:
        df: Input DataFrame (not mutated).
        columns: Categorical columns to encode.
        target_col: Binary target column (0/1).

    Returns:
        New DataFrame with WoE-encoded columns.
    """
    result = df.copy()
    total_events = int(result[target_col].sum())
    total_non_events = int(len(result) - total_events)

    if total_events == 0 or total_non_events == 0:
        logger.error("WoE encoding requires both classes present in target '%s'", target_col)
        return result

    for col in columns:
        grouped = result.groupby(col)[target_col].agg(["sum", "count"])
        grouped.columns = ["events", "total"]
        grouped["non_events"] = grouped["total"] - grouped["events"]

        # Add 0.5 smoothing to avoid division by zero / log(0)
        dist_events = (grouped["events"] + 0.5) / (total_events + 0.5)
        dist_non_events = (grouped["non_events"] + 0.5) / (total_non_events + 0.5)

        woe = np.log(dist_events / dist_non_events)
        result[col] = result[col].map(woe).astype(float)
        logger.info("WoE-encoded '%s'", col)

    return result


def label_encode(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Label encode categorical columns as integer codes.

    Assigns each unique category an integer starting from 0.

    Args:
        df: Input DataFrame (not mutated).
        columns: Categorical columns to encode.

    Returns:
        New DataFrame with label-encoded columns.
    """
    result = df.copy()

    for col in columns:
        result[col] = pd.Categorical(result[col]).codes
        logger.info("Label-encoded '%s'", col)

    return result


# ---------------------------------------------------------------------------
# Scaling (4)
# ---------------------------------------------------------------------------


def standard_scale(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Standardise columns to zero mean and unit variance (z-score).

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to scale.

    Returns:
        New DataFrame with standardised columns.
    """
    from sklearn.preprocessing import StandardScaler

    result = df.copy()
    scaler = StandardScaler()
    result[columns] = scaler.fit_transform(result[columns])
    logger.info("Standard-scaled %d columns", len(columns))
    return result


def minmax_scale(
    df: pd.DataFrame,
    columns: list[str],
    feature_range: tuple = (0, 1),
) -> pd.DataFrame:
    """Scale columns to a given range using min-max normalisation.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to scale.
        feature_range: Desired range ``(min, max)``.

    Returns:
        New DataFrame with min-max scaled columns.
    """
    from sklearn.preprocessing import MinMaxScaler

    result = df.copy()
    scaler = MinMaxScaler(feature_range=feature_range)
    result[columns] = scaler.fit_transform(result[columns])
    logger.info("MinMax-scaled %d columns to range %s", len(columns), feature_range)
    return result


def robust_scale(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Scale columns using median and IQR, robust to outliers.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to scale.

    Returns:
        New DataFrame with robust-scaled columns.
    """
    from sklearn.preprocessing import RobustScaler

    result = df.copy()
    scaler = RobustScaler()
    result[columns] = scaler.fit_transform(result[columns])
    logger.info("Robust-scaled %d columns", len(columns))
    return result


def normalize(
    df: pd.DataFrame,
    columns: list[str],
    norm: str = "l2",
) -> pd.DataFrame:
    """Normalise columns using the specified vector norm.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to normalise.
        norm: Norm to use (``"l1"``, ``"l2"``, or ``"max"``).

    Returns:
        New DataFrame with normalised columns.
    """
    from sklearn.preprocessing import Normalizer

    result = df.copy()
    normalizer = Normalizer(norm=norm)
    result[columns] = normalizer.fit_transform(result[columns])
    logger.info("Normalized %d columns using '%s' norm", len(columns), norm)
    return result


# ---------------------------------------------------------------------------
# Transforms (5)
# ---------------------------------------------------------------------------


def log_transform(
    df: pd.DataFrame,
    columns: list[str],
    base: str = "natural",
) -> pd.DataFrame:
    """Apply logarithmic transform to reduce right skew.

    Adds 1 before taking log to handle zeros (``log1p``).

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to transform.
        base: ``"natural"`` (ln), ``"log2"``, or ``"log10"``.

    Returns:
        New DataFrame with log-transformed columns.
    """
    result = df.copy()

    for col in columns:
        if base == "natural":
            result[col] = np.log1p(result[col])
        elif base == "log2":
            result[col] = np.log2(result[col] + 1)
        elif base == "log10":
            result[col] = np.log10(result[col] + 1)
        else:
            logger.error("Unknown log base '%s', using natural log", base)
            result[col] = np.log1p(result[col])

    logger.info("Log-transformed (%s) %d columns", base, len(columns))
    return result


def box_cox_transform(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Apply Box-Cox power transform (requires strictly positive values).

    The optimal lambda is determined per column via maximum likelihood.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to transform (must be > 0).

    Returns:
        New DataFrame with Box-Cox transformed columns.
    """
    from scipy.stats import boxcox

    result = df.copy()

    for col in columns:
        col_data = result[col].dropna()
        min_val = float(col_data.min())

        if min_val <= 0:
            shift = abs(min_val) + 1.0
            logger.warning(
                "Column '%s' has non-positive values (min=%.4f). Shifting by %.4f for Box-Cox.",
                col, min_val, shift,
            )
            col_data = result[col] + shift
        else:
            col_data = result[col]

        non_null_mask = col_data.notna()
        transformed, lmbda = boxcox(col_data[non_null_mask].values)
        result.loc[non_null_mask, col] = transformed
        logger.info("Box-Cox transformed '%s' (lambda=%.4f)", col, lmbda)

    return result


def yeo_johnson_transform(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Apply Yeo-Johnson power transform (handles zero and negative values).

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to transform.

    Returns:
        New DataFrame with Yeo-Johnson transformed columns.
    """
    from sklearn.preprocessing import PowerTransformer

    result = df.copy()
    pt = PowerTransformer(method="yeo-johnson", standardize=False)
    result[columns] = pt.fit_transform(result[columns])
    logger.info("Yeo-Johnson transformed %d columns", len(columns))
    return result


def sqrt_transform(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Apply square-root transform to reduce moderate right skew.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to transform (must be >= 0).

    Returns:
        New DataFrame with square-root transformed columns.
    """
    result = df.copy()

    for col in columns:
        has_negatives = bool((result[col].dropna() < 0).any())
        if has_negatives:
            logger.warning("Column '%s' contains negative values; clipping to 0 before sqrt", col)
            result[col] = np.sqrt(result[col].clip(lower=0))
        else:
            result[col] = np.sqrt(result[col])

    logger.info("Sqrt-transformed %d columns", len(columns))
    return result


def power_transform(
    df: pd.DataFrame,
    columns: list[str],
    power: float = 2,
) -> pd.DataFrame:
    """Raise columns to an arbitrary power.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to transform.
        power: Exponent to apply.

    Returns:
        New DataFrame with power-transformed columns.
    """
    result = df.copy()

    for col in columns:
        result[col] = np.power(result[col], power)

    logger.info("Power-transformed %d columns (power=%.2f)", len(columns), power)
    return result


# ---------------------------------------------------------------------------
# Feature Creation (8)
# ---------------------------------------------------------------------------


def polynomial_features(
    df: pd.DataFrame,
    columns: list[str],
    degree: int = 2,
    interaction_only: bool = False,
) -> pd.DataFrame:
    """Generate polynomial and interaction features.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to expand.
        degree: Maximum polynomial degree.
        interaction_only: If ``True``, only produce interaction terms.

    Returns:
        New DataFrame with original columns plus polynomial features.
    """
    from sklearn.preprocessing import PolynomialFeatures as PolyFeat

    result = df.copy()
    poly = PolyFeat(degree=degree, interaction_only=interaction_only, include_bias=False)
    poly_array = poly.fit_transform(result[columns])
    poly_names = poly.get_feature_names_out(columns).tolist()

    poly_df = pd.DataFrame(poly_array, columns=poly_names, index=result.index)

    new_cols = [c for c in poly_names if c not in columns]
    for col_name in new_cols:
        result[col_name] = poly_df[col_name]

    logger.info(
        "Generated %d polynomial features (degree=%d, interaction_only=%s)",
        len(new_cols), degree, interaction_only,
    )
    return result


def interaction_features(
    df: pd.DataFrame,
    col_pairs: list[tuple[str, str]],
) -> pd.DataFrame:
    """Create pairwise interaction (product) features for specified column pairs.

    Args:
        df: Input DataFrame (not mutated).
        col_pairs: List of ``(col_a, col_b)`` tuples to multiply.

    Returns:
        New DataFrame with original columns plus interaction columns.
    """
    result = df.copy()

    for col_a, col_b in col_pairs:
        interaction_name = f"{col_a}_x_{col_b}"
        result[interaction_name] = result[col_a] * result[col_b]
        logger.info("Created interaction feature '%s'", interaction_name)

    return result


def date_parts(
    df: pd.DataFrame,
    date_col: str,
) -> pd.DataFrame:
    """Extract date/time components from a datetime column.

    Produces columns for year, month, day, day-of-week, hour (if present),
    quarter, and is-weekend flag.

    Args:
        df: Input DataFrame (not mutated).
        date_col: Name of the datetime column.

    Returns:
        New DataFrame with original columns plus extracted date parts.
    """
    result = df.copy()
    dt_series = pd.to_datetime(result[date_col], errors="coerce")

    result[f"{date_col}_year"] = dt_series.dt.year
    result[f"{date_col}_month"] = dt_series.dt.month
    result[f"{date_col}_day"] = dt_series.dt.day
    result[f"{date_col}_dow"] = dt_series.dt.dayofweek
    result[f"{date_col}_quarter"] = dt_series.dt.quarter
    result[f"{date_col}_is_weekend"] = (dt_series.dt.dayofweek >= 5).astype(int)

    has_time = bool((dt_series.dt.hour != 0).any() or (dt_series.dt.minute != 0).any())
    if has_time:
        result[f"{date_col}_hour"] = dt_series.dt.hour
        logger.info("Extracted date parts (including hour) from '%s'", date_col)
    else:
        logger.info("Extracted date parts (no hour component) from '%s'", date_col)

    return result


def lag_features(
    df: pd.DataFrame,
    column: str,
    lags: list[int],
    sort_col: str | None = None,
) -> pd.DataFrame:
    """Create lag features for time-series or sequential data.

    Args:
        df: Input DataFrame (not mutated).
        column: Column to lag.
        lags: List of lag periods (e.g. ``[1, 7, 30]``).
        sort_col: Column to sort by before lagging (e.g. a date column).

    Returns:
        New DataFrame with original columns plus lag columns.
    """
    result = df.copy()

    if sort_col is not None:
        result = result.sort_values(sort_col).reset_index(drop=True)
        logger.info("Sorted by '%s' before creating lag features", sort_col)

    for lag in lags:
        lag_name = f"{column}_lag_{lag}"
        result[lag_name] = result[column].shift(lag)

    logger.info("Created %d lag features for '%s': %s", len(lags), column, lags)
    return result


def rolling_features(
    df: pd.DataFrame,
    column: str,
    windows: list[int],
    aggs: list[str] | None = None,
) -> pd.DataFrame:
    """Create rolling-window aggregate features.

    Args:
        df: Input DataFrame (not mutated).
        column: Column to aggregate.
        windows: List of window sizes.
        aggs: Aggregation functions (default ``["mean", "std"]``).

    Returns:
        New DataFrame with original columns plus rolling features.
    """
    result = df.copy()

    if aggs is None:
        aggs = ["mean", "std"]

    for window in windows:
        rolling_obj = result[column].rolling(window=window, min_periods=1)
        for agg in aggs:
            feat_name = f"{column}_rolling_{window}_{agg}"
            result[feat_name] = getattr(rolling_obj, agg)()

    logger.info(
        "Created rolling features for '%s': windows=%s, aggs=%s",
        column, windows, aggs,
    )
    return result


def binning(
    df: pd.DataFrame,
    column: str,
    strategy: str = "quantile",
    n_bins: int = 5,
    labels: list | None = None,
) -> pd.DataFrame:
    """Bin a numeric column into discrete intervals.

    Args:
        df: Input DataFrame (not mutated).
        column: Numeric column to bin.
        strategy: ``"quantile"`` (equal-frequency) or ``"uniform"`` (equal-width).
        n_bins: Number of bins.
        labels: Optional labels for the bins.

    Returns:
        New DataFrame with a new binned column appended.
    """
    result = df.copy()
    binned_col_name = f"{column}_binned"

    if strategy == "quantile":
        result[binned_col_name] = pd.qcut(
            result[column], q=n_bins, labels=labels, duplicates="drop",
        )
    elif strategy == "uniform":
        result[binned_col_name] = pd.cut(
            result[column], bins=n_bins, labels=labels, duplicates="drop",
        )
    else:
        logger.error("Unknown binning strategy '%s', using 'quantile'", strategy)
        result[binned_col_name] = pd.qcut(
            result[column], q=n_bins, labels=labels, duplicates="drop",
        )

    logger.info("Binned '%s' into %d bins (strategy='%s')", column, n_bins, strategy)
    return result


def ratio_features(
    df: pd.DataFrame,
    numerator_col: str,
    denominator_col: str,
    name: str | None = None,
) -> pd.DataFrame:
    """Create a ratio feature from two numeric columns.

    Division by zero is replaced with ``NaN``.

    Args:
        df: Input DataFrame (not mutated).
        numerator_col: Column for numerator.
        denominator_col: Column for denominator.
        name: Name for the new column (default ``"<num>_over_<den>"``).

    Returns:
        New DataFrame with the ratio column appended.
    """
    result = df.copy()
    ratio_name = name if name is not None else f"{numerator_col}_over_{denominator_col}"

    result[ratio_name] = result[numerator_col] / result[denominator_col].replace(0, np.nan)
    result[ratio_name] = result[ratio_name].replace([np.inf, -np.inf], np.nan)

    logger.info("Created ratio feature '%s'", ratio_name)
    return result


def text_length_features(
    df: pd.DataFrame,
    text_col: str,
) -> pd.DataFrame:
    """Extract length-based features from a text column.

    Produces columns for character count, word count, and average word length.

    Args:
        df: Input DataFrame (not mutated).
        text_col: Name of the text column.

    Returns:
        New DataFrame with original columns plus text length features.
    """
    result = df.copy()
    text_series = result[text_col].fillna("").astype(str)

    result[f"{text_col}_char_count"] = text_series.str.len()
    result[f"{text_col}_word_count"] = text_series.str.split().str.len().fillna(0).astype(int)
    result[f"{text_col}_avg_word_len"] = (
        result[f"{text_col}_char_count"]
        / result[f"{text_col}_word_count"].replace(0, np.nan)
    ).fillna(0.0)

    logger.info("Extracted text length features from '%s'", text_col)
    return result


# ---------------------------------------------------------------------------
# Imputation (4)
# ---------------------------------------------------------------------------


def impute_mean(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Impute missing values with the column mean.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to impute.

    Returns:
        New DataFrame with missing values filled by mean.
    """
    result = df.copy()

    for col in columns:
        col_mean = result[col].mean()
        n_missing = int(result[col].isna().sum())
        result[col] = result[col].fillna(col_mean)
        if n_missing > 0:
            logger.info("Imputed %d missing values in '%s' with mean=%.4f", n_missing, col, col_mean)

    return result


def impute_median(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Impute missing values with the column median.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to impute.

    Returns:
        New DataFrame with missing values filled by median.
    """
    result = df.copy()

    for col in columns:
        col_median = result[col].median()
        n_missing = int(result[col].isna().sum())
        result[col] = result[col].fillna(col_median)
        if n_missing > 0:
            logger.info("Imputed %d missing values in '%s' with median=%.4f", n_missing, col, col_median)

    return result


def impute_mode(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Impute missing values with the column mode.

    Args:
        df: Input DataFrame (not mutated).
        columns: Columns to impute (works for any dtype).

    Returns:
        New DataFrame with missing values filled by mode.
    """
    result = df.copy()

    for col in columns:
        mode_vals = result[col].mode()
        if mode_vals.empty:
            logger.warning("Column '%s' has no mode (all NaN), skipping imputation", col)
            continue

        col_mode = mode_vals.iloc[0]
        n_missing = int(result[col].isna().sum())
        result[col] = result[col].fillna(col_mode)
        if n_missing > 0:
            logger.info("Imputed %d missing values in '%s' with mode=%s", n_missing, col, col_mode)

    return result


def impute_knn(
    df: pd.DataFrame,
    columns: list[str],
    n_neighbors: int = 5,
) -> pd.DataFrame:
    """Impute missing values using K-Nearest Neighbours.

    Args:
        df: Input DataFrame (not mutated).
        columns: Numeric columns to impute.
        n_neighbors: Number of neighbours to use.

    Returns:
        New DataFrame with KNN-imputed values.
    """
    from sklearn.impute import KNNImputer

    result = df.copy()
    imputer = KNNImputer(n_neighbors=n_neighbors)
    result[columns] = imputer.fit_transform(result[columns])
    logger.info("KNN-imputed %d columns (n_neighbors=%d)", len(columns), n_neighbors)
    return result


# ---------------------------------------------------------------------------
# Selection (2)
# ---------------------------------------------------------------------------


def select_features_importance(
    df: pd.DataFrame,
    target_col: str,
    top_n: int = 20,
) -> pd.DataFrame:
    """Select the top-N features by importance using a tree-based model.

    Fits a lightweight random forest and returns only the columns
    (plus the target) that rank in the top *top_n* by feature importance.

    Args:
        df: Input DataFrame (not mutated).
        target_col: Name of the target column.
        top_n: Number of top features to keep.

    Returns:
        New DataFrame containing only the selected features and the target.
    """
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

    result = df.copy()
    feature_cols = [c for c in result.columns if c != target_col]

    numeric_cols = result[feature_cols].select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        logger.warning("No numeric feature columns found for importance selection")
        return result

    X = result[numeric_cols].fillna(0)
    y = result[target_col]

    if y.nunique() <= 20:
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1)
    else:
        model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1)

    model.fit(X, y)

    importances = pd.Series(model.feature_importances_, index=numeric_cols)
    importances = importances.sort_values(ascending=False)

    top_features = importances.head(top_n).index.tolist()
    non_numeric = [c for c in feature_cols if c not in numeric_cols]
    keep_cols = top_features + [target_col] + non_numeric

    logger.info("Selected top %d features by importance: %s", len(top_features), top_features)
    return result[keep_cols]


def drop_low_variance(
    df: pd.DataFrame,
    threshold: float = 0.01,
) -> pd.DataFrame:
    """Drop numeric columns whose variance falls below a threshold.

    Args:
        df: Input DataFrame (not mutated).
        threshold: Minimum variance to keep a column.

    Returns:
        New DataFrame with low-variance columns removed.
    """
    from sklearn.feature_selection import VarianceThreshold

    result = df.copy()
    numeric_cols = result.select_dtypes(include="number").columns.tolist()

    if not numeric_cols:
        logger.info("No numeric columns found for variance thresholding")
        return result

    selector = VarianceThreshold(threshold=threshold)
    selector.fit(result[numeric_cols].fillna(0))

    kept_mask = selector.get_support()
    dropped_cols = [c for c, keep in zip(numeric_cols, kept_mask) if not keep]

    if dropped_cols:
        result = result.drop(columns=dropped_cols)
        logger.info(
            "Dropped %d low-variance columns (threshold=%.4f): %s",
            len(dropped_cols), threshold, dropped_cols,
        )
    else:
        logger.info("No columns dropped (all variances above %.4f)", threshold)

    return result
