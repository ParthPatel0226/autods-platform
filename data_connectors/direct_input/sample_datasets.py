"""Built-in sample datasets for testing and demos.

Provides ready-to-use datasets so users can test the platform immediately
without finding their own data. Each dataset is designed to showcase
a different domain and problem type.
"""

import logging

import numpy as np
import pandas as pd

from data_connectors.base import BaseConnector

logger = logging.getLogger(__name__)


# ============================================================================
# Sample Dataset Generators
# ============================================================================

def generate_customer_churn(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """E-commerce customer churn dataset."""
    rng = np.random.RandomState(seed)
    return pd.DataFrame({
        "customer_id": range(1, n + 1),
        "age": rng.randint(18, 75, n),
        "gender": rng.choice(["Male", "Female", "Other"], n, p=[0.48, 0.48, 0.04]),
        "tenure_months": rng.randint(1, 72, n),
        "monthly_spend": rng.lognormal(4, 0.8, n).round(2),
        "num_purchases_last_6m": rng.poisson(8, n),
        "avg_order_value": rng.lognormal(3.5, 0.6, n).round(2),
        "num_support_tickets": rng.poisson(1.5, n),
        "days_since_last_purchase": rng.exponential(30, n).astype(int),
        "discount_usage_pct": rng.uniform(0, 0.5, n).round(3),
        "product_category_diversity": rng.randint(1, 10, n),
        "device_type": rng.choice(["mobile", "desktop", "tablet"], n, p=[0.5, 0.35, 0.15]),
        "region": rng.choice(["North", "South", "East", "West"], n),
        "satisfaction_score": rng.choice([1, 2, 3, 4, 5], n, p=[0.05, 0.1, 0.25, 0.35, 0.25]),
        "churned": rng.choice([0, 1], n, p=[0.82, 0.18]),
    })


def generate_hospital_readmission(n: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Healthcare hospital readmission dataset."""
    rng = np.random.RandomState(seed)
    return pd.DataFrame({
        "patient_id": range(1, n + 1),
        "age": rng.randint(18, 95, n),
        "gender": rng.choice(["Male", "Female"], n),
        "race": rng.choice(["White", "Black", "Hispanic", "Asian", "Other"], n,
                           p=[0.55, 0.18, 0.15, 0.08, 0.04]),
        "admission_type": rng.choice(["Emergency", "Elective", "Urgent"], n, p=[0.5, 0.3, 0.2]),
        "insurance_type": rng.choice(["Medicare", "Medicaid", "Private", "Self-Pay"], n,
                                     p=[0.4, 0.2, 0.3, 0.1]),
        "diagnosis_code": rng.choice(["I10", "E11.9", "J44.1", "N18.9", "I50.9", "K21.0",
                                      "J18.9", "I25.10", "E78.5", "M54.5"], n),
        "num_medications": rng.randint(0, 25, n),
        "num_procedures": rng.randint(0, 8, n),
        "num_lab_tests": rng.randint(1, 50, n),
        "length_of_stay": rng.exponential(5, n).astype(int).clip(1, 30),
        "num_prior_admissions_12m": rng.poisson(0.8, n),
        "hemoglobin": rng.normal(12.5, 2.5, n).round(1).clip(5, 20),
        "creatinine": rng.lognormal(0, 0.5, n).round(2).clip(0.3, 10),
        "glucose": rng.normal(120, 40, n).round(0).clip(60, 400).astype(int),
        "bmi": rng.normal(28, 6, n).round(1).clip(15, 55),
        "readmitted_30day": rng.choice([0, 1], n, p=[0.82, 0.18]),
    })


def generate_credit_default(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Finance credit default dataset."""
    rng = np.random.RandomState(seed)
    return pd.DataFrame({
        "application_id": range(1, n + 1),
        "age": rng.randint(21, 70, n),
        "income": rng.lognormal(10.5, 0.7, n).astype(int),
        "employment_length_years": rng.exponential(5, n).round(1).clip(0, 40),
        "home_ownership": rng.choice(["Own", "Mortgage", "Rent"], n, p=[0.2, 0.45, 0.35]),
        "loan_amount": rng.lognormal(9.5, 0.8, n).astype(int),
        "interest_rate": rng.uniform(5, 25, n).round(2),
        "loan_term_months": rng.choice([36, 60], n, p=[0.4, 0.6]),
        "credit_score": rng.normal(680, 80, n).astype(int).clip(300, 850),
        "debt_to_income": rng.uniform(0.05, 0.6, n).round(3),
        "num_credit_lines": rng.randint(1, 30, n),
        "num_delinquencies": rng.poisson(0.3, n),
        "months_since_last_delinquency": rng.exponential(24, n).astype(int).clip(0, 120),
        "credit_utilization": rng.uniform(0, 1, n).round(3),
        "loan_purpose": rng.choice(["debt_consolidation", "home_improvement", "major_purchase",
                                    "medical", "car", "education"], n),
        "defaulted": rng.choice([0, 1], n, p=[0.88, 0.12]),
    })


def generate_employee_attrition(n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """HR employee attrition dataset."""
    rng = np.random.RandomState(seed)
    return pd.DataFrame({
        "employee_id": range(1, n + 1),
        "age": rng.randint(22, 60, n),
        "gender": rng.choice(["Male", "Female", "Non-Binary"], n, p=[0.48, 0.48, 0.04]),
        "department": rng.choice(["Engineering", "Sales", "Marketing", "HR", "Finance", "Support"], n),
        "job_level": rng.choice([1, 2, 3, 4, 5], n, p=[0.3, 0.3, 0.2, 0.12, 0.08]),
        "tenure_years": rng.exponential(4, n).round(1).clip(0.1, 30),
        "monthly_salary": rng.lognormal(8.8, 0.4, n).astype(int),
        "performance_rating": rng.choice([1, 2, 3, 4, 5], n, p=[0.03, 0.12, 0.35, 0.35, 0.15]),
        "satisfaction_score": rng.choice([1, 2, 3, 4, 5], n, p=[0.08, 0.12, 0.25, 0.35, 0.20]),
        "overtime_hours_monthly": rng.exponential(5, n).round(0).clip(0, 40).astype(int),
        "num_projects": rng.randint(1, 8, n),
        "years_since_promotion": rng.exponential(2, n).round(1).clip(0, 10),
        "distance_from_home_km": rng.exponential(10, n).round(0).clip(1, 80).astype(int),
        "training_hours_last_year": rng.poisson(20, n),
        "attrition": rng.choice([0, 1], n, p=[0.84, 0.16]),
    })


def generate_retail_sales(n: int = 10000, seed: int = 42) -> pd.DataFrame:
    """E-commerce retail sales (time-series) dataset."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="h")
    base_demand = 50 + 20 * np.sin(np.arange(n) * 2 * np.pi / 24)  # Daily seasonality
    weekly = 10 * np.sin(np.arange(n) * 2 * np.pi / (24 * 7))  # Weekly seasonality
    trend = np.linspace(0, 15, n)  # Upward trend
    noise = rng.normal(0, 8, n)
    demand = (base_demand + weekly + trend + noise).clip(0).astype(int)

    return pd.DataFrame({
        "timestamp": dates,
        "demand": demand,
        "temperature_f": rng.normal(65, 15, n).round(1),
        "is_holiday": rng.choice([0, 1], n, p=[0.97, 0.03]),
        "is_weekend": [1 if d.weekday() >= 5 else 0 for d in dates],
        "promotion_active": rng.choice([0, 1], n, p=[0.85, 0.15]),
        "price": rng.uniform(10, 50, n).round(2),
        "competitor_price": rng.uniform(10, 50, n).round(2),
        "store_id": rng.choice(["S001", "S002", "S003", "S004"], n),
        "category": rng.choice(["Electronics", "Clothing", "Food", "Home"], n),
    })


def generate_manufacturing_quality(n: int = 4000, seed: int = 42) -> pd.DataFrame:
    """Manufacturing quality control dataset."""
    rng = np.random.RandomState(seed)
    return pd.DataFrame({
        "batch_id": range(1, n + 1),
        "machine_id": rng.choice(["M01", "M02", "M03", "M04", "M05"], n),
        "operator_id": rng.choice([f"OP{i:02d}" for i in range(1, 16)], n),
        "temperature_c": rng.normal(180, 5, n).round(1),
        "pressure_psi": rng.normal(50, 3, n).round(1),
        "vibration_mm_s": rng.exponential(2, n).round(2),
        "humidity_pct": rng.uniform(30, 70, n).round(1),
        "cycle_time_sec": rng.normal(45, 5, n).round(1).clip(20, 80),
        "material_thickness_mm": rng.normal(2.0, 0.1, n).round(3),
        "speed_rpm": rng.normal(1500, 100, n).round(0).astype(int),
        "shift": rng.choice(["Morning", "Afternoon", "Night"], n, p=[0.4, 0.35, 0.25]),
        "day_of_week": rng.choice(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], n),
        "defect": rng.choice([0, 1], n, p=[0.93, 0.07]),
    })


# ============================================================================
# Available Datasets Registry
# ============================================================================

SAMPLE_DATASETS = {
    "customer_churn": {
        "name": "Customer Churn (E-commerce)",
        "description": "5,000 customers with behavioral features and churn labels",
        "domain": "ecommerce",
        "problem_type": "classification",
        "target_column": "churned",
        "generator": generate_customer_churn,
        "rows": 5000,
        "icon": "🛒",
    },
    "hospital_readmission": {
        "name": "Hospital Readmission (Healthcare)",
        "description": "3,000 patients with clinical data and 30-day readmission labels",
        "domain": "healthcare",
        "problem_type": "classification",
        "target_column": "readmitted_30day",
        "generator": generate_hospital_readmission,
        "rows": 3000,
        "icon": "🏥",
    },
    "credit_default": {
        "name": "Credit Default (Finance)",
        "description": "5,000 loan applications with credit features and default labels",
        "domain": "finance",
        "problem_type": "classification",
        "target_column": "defaulted",
        "generator": generate_credit_default,
        "rows": 5000,
        "icon": "💰",
    },
    "employee_attrition": {
        "name": "Employee Attrition (HR)",
        "description": "2,000 employees with workplace features and attrition labels",
        "domain": "hr",
        "problem_type": "classification",
        "target_column": "attrition",
        "generator": generate_employee_attrition,
        "rows": 2000,
        "icon": "👥",
    },
    "retail_sales": {
        "name": "Retail Sales Forecast (E-commerce)",
        "description": "10,000 hourly records with demand, pricing, and external factors",
        "domain": "ecommerce",
        "problem_type": "time_series",
        "target_column": "demand",
        "generator": generate_retail_sales,
        "rows": 10000,
        "icon": "📈",
    },
    "manufacturing_quality": {
        "name": "Manufacturing Quality (Manufacturing)",
        "description": "4,000 production batches with sensor readings and defect labels",
        "domain": "manufacturing",
        "problem_type": "classification",
        "target_column": "defect",
        "generator": generate_manufacturing_quality,
        "rows": 4000,
        "icon": "🏭",
    },
}


class SampleDatasetConnector(BaseConnector):
    """Connector for built-in sample datasets."""

    @property
    def connector_type(self) -> str:
        return "sample"

    @property
    def display_name(self) -> str:
        return "Sample Dataset"

    def validate_config(self, config: dict) -> tuple[bool, str]:
        dataset_name = config.get("dataset_name")
        if not dataset_name:
            return False, "dataset_name is required"
        if dataset_name not in SAMPLE_DATASETS:
            available = ", ".join(SAMPLE_DATASETS.keys())
            return False, f"Unknown dataset: '{dataset_name}'. Available: {available}"
        return True, ""

    def load(self, config: dict) -> pd.DataFrame:
        valid, error = self.validate_config(config)
        if not valid:
            from core.exceptions import DataLoadError
            raise DataLoadError(error)

        dataset_name = config["dataset_name"]
        dataset_info = SAMPLE_DATASETS[dataset_name]
        seed = config.get("seed", 42)
        n = config.get("n_rows", dataset_info["rows"])

        logger.info("Generating sample dataset: %s (%d rows)", dataset_name, n)
        return dataset_info["generator"](n=n, seed=seed)

    def get_preview(self, config: dict, n_rows: int = 5) -> pd.DataFrame:
        preview_config = {**config, "n_rows": n_rows}
        return self.load(preview_config)

    def get_metadata(self, config: dict) -> dict:
        dataset_name = config.get("dataset_name", "")
        info = SAMPLE_DATASETS.get(dataset_name, {})
        return {
            "name": info.get("name", ""),
            "description": info.get("description", ""),
            "domain": info.get("domain", ""),
            "problem_type": info.get("problem_type", ""),
            "target_column": info.get("target_column", ""),
            "rows": info.get("rows", 0),
        }

    @staticmethod
    def list_available() -> list[dict]:
        """List all available sample datasets for the UI."""
        return [
            {
                "key": key,
                "name": info["name"],
                "description": info["description"],
                "domain": info["domain"],
                "problem_type": info["problem_type"],
                "rows": info["rows"],
                "icon": info["icon"],
            }
            for key, info in SAMPLE_DATASETS.items()
        ]
