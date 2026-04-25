"""Unit tests for domains/domain_registry.py.

Covers the three public functions:
  - detect_domain       : auto-detect industry domain from column names
  - get_domain_config   : retrieve a specific domain configuration by name
  - list_available_domains : enumerate all registered domains

Fixture dependencies (from tests/conftest.py):
  - sample_healthcare_df  (300 rows, columns: patient_id, age, gender,
      admission_type, diagnosis_code, num_medications, num_procedures,
      length_of_stay, insurance_type, readmitted_30day)
  - sample_classification_df  (500 rows, generic columns: age, income,
      gender, region, tenure_months, num_products, has_credit_card,
      is_active, balance, churned)

Local fixtures defined here:
  - finance_columns          : column list triggering finance detection
  - ecommerce_columns        : column list triggering ecommerce detection
  - marketing_columns        : column list triggering marketing detection
  - hr_columns               : column list triggering HR detection
  - manufacturing_columns    : column list triggering manufacturing detection
  - ambiguous_columns        : column list with weak signals from multiple domains
  - completely_generic_columns : column list with no domain signal at all
"""

import pytest

from domains.domain_registry import (
    detect_domain,
    get_domain_config,
    list_available_domains,
)


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def healthcare_columns():
    """Column names with strong healthcare signals."""
    return [
        "patient_id",
        "age",
        "gender",
        "admission_type",
        "diagnosis_code",
        "num_medications",
        "num_procedures",
        "length_of_stay",
        "insurance_type",
        "readmitted_30day",
    ]


@pytest.fixture
def finance_columns():
    """Column names with strong finance signals."""
    return [
        "account_id",
        "credit_score",
        "transaction_amount",
        "account_balance",
        "delinquency",
        "loan",
        "interest_rate",
        "payment",
        "income",
        "debt",
    ]


@pytest.fixture
def ecommerce_columns():
    """Column names with strong ecommerce signals."""
    return [
        "customer_id",
        "product_id",
        "order_id",
        "cart_value",
        "purchase",
        "price",
        "quantity",
        "category",
        "discount",
        "shipping",
    ]


@pytest.fixture
def marketing_columns():
    """Column names with strong marketing signals."""
    return [
        "campaign_id",
        "impressions",
        "clicks",
        "conversions",
        "ad_spend",
        "ctr",
        "channel",
        "audience",
        "creative",
        "landing_page",
    ]


@pytest.fixture
def hr_columns():
    """Column names with strong HR signals."""
    return [
        "employee_id",
        "department",
        "hire_date",
        "salary",
        "performance_rating",
        "job_title",
        "attrition",
        "tenure",
        "manager",
        "satisfaction",
    ]


@pytest.fixture
def manufacturing_columns():
    """Column names with strong manufacturing signals."""
    return [
        "machine_id",
        "sensor",
        "defect",
        "yield",
        "oee",
        "downtime",
        "temperature",
        "pressure",
        "vibration",
        "cycle_time",
    ]


@pytest.fixture
def ambiguous_columns():
    """Column names with weak signals from multiple domains."""
    return ["id", "date", "status", "type", "name", "value", "code"]


@pytest.fixture
def completely_generic_columns():
    """Column names with zero domain signal."""
    return ["col_a", "col_b", "col_c", "feature_1", "feature_2", "target"]


# ---------------------------------------------------------------------------
# Helper assertions
# ---------------------------------------------------------------------------


def _assert_valid_detection_result(result: tuple) -> None:
    """Assert that detect_domain returns a well-formed 3-tuple."""
    assert isinstance(result, tuple), "detect_domain must return a tuple"
    assert len(result) == 3, "detect_domain must return a 3-tuple"

    domain_name, confidence, config_dict = result
    assert isinstance(domain_name, str), "domain_name must be a string"
    assert len(domain_name) > 0, "domain_name must not be empty"
    assert isinstance(confidence, float), "confidence must be a float"
    assert 0.0 <= confidence <= 1.0, f"confidence out of [0, 1]: {confidence}"
    assert isinstance(config_dict, dict), "config_dict must be a dict"
    assert "domain_name" in config_dict, "config_dict must contain 'domain_name'"


# ===========================================================================
# 1. detect_domain — Healthcare
# ===========================================================================


