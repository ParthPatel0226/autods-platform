"""Domain Detection Agent.

Analyzes column names, data patterns, and value distributions to identify
the industry domain (healthcare, finance, ecommerce, etc.).
"""

import logging
from core.state import AutoDSState
from domains.domain_registry import detect_domain

logger = logging.getLogger(__name__)


def run_domain_detection(state: AutoDSState) -> AutoDSState:
    """Detect the industry domain from loaded data.
    
    Examines column names and sample values to determine
    which domain configuration to use.
    """
    columns = [col.get("name", "") for col in state.get("columns", []) if col.get("name")]
    
    if not columns:
        logger.warning("No columns found in state for domain detection")
        state["detected_domain"] = "generic"
        state["domain_detection_confidence"] = 0.0
        from domains.generic import GenericDomainConfig
        state["domain_config"] = GenericDomainConfig().to_dict()
        return state
    
    domain_name, confidence, config_dict = detect_domain(columns)
    
    state["detected_domain"] = domain_name
    state["domain_detection_confidence"] = confidence
    state["domain_config"] = config_dict
    state["current_step"] = "domain_detection"
    state["completed_steps"] = state.get("completed_steps", []) + ["domain_detection"]
    
    logger.info("Domain detected: %s (confidence: %.2f)", domain_name, confidence)
    
    return state
