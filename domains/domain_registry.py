"""Domain detection and registry.

Auto-detects the industry domain from column names and data patterns,
and returns the appropriate domain configuration.
"""

import logging
from typing import Any

from domains.base_domain import BaseDomainConfig

logger = logging.getLogger(__name__)


def _get_all_domain_configs() -> list[BaseDomainConfig]:
    """Lazy-load all domain configurations."""
    configs = []

    try:
        from domains.healthcare import HealthcareDomainConfig
        configs.append(HealthcareDomainConfig())
    except ImportError:
        pass

    try:
        from domains.finance import FinanceDomainConfig
        configs.append(FinanceDomainConfig())
    except ImportError:
        pass

    try:
        from domains.ecommerce import EcommerceDomainConfig
        configs.append(EcommerceDomainConfig())
    except ImportError:
        pass

    try:
        from domains.marketing import MarketingDomainConfig
        configs.append(MarketingDomainConfig())
    except ImportError:
        pass

    try:
        from domains.hr import HRDomainConfig
        configs.append(HRDomainConfig())
    except ImportError:
        pass

    try:
        from domains.manufacturing import ManufacturingDomainConfig
        configs.append(ManufacturingDomainConfig())
    except ImportError:
        pass

    return configs


def detect_domain(column_names: list[str], sample_values: dict | None = None) -> tuple[str, float, dict]:
    """Detect industry domain from column names and data patterns.
    
    Args:
        column_names: List of column names in the dataset.
        sample_values: Optional dict of column_name → sample values for pattern matching.
        
    Returns:
        Tuple of (domain_name, confidence_score, domain_config_dict).
        confidence_score is 0.0 to 1.0.
    """
    # Normalize column names for matching
    normalized_cols = [col.lower().replace(" ", "_").replace("-", "_") for col in column_names]
    col_set = set(normalized_cols)

    best_domain = None
    best_score = 0.0
    best_config = None

    for config in _get_all_domain_configs():
        keywords = config.detection_keywords
        score = 0.0

        # Count keyword matches
        strong_matches = sum(
            1 for kw in keywords.get("strong", [])
            if any(kw in col for col in normalized_cols)
        )
        moderate_matches = sum(
            1 for kw in keywords.get("moderate", [])
            if any(kw in col for col in normalized_cols)
        )
        weak_matches = sum(
            1 for kw in keywords.get("weak", [])
            if any(kw in col for col in normalized_cols)
        )

        # Weighted scoring
        score = strong_matches * 3.0 + moderate_matches * 1.5 + weak_matches * 0.5

        logger.debug(
            "Domain %s: strong=%d, moderate=%d, weak=%d, score=%.1f",
            config.domain_name, strong_matches, moderate_matches, weak_matches, score,
        )

        if score > best_score:
            best_score = score
            best_domain = config.domain_name
            best_config = config

    # Fallback to generic
    if best_domain is None or best_score < 3.0:
        from domains.generic import GenericDomainConfig
        generic = GenericDomainConfig()
        return generic.domain_name, 0.0, generic.to_dict()

    # Normalize raw score to 0-1 confidence once: 15+ points = 100%
    confidence = min(best_score / 15.0, 1.0)
    logger.info("Detected domain: %s (confidence: %.2f)", best_domain, confidence)

    return best_domain, confidence, best_config.to_dict()


def get_domain_config(domain_name: str) -> BaseDomainConfig:
    """Get a specific domain configuration by name.
    
    Args:
        domain_name: Domain identifier.
        
    Returns:
        Domain configuration instance.
        
    Raises:
        ValueError: If domain is not found.
    """
    for config in _get_all_domain_configs():
        if config.domain_name == domain_name:
            return config

    if domain_name == "generic":
        from domains.generic import GenericDomainConfig
        return GenericDomainConfig()

    raise ValueError(f"Unknown domain: '{domain_name}'")


def list_available_domains() -> list[dict]:
    """List all available domains with display info."""
    domains = []
    for config in _get_all_domain_configs():
        domains.append({
            "name": config.domain_name,
            "display_name": config.display_name,
            "icon": config.icon,
        })

    from domains.generic import GenericDomainConfig
    generic = GenericDomainConfig()
    domains.append({
        "name": generic.domain_name,
        "display_name": generic.display_name,
        "icon": generic.icon,
    })

    return domains