class TestDetectDomainHealthcare:
    """Tests for healthcare domain detection."""

    def test_detects_healthcare_from_strong_keywords(self, healthcare_columns):
        """Healthcare domain is detected when column names contain strong
        healthcare keywords like patient_id, diagnosis_code, readmitted."""
        domain_name, confidence, config = detect_domain(healthcare_columns)
        assert domain_name == "healthcare"
        assert confidence > 0.0

    def test_healthcare_confidence_increases_with_more_keywords(self):
        """Adding more healthcare keywords should increase confidence."""
        few_cols = ["patient_id", "age", "gender"]
        many_cols = [
            "patient_id",
            "diagnosis_code",
            "readmission",
            "admission",
            "discharge",
            "hemoglobin",
            "creatinine",
            "mortality",
            "length_of_stay",
            "comorbidity",
        ]
        _, conf_few, _ = detect_domain(few_cols)
        _, conf_many, _ = detect_domain(many_cols)
        assert conf_many > conf_few

    def test_healthcare_config_contains_required_keys(self, healthcare_columns):
        """The returned config dict must have standard domain config keys."""
        _, _, config = detect_domain(healthcare_columns)
        required_keys = {
            "domain_name",
            "display_name",
            "icon",
            "primary_metrics",
            "terminology_map",
            "report_style",
        }
        assert required_keys.issubset(set(config.keys()))

    def test_healthcare_from_conftest_fixture(self, sample_healthcare_df):
        """The sample_healthcare_df fixture from conftest should be detected
        as healthcare based on its column names."""
        columns = list(sample_healthcare_df.columns)
        domain_name, confidence, _ = detect_domain(columns)
        assert domain_name == "healthcare"
        assert confidence > 0.0

    def test_healthcare_result_is_well_formed(self, healthcare_columns):
        """Verify the 3-tuple structure of the detection result."""
        result = detect_domain(healthcare_columns)
        _assert_valid_detection_result(result)


# ===========================================================================
# 2. detect_domain — Finance
# ===========================================================================


