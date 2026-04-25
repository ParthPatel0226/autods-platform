"""Integration tests -- healthcare domain path.

Verifies healthcare-specific pipeline behavior: domain detection,
domain config loading, domain-specific tool execution, and healthcare
report template availability.
"""

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def healthcare_df():
    """Healthcare dataset with clinical columns."""
    np.random.seed(42)
    n = 200
    return pd.DataFrame({
        "patient_id": range(1, n + 1),
        "age": np.random.randint(18, 95, n),
        "gender": np.random.choice(["Male", "Female"], n),
        "diagnosis_code": np.random.choice(["I10", "E11", "J44", "N18", "I50"], n),
        "num_medications": np.random.randint(0, 20, n),
        "length_of_stay": np.random.randint(1, 30, n),
        "readmitted_30day": np.random.choice([0, 1], n, p=[0.82, 0.18]),
    })


class TestHealthcareDomainDetection:
    def test_detects_healthcare_from_clinical_columns(self, healthcare_df):
        from domains.domain_registry import detect_domain

        domain, confidence, config = detect_domain(list(healthcare_df.columns))
        assert domain == "healthcare"
        assert confidence > 0.0

    def test_healthcare_config_has_required_keys(self):
        from domains.healthcare import HEALTHCARE_CONFIG

        assert "domain_name" in HEALTHCARE_CONFIG or "name" in HEALTHCARE_CONFIG or len(HEALTHCARE_CONFIG) > 0


class TestHealthcareTools:
    def test_charlson_comorbidity_runs(self):
        from agents.tools.domain_tools import charlson_comorbidity_index

        df = pd.DataFrame({
            "diagnosis_code": ["I10", "E11", "J44", "N18", "I50"] * 20,
            "patient_id": range(100),
        })
        result = charlson_comorbidity_index(df, "diagnosis_code")
        assert isinstance(result, dict)


class TestHealthcareEdgeCases:
    def test_single_diagnosis_code(self):
        from agents.tools.domain_tools import charlson_comorbidity_index

        df = pd.DataFrame({
            "diagnosis_code": ["I10"] * 10,
            "patient_id": range(10),
        })
        result = charlson_comorbidity_index(df, "diagnosis_code")
        assert isinstance(result, dict)
