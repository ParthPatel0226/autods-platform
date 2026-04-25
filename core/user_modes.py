"""User mode logic for Auto, Guided, and Expert modes.

Each mode changes how the pipeline interacts with the user:
- Auto: System makes all decisions, no questions asked
- Guided: System proposes options, user selects from recommendations  
- Expert: User has full control over every parameter
"""

import logging
from typing import Any

from core.constants import MODE_AUTO, MODE_GUIDED, MODE_EXPERT

logger = logging.getLogger(__name__)


def should_ask_questions(user_mode: str) -> bool:
    """Whether the current mode requires asking user questions."""
    return user_mode in (MODE_GUIDED, MODE_EXPERT)


def should_show_recommendations(user_mode: str) -> bool:
    """Whether to show AI recommendations alongside options."""
    return user_mode == MODE_GUIDED


def should_allow_custom_input(user_mode: str) -> bool:
    """Whether to show custom/advanced input fields."""
    return user_mode == MODE_EXPERT


def get_mode_description(user_mode: str) -> dict:
    """Get display info for a mode."""
    modes = {
        MODE_AUTO: {
            "name": "Auto",
            "icon": "🤖",
            "description": "System makes all decisions automatically. Best for quick analysis.",
            "detail": "The AI agents will choose the best cleaning methods, analyses, features, "
                      "and models based on your data and domain. You'll get a complete report "
                      "without any questions.",
        },
        MODE_GUIDED: {
            "name": "Guided",
            "icon": "🎛️",
            "description": "System recommends options, you choose. Best for learning.",
            "detail": "At each step, the system shows you 2-4 recommended approaches with "
                      "explanations of why each is good. You pick the one that fits your needs. "
                      "The system highlights its recommendation.",
        },
        MODE_EXPERT: {
            "name": "Expert",
            "icon": "🔧",
            "description": "Full control over every parameter. Best for experienced data scientists.",
            "detail": "You specify exactly which cleaning methods, statistical tests, features, "
                      "algorithms, and hyperparameters to use. The system executes your choices "
                      "precisely. All options are exposed.",
        },
    }
    return modes.get(user_mode, modes[MODE_GUIDED])


def filter_questions_for_mode(questions: list[dict], user_mode: str) -> list[dict]:
    """Filter and adapt questions based on user mode.
    
    - Auto: No questions returned
    - Guided: Core questions with recommendations highlighted
    - Expert: All questions including advanced options
    """
    if user_mode == MODE_AUTO:
        return []

    filtered = []
    for q in questions:
        q_copy = q.copy()

        if user_mode == MODE_GUIDED:
            # Remove advanced-only questions
            if q_copy.get("expert_only", False):
                continue
            # Ensure recommendations are visible
            q_copy["show_recommendation"] = True

        elif user_mode == MODE_EXPERT:
            # Show everything including advanced options
            q_copy["show_recommendation"] = False
            # Add "custom" option to all single_select questions
            if q_copy.get("type") == "single_select":
                has_custom = any(opt.get("value") == "custom" for opt in q_copy.get("options", []))
                if not has_custom:
                    q_copy.setdefault("options", []).append(
                        {"value": "custom", "label": "Custom — specify manually"}
                    )

        filtered.append(q_copy)

    return filtered


def auto_select_best_option(question: dict, state: dict) -> Any:
    """In Auto mode, select the best option for a question.
    
    Uses the 'recommended' flag on options, or falls back to
    the first option if no recommendation exists.
    """
    options = question.get("options", [])

    # Find the recommended option
    for opt in options:
        if opt.get("recommended", False):
            return opt["value"]

    # Fallback: first non-custom option
    for opt in options:
        if opt.get("value") != "custom":
            return opt["value"]

    # Last resort
    return options[0]["value"] if options else None
