"""Shared pytest fixtures for AutoDS tests."""

import os
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_classification_df():
    """Create a sample classification dataset."""
    np.random.seed(42)
    n = 500
    return pd.DataFrame({
        "age": np.random.randint(18, 80, n),
        "income": np.random.lognormal(10, 1, n).astype(int),
        "gender": np.random.choice(["M", "F"], n),
        "region": np.random.choice(["North", "South", "East", "West"], n),
        "tenure_months": np.random.randint(1, 120, n),
        "num_products": np.random.randint(1, 5, n),
        "has_credit_card": np.random.choice([0, 1], n),
        "is_active": np.random.choice([0, 1], n, p=[0.3, 0.7]),
        "balance": np.random.lognormal(8, 2, n),
        "churned": np.random.choice([0, 1], n, p=[0.8, 0.2]),
    })


@pytest.fixture
def sample_regression_df():
    """Create a sample regression dataset."""
    np.random.seed(42)
    n = 500
    return pd.DataFrame({
        "sqft": np.random.randint(500, 5000, n),
        "bedrooms": np.random.randint(1, 6, n),
        "bathrooms": np.random.randint(1, 4, n),
        "year_built": np.random.randint(1950, 2024, n),
        "neighborhood": np.random.choice(["A", "B", "C", "D"], n),
        "has_garage": np.random.choice([0, 1], n),
        "lot_size": np.random.lognormal(8, 0.5, n).astype(int),
        "price": np.random.lognormal(12, 0.5, n).astype(int),
    })


@pytest.fixture
def sample_healthcare_df():
    """Create a sample healthcare dataset."""
    np.random.seed(42)
    n = 300
    return pd.DataFrame({
        "patient_id": range(1, n + 1),
        "age": np.random.randint(18, 95, n),
        "gender": np.random.choice(["Male", "Female"], n),
        "admission_type": np.random.choice(["Emergency", "Elective", "Urgent"], n),
        "diagnosis_code": np.random.choice(["I10", "E11", "J44", "N18", "I50"], n),
        "num_medications": np.random.randint(0, 20, n),
        "num_procedures": np.random.randint(0, 6, n),
        "length_of_stay": np.random.randint(1, 30, n),
        "insurance_type": np.random.choice(["Medicare", "Medicaid", "Private", "Self-Pay"], n),
        "readmitted_30day": np.random.choice([0, 1], n, p=[0.82, 0.18]),
    })


@pytest.fixture
def tmp_csv(tmp_path, sample_classification_df):
    """Save sample data as CSV and return path."""
    path = tmp_path / "test_data.csv"
    sample_classification_df.to_csv(path, index=False)
    return str(path)