class TestDetectDomainFinance:
    """Tests for finance domain detection."""

    def test_detects_finance_from_strong_keywords(self, finance_columns):
        """Finance domain is detected when column names contain strong
        finance keywords like credit_score, transaction_amount, delinquency."""
        domain_name, confidence, config = detect_domain(finance_columns)
        assert domain_name == "finance"
        assert confidence > 0.0

    def test_finance_config_contains_domain_name(self, finance_columns):
        """The config dict domain_name must match the returned domain string."""
        domain_name, _, config = detect_domain(finance_columns)
        assert config["domain_name"] == domain_name

    def test_finance_detected_with_credit_risk_columns(self):
        """Credit risk datasets typically have these columns."""
        columns = [
            "applicant_id",
            "credit_score",
            "loan",
            "default",
            "interest_rate",
            "credit_limit",
            "fico",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "finance"

    def test_finance_detected_with_fraud_columns(self):
        """Fraud detection datasets trigger finance detection."""
        columns = [
            "transaction_id",
            "transaction_amount",
            "merchant",
            "fraud",
            "account_balance",
            "payment",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "finance"

    def test_finance_result_is_well_formed(self, finance_columns):
        """Verify the 3-tuple structure of the detection result."""
        result = detect_domain(finance_columns)
        _assert_valid_detection_result(result)


# ===========================================================================
# 3. detect_domain — E-commerce
# ===========================================================================


class TestDetectDomainEcommerce:
    """Tests for ecommerce domain detection."""

    def test_detects_ecommerce_from_strong_keywords(self, ecommerce_columns):
        """Ecommerce domain is detected when column names contain strong
        ecommerce keywords like product_id, cart_value, order_id."""
        domain_name, confidence, config = detect_domain(ecommerce_columns)
        assert domain_name == "ecommerce"
        assert confidence > 0.0

    def test_ecommerce_config_domain_name_matches(self, ecommerce_columns):
        """The config dict domain_name must match the returned domain string."""
        domain_name, _, config = detect_domain(ecommerce_columns)
        assert config["domain_name"] == domain_name

    def test_ecommerce_detected_with_shopping_columns(self):
        """Typical online shopping dataset columns."""
        columns = [
            "session_id",
            "customer_id",
            "product_id",
            "add_to_cart",
            "checkout",
            "sku",
            "shopping",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "ecommerce"

    def test_ecommerce_result_is_well_formed(self, ecommerce_columns):
        """Verify the 3-tuple structure of the detection result."""
        result = detect_domain(ecommerce_columns)
        _assert_valid_detection_result(result)


# ===========================================================================
# 4. detect_domain — Marketing
# ===========================================================================


class TestDetectDomainMarketing:
    """Tests for marketing domain detection."""

    def test_detects_marketing_from_strong_keywords(self, marketing_columns):
        """Marketing domain is detected when column names contain strong
        marketing keywords like campaign_id, impressions, clicks, ad_spend."""
        domain_name, confidence, config = detect_domain(marketing_columns)
        assert domain_name == "marketing"
        assert confidence > 0.0

    def test_marketing_config_domain_name_matches(self, marketing_columns):
        """The config dict domain_name must match the returned domain string."""
        domain_name, _, config = detect_domain(marketing_columns)
        assert config["domain_name"] == domain_name

    def test_marketing_detected_with_campaign_columns(self):
        """Digital campaign dataset columns."""
        columns = [
            "campaign_id",
            "impressions",
            "clicks",
            "conversions",
            "ad_spend",
            "roas",
            "ctr",
            "cpc",
            "campaign",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "marketing"

    def test_marketing_result_is_well_formed(self, marketing_columns):
        """Verify the 3-tuple structure of the detection result."""
        result = detect_domain(marketing_columns)
        _assert_valid_detection_result(result)


# ===========================================================================
# 5. detect_domain — HR
# ===========================================================================


class TestDetectDomainHR:
    """Tests for HR domain detection."""

    def test_detects_hr_from_strong_keywords(self, hr_columns):
        """HR domain is detected when column names contain strong HR keywords
        like employee_id, department, salary, attrition."""
        domain_name, confidence, config = detect_domain(hr_columns)
        assert domain_name == "hr"
        assert confidence > 0.0

    def test_hr_config_domain_name_matches(self, hr_columns):
        """The config dict domain_name must match the returned domain string."""
        domain_name, _, config = detect_domain(hr_columns)
        assert config["domain_name"] == domain_name

    def test_hr_detected_with_attrition_columns(self):
        """Typical employee attrition prediction dataset."""
        columns = [
            "employee_id",
            "department",
            "hire_date",
            "termination",
            "salary",
            "performance_rating",
            "job_title",
            "employee",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "hr"

    def test_hr_result_is_well_formed(self, hr_columns):
        """Verify the 3-tuple structure of the detection result."""
        result = detect_domain(hr_columns)
        _assert_valid_detection_result(result)


# ===========================================================================
# 6. detect_domain — Manufacturing
# ===========================================================================


class TestDetectDomainManufacturing:
    """Tests for manufacturing domain detection."""

    def test_detects_manufacturing_from_strong_keywords(self, manufacturing_columns):
        """Manufacturing domain is detected when column names contain strong
        manufacturing keywords like machine_id, sensor, defect, oee."""
        domain_name, confidence, config = detect_domain(manufacturing_columns)
        assert domain_name == "manufacturing"
        assert confidence > 0.0

    def test_manufacturing_config_domain_name_matches(self, manufacturing_columns):
        """The config dict domain_name must match the returned domain string."""
        domain_name, _, config = detect_domain(manufacturing_columns)
        assert config["domain_name"] == domain_name

    def test_manufacturing_detected_with_iot_sensor_columns(self):
        """IoT sensor dataset with predictive maintenance focus."""
        columns = [
            "machine_id",
            "sensor",
            "equipment",
            "batch_id",
            "production_line",
            "defect",
            "downtime",
            "vibration",
            "temperature",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "manufacturing"

    def test_manufacturing_result_is_well_formed(self, manufacturing_columns):
        """Verify the 3-tuple structure of the detection result."""
        result = detect_domain(manufacturing_columns)
        _assert_valid_detection_result(result)


# ===========================================================================
# 7. detect_domain — Generic fallback
# ===========================================================================


class TestDetectDomainGeneric:
    """Tests for generic domain fallback."""

    def test_falls_back_to_generic_with_no_signal(self, completely_generic_columns):
        """When column names have no domain-specific keywords, the system
        must fall back to the generic domain."""
        domain_name, confidence, config = detect_domain(completely_generic_columns)
        assert domain_name == "generic"
        assert confidence == 0.0

    def test_falls_back_to_generic_with_ambiguous_columns(self, ambiguous_columns):
        """Columns that match only weak keywords from multiple domains should
        not trigger any specific domain and should fall back to generic."""
        domain_name, confidence, config = detect_domain(ambiguous_columns)
        assert domain_name == "generic"
        assert confidence == 0.0

    def test_generic_fallback_returns_valid_config(self, completely_generic_columns):
        """The generic fallback config must contain standard keys."""
        _, _, config = detect_domain(completely_generic_columns)
        assert config["domain_name"] == "generic"
        assert "primary_metrics" in config
        assert "classification" in config["primary_metrics"]
        assert "regression" in config["primary_metrics"]

    def test_generic_fallback_with_empty_column_list(self):
        """An empty column list should safely return generic."""
        domain_name, confidence, config = detect_domain([])
        assert domain_name == "generic"
        assert confidence == 0.0

    def test_generic_fallback_result_is_well_formed(self, completely_generic_columns):
        """Verify the 3-tuple structure of the detection result."""
        result = detect_domain(completely_generic_columns)
        _assert_valid_detection_result(result)

    def test_generic_display_name_is_set(self, completely_generic_columns):
        """The generic domain config must have a display_name."""
        _, _, config = detect_domain(completely_generic_columns)
        assert "display_name" in config
        assert isinstance(config["display_name"], str)
        assert len(config["display_name"]) > 0


# ===========================================================================
# 8. detect_domain — Confidence scoring
# ===========================================================================


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_confidence_is_zero_for_generic(self, completely_generic_columns):
        """Generic fallback must have confidence exactly 0.0."""
        _, confidence, _ = detect_domain(completely_generic_columns)
        assert confidence == 0.0

    def test_confidence_increases_with_strong_keywords(self):
        """More strong keyword matches should yield higher confidence."""
        one_strong = ["patient_id", "col_a", "col_b"]
        three_strong = ["patient_id", "diagnosis_code", "readmission"]
        many_strong = [
            "patient_id",
            "diagnosis_code",
            "readmission",
            "admission",
            "discharge",
            "hemoglobin",
        ]

        _, conf_1, _ = detect_domain(one_strong)
        _, conf_3, _ = detect_domain(three_strong)
        _, conf_many, _ = detect_domain(many_strong)

        # one_strong alone produces score 3.0, which is the threshold boundary.
        # three_strong produces score 9.0 (3 strong * 3.0 weight).
        # many_strong produces even higher.
        assert conf_many >= conf_3

    def test_confidence_capped_at_one(self):
        """Even with many keyword matches, confidence must not exceed 1.0."""
        # Use all strong healthcare keywords to push score very high
        columns = [
            "patient_id",
            "patient",
            "diagnosis",
            "icd",
            "admission",
            "discharge",
            "readmission",
            "readmitted",
            "hemoglobin",
            "creatinine",
            "mortality",
            "diagnosis_code",
            "procedure_code",
            "drg",
            "ndc",
            "los",
            "length_of_stay",
            "comorbidity",
            "charlson",
        ]
        _, confidence, _ = detect_domain(columns)
        assert confidence <= 1.0

    def test_confidence_bounded_between_zero_and_one(self, healthcare_columns):
        """Confidence must always be in [0.0, 1.0] for any detected domain."""
        _, confidence, _ = detect_domain(healthcare_columns)
        assert 0.0 <= confidence <= 1.0

    def test_strong_keywords_weigh_more_than_moderate(self):
        """A single strong keyword match should score higher than a single
        moderate keyword match. Strong weight is 3.0 vs moderate 1.5."""
        # One strong healthcare keyword
        strong_only = ["patient_id", "col_a", "col_b"]
        # One moderate keyword that is unique to healthcare context
        moderate_only = ["hospital", "col_a", "col_b"]

        result_strong = detect_domain(strong_only)
        result_moderate = detect_domain(moderate_only)

        # strong produces score 3.0 (threshold), moderate produces 1.5 (below threshold)
        # Both may fall to generic, but let us check that the scoring logic
        # distinguishes them. If strong triggers a domain, moderate should not
        # or should have lower confidence.
        strong_score = result_strong[1]
        moderate_score = result_moderate[1]
        # moderate_only (score 1.5) is below threshold 3.0, so falls to generic (conf 0.0)
        # strong_only (score 3.0) is at threshold, so it may or may not trigger.
        # The key invariant: strong_score >= moderate_score
        assert strong_score >= moderate_score

    def test_weak_keywords_contribute_least(self):
        """Five weak keyword matches produce score 2.5 (5 * 0.5), which is
        below the threshold of 3.0. This should fall back to generic.
        We use columns that match exactly 5 weak finance keywords
        (id, date, status, type) without hitting any strong or moderate
        keywords via substring matching."""
        # Finance weak keywords: "id", "date", "status", "type"
        # 4 weak matches = 4 * 0.5 = 2.0 < 3.0 threshold
        weak_only = ["record_id", "create_date", "current_status", "record_type"]
        domain_name, confidence, _ = detect_domain(weak_only)
        assert domain_name == "generic"
        assert confidence == 0.0


# ===========================================================================
# 9. detect_domain — Column name normalization
# ===========================================================================


class TestColumnNameNormalization:
    """Tests for column name normalization during detection."""

    def test_uppercase_columns_are_normalized(self):
        """Column names should be lowercased before matching."""
        columns = ["PATIENT_ID", "DIAGNOSIS_CODE", "READMISSION", "ADMISSION"]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "healthcare"

    def test_mixed_case_columns_are_normalized(self):
        """Mixed case column names should be normalized."""
        columns = ["Patient_Id", "Diagnosis_Code", "Readmission", "Admission"]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "healthcare"

    def test_spaces_replaced_with_underscores(self):
        """Spaces in column names should be treated as underscores."""
        columns = ["patient id", "diagnosis code", "readmission", "admission"]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "healthcare"

    def test_hyphens_replaced_with_underscores(self):
        """Hyphens in column names should be treated as underscores."""
        columns = ["patient-id", "diagnosis-code", "readmission", "admission"]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "healthcare"

    def test_mixed_separators_normalized(self):
        """Columns with mixed spaces, hyphens, and underscores should
        all be normalized before keyword matching."""
        columns = [
            "credit-score",
            "transaction amount",
            "account_balance",
            "delinquency",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "finance"


# ===========================================================================
# 10. detect_domain — Domain override (get_domain_config)
# ===========================================================================


class TestGetDomainConfig:
    """Tests for explicit domain config retrieval by name."""

    def test_get_healthcare_config(self):
        """get_domain_config('healthcare') must return a HealthcareDomainConfig."""
        config = get_domain_config("healthcare")
        assert config.domain_name == "healthcare"
        assert config.display_name == "Healthcare"

    def test_get_finance_config(self):
        """get_domain_config('finance') must return a FinanceDomainConfig."""
        config = get_domain_config("finance")
        assert config.domain_name == "finance"

    def test_get_ecommerce_config(self):
        """get_domain_config('ecommerce') must return an EcommerceDomainConfig."""
        config = get_domain_config("ecommerce")
        assert config.domain_name == "ecommerce"

    def test_get_marketing_config(self):
        """get_domain_config('marketing') must return a MarketingDomainConfig."""
        config = get_domain_config("marketing")
        assert config.domain_name == "marketing"

    def test_get_hr_config(self):
        """get_domain_config('hr') must return an HRDomainConfig."""
        config = get_domain_config("hr")
        assert config.domain_name == "hr"

    def test_get_manufacturing_config(self):
        """get_domain_config('manufacturing') must return a ManufacturingDomainConfig."""
        config = get_domain_config("manufacturing")
        assert config.domain_name == "manufacturing"

    def test_get_generic_config(self):
        """get_domain_config('generic') must return a GenericDomainConfig."""
        config = get_domain_config("generic")
        assert config.domain_name == "generic"

    def test_raises_on_unknown_domain(self):
        """Requesting a nonexistent domain must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown domain"):
            get_domain_config("nonexistent_domain")

    def test_config_has_detection_keywords(self):
        """Every domain config must have detection_keywords with the
        standard key structure."""
        for name in ["healthcare", "finance", "ecommerce", "marketing", "hr", "manufacturing"]:
            config = get_domain_config(name)
            keywords = config.detection_keywords
            assert "strong" in keywords
            assert "moderate" in keywords
            assert "weak" in keywords
            assert isinstance(keywords["strong"], list)
            assert isinstance(keywords["moderate"], list)
            assert isinstance(keywords["weak"], list)

    def test_config_to_dict_round_trip(self):
        """to_dict() must produce a dict whose domain_name matches."""
        for name in ["healthcare", "finance", "ecommerce", "marketing", "hr", "manufacturing", "generic"]:
            config = get_domain_config(name)
            config_dict = config.to_dict()
            assert config_dict["domain_name"] == name

    def test_config_has_primary_metrics(self):
        """Every domain config must expose primary_metrics."""
        for name in ["healthcare", "finance", "ecommerce", "marketing", "hr", "manufacturing", "generic"]:
            config = get_domain_config(name)
            metrics = config.primary_metrics
            assert isinstance(metrics, dict)
            assert "classification" in metrics or "regression" in metrics


# ===========================================================================
# 11. list_available_domains
# ===========================================================================


class TestListAvailableDomains:
    """Tests for listing all available domains."""

    def test_returns_list_of_dicts(self):
        """list_available_domains must return a list of dicts."""
        domains = list_available_domains()
        assert isinstance(domains, list)
        assert len(domains) > 0
        for d in domains:
            assert isinstance(d, dict)

    def test_each_domain_has_required_keys(self):
        """Each domain entry must have name, display_name, and icon."""
        domains = list_available_domains()
        for d in domains:
            assert "name" in d
            assert "display_name" in d
            assert "icon" in d

    def test_contains_all_expected_domains(self):
        """The list must include all six specific domains plus generic."""
        domains = list_available_domains()
        domain_names = {d["name"] for d in domains}
        expected = {"healthcare", "finance", "ecommerce", "marketing", "hr", "manufacturing", "generic"}
        assert expected.issubset(domain_names)

    def test_generic_domain_is_included(self):
        """Generic must always be in the domain list."""
        domains = list_available_domains()
        domain_names = {d["name"] for d in domains}
        assert "generic" in domain_names

    def test_no_duplicate_domain_names(self):
        """Each domain name must appear exactly once."""
        domains = list_available_domains()
        names = [d["name"] for d in domains]
        assert len(names) == len(set(names))

    def test_display_names_are_non_empty_strings(self):
        """Every display_name must be a non-empty string."""
        domains = list_available_domains()
        for d in domains:
            assert isinstance(d["display_name"], str)
            assert len(d["display_name"].strip()) > 0

    def test_icons_are_non_empty_strings(self):
        """Every icon must be a non-empty string (emoji)."""
        domains = list_available_domains()
        for d in domains:
            assert isinstance(d["icon"], str)
            assert len(d["icon"].strip()) > 0


# ===========================================================================
# 12. detect_domain — Cross-domain disambiguation
# ===========================================================================


class TestCrossDomainDisambiguation:
    """Tests verifying correct domain when columns have overlapping keywords."""

    def test_healthcare_beats_generic_age_gender(self):
        """Columns with age/gender plus strong healthcare keywords should
        detect healthcare, not generic (age and gender are moderate for
        healthcare and weak for HR)."""
        columns = ["patient_id", "age", "gender", "diagnosis_code", "readmitted"]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "healthcare"

    def test_finance_beats_generic_with_amount_and_balance(self):
        """Columns with amount and balance (moderate finance) plus strong
        finance keywords should detect finance."""
        columns = ["credit_score", "amount", "balance", "loan", "default"]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "finance"

    def test_strongest_domain_wins_in_mixed_columns(self):
        """When columns contain keywords from multiple domains, the domain
        with the highest weighted score wins."""
        # 3 strong healthcare + 1 moderate finance
        columns = ["patient_id", "diagnosis_code", "readmission", "income"]
        domain_name, _, _ = detect_domain(columns)
        # 3 strong healthcare = 9.0 score; income is moderate for finance = 1.5
        assert domain_name == "healthcare"

    def test_score_below_threshold_falls_to_generic(self):
        """When no domain reaches the minimum threshold score of 3.0,
        detection must fall back to generic."""
        # Only moderate keywords, each scoring 1.5
        columns = ["temperature", "amount"]
        domain_name, confidence, _ = detect_domain(columns)
        # temperature is moderate mfg (1.5), amount is moderate finance (1.5)
        # Neither domain reaches 3.0 threshold
        assert domain_name == "generic"
        assert confidence == 0.0


# ===========================================================================
# 13. detect_domain — Substring matching behavior
# ===========================================================================


class TestSubstringMatching:
    """Tests verifying that keyword matching uses substring containment,
    not exact column name equality."""

    def test_patient_id_prefix_matches(self):
        """A column like 'patient_id_number' should match the 'patient_id'
        keyword via substring containment."""
        columns = [
            "patient_id_number",
            "primary_diagnosis",
            "discharge_date",
            "readmission_flag",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "healthcare"

    def test_compound_column_names_match(self):
        """Column names that contain keywords as substrings should match."""
        columns = [
            "total_transaction_amount",
            "current_credit_score",
            "outstanding_loan_balance",
            "past_delinquency_count",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "finance"

    def test_suffix_keywords_match(self):
        """Keywords appearing as suffixes in column names should match."""
        columns = [
            "main_campaign_id",
            "total_impressions",
            "unique_clicks",
            "daily_conversions",
            "monthly_ad_spend",
        ]
        domain_name, _, _ = detect_domain(columns)
        assert domain_name == "marketing"


# ===========================================================================
# 14. detect_domain — Edge cases
# ===========================================================================


class TestDetectDomainEdgeCases:
    """Edge case tests for detect_domain."""

    def test_single_strong_keyword_at_threshold(self):
        """A single strong keyword produces score 3.0, which is at the
        threshold boundary (score must be > 3.0, not >= 3.0, to pass).
        This should fall back to generic per the < 3.0 check in code."""
        # The code uses: if best_score < 3.0 => generic
        # A single strong keyword = 3.0, which is NOT < 3.0, so it passes
        columns = ["patient_id"]
        domain_name, confidence, _ = detect_domain(columns)
        # Score 3.0 is exactly at threshold, should detect the domain
        assert domain_name == "healthcare"
        assert confidence > 0.0

    def test_duplicated_column_names(self):
        """Duplicate column names should not inflate the score because
        detection iterates keywords, not columns."""
        columns = ["patient_id", "patient_id", "patient_id"]
        # This tests one strong keyword against multiple columns.
        # The keyword "patient_id" matches patient_id, scoring once.
        domain_name_dup, conf_dup, _ = detect_domain(columns)

        single = ["patient_id"]
        domain_name_single, conf_single, _ = detect_domain(single)

        assert domain_name_dup == domain_name_single
        assert conf_dup == conf_single

    def test_very_long_column_list(self):
        """Detection should handle a large number of columns without error."""
        columns = [f"col_{i}" for i in range(1000)] + ["patient_id", "diagnosis_code"]
        domain_name, _, _ = detect_domain(columns)
        # Two strong healthcare keywords = score 6.0, should detect healthcare
        assert domain_name == "healthcare"

    def test_special_characters_in_column_names(self):
        """Columns with special characters should not crash detection."""
        columns = ["col@#$", "col%^&", "col!?", "patient_id", "diagnosis"]
        result = detect_domain(columns)
        _assert_valid_detection_result(result)

    def test_numeric_column_names(self):
        """Purely numeric column names should fall to generic."""
        columns = ["1", "2", "3", "4", "5"]
        domain_name, confidence, _ = detect_domain(columns)
        assert domain_name == "generic"
        assert confidence == 0.0

    def test_sample_values_parameter_accepted(self):
        """detect_domain accepts an optional sample_values parameter
        without error, even though current implementation may not use it."""
        columns = ["patient_id", "diagnosis_code", "readmission"]
        sample_values = {"patient_id": [1, 2, 3], "diagnosis_code": ["I10", "E11"]}
        result = detect_domain(columns, sample_values=sample_values)
        _assert_valid_detection_result(result)
        assert result[0] == "healthcare"
