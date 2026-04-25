"""Abstract base class for domain configurations.

Each industry domain (healthcare, finance, etc.) extends this base
with domain-specific metrics, questions, tools, and compliance rules.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseDomainConfig(ABC):
    """Abstract base for all domain configurations."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Internal domain identifier."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable domain name."""
        ...

    @property
    @abstractmethod
    def icon(self) -> str:
        """Emoji icon for the domain."""
        ...

    @property
    @abstractmethod
    def detection_keywords(self) -> dict[str, list[str]]:
        """Keywords for auto-detecting this domain from column names.
        
        Returns dict with keys 'strong', 'moderate', 'weak' mapping to
        lists of column name keywords.
        """
        ...

    @property
    def detection_threshold(self) -> int:
        """Minimum keyword matches needed for detection. Default: 3 strong or 5 moderate."""
        return 3

    @property
    @abstractmethod
    def primary_metrics(self) -> dict[str, list[str]]:
        """Domain-specific evaluation metrics by problem type.
        
        Example: {"classification": ["sensitivity", "specificity", "auc"]}
        """
        ...

    @property
    def default_cost_matrix(self) -> dict[str, float] | None:
        """Default cost weights for false negatives vs false positives."""
        return None

    @property
    def fairness_config(self) -> dict | None:
        """Fairness analysis configuration."""
        return None

    @property
    def compliance_notes(self) -> list[str]:
        """Compliance/regulatory notes for this domain."""
        return []

    @property
    def terminology_map(self) -> dict[str, str]:
        """Map generic terms to domain-specific terminology.
        
        Example: {"user": "patient", "prediction": "risk assessment"}
        """
        return {}

    @property
    def report_style(self) -> str:
        """Report style identifier."""
        return "standard"

    @abstractmethod
    def get_eda_questions(self, schema_info: dict) -> list[dict]:
        """Get domain-specific EDA questions based on data schema.
        
        Args:
            schema_info: Column names, types, and cardinality info.
            
        Returns:
            List of question dicts for the interactive UI.
        """
        ...

    @abstractmethod
    def get_feature_engineering_questions(self, schema_info: dict) -> list[dict]:
        """Get domain-specific feature engineering questions."""
        ...

    @abstractmethod
    def get_model_questions(self, schema_info: dict, problem_type: str) -> list[dict]:
        """Get domain-specific model configuration questions."""
        ...

    def get_special_encodings(self) -> dict[str, list[str]]:
        """Special column encodings for this domain.
        
        Example: {"icd_codes": ["charlson_index", "ccs_category"]}
        """
        return {}

    def to_dict(self) -> dict:
        """Export domain config as a dict for state storage."""
        return {
            "domain_name": self.domain_name,
            "display_name": self.display_name,
            "icon": self.icon,
            "primary_metrics": self.primary_metrics,
            "default_cost_matrix": self.default_cost_matrix,
            "fairness": self.fairness_config,
            "compliance_notes": self.compliance_notes,
            "terminology_map": self.terminology_map,
            "report_style": self.report_style,
            "special_encodings": self.get_special_encodings(),
            "eda_questions": self.get_eda_questions({}),
            "feature_questions": self.get_feature_engineering_questions({}),
        }
