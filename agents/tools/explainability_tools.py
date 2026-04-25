"""Tool module: explainability_tools

Re-exports explainability utilities from the actual implementation
modules under ``explainability/``.  Agent code can import from here
for a flat namespace.
"""

import logging

logger = logging.getLogger(__name__)

# Re-export public APIs from the canonical implementation modules.
from explainability.shap_explainer import compute_shap_values, shap_summary_plot  # noqa: F401
from explainability.pdp_ice import partial_dependence_plot, ice_plot  # noqa: F401
from explainability.counterfactual import generate_counterfactuals  # noqa: F401
from explainability.fairness_audit import run_fairness_audit  # noqa: F401
from explainability.model_card_generator import generate_model_card  # noqa: F401
from explainability.plain_english import explain_prediction  # noqa: F401
from explainability.what_if import what_if_prediction, what_if_sweep  # noqa: F401
from explainability.adverse_action import generate_adverse_action_codes  # noqa: F401
from explainability.calibration import calibration_curve_data, calibration_plot  # noqa: F401

__all__ = [
    "compute_shap_values",
    "shap_summary_plot",
    "partial_dependence_plot",
    "ice_plot",
    "generate_counterfactuals",
    "run_fairness_audit",
    "generate_model_card",
    "explain_prediction",
    "what_if_prediction",
    "what_if_sweep",
    "generate_adverse_action_codes",
    "calibration_curve_data",
    "calibration_plot",
]
