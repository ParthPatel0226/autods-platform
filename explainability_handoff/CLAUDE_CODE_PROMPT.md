# Prompt to give Claude Code

Copy-paste the block below into Claude Code at the root of your AutoDS project. The `explainability_handoff/` folder must be at the project root.

> **Prerequisites:** Handoffs #1–6 deployed. A trained model exists in the project.

---

```
Read the AutoDS explainability handoff in `explainability_handoff/` thoroughly before writing any code:

1. Start with explainability_handoff/00_START_HERE.md — read all of it.
2. Read every spec file in explainability_handoff/specs/ in order (01 → 09).
3. Open explainability_handoff/reference/explainability_mockup.html in a browser as the visual target. Click between the 7 horizontal section tabs. Try the What-If sliders.

BEFORE writing any component, OPEN the backend module it wraps:
  - explainability/shap_explainer.py — confirm compute_shap_values() signature and return shape
  - explainability/counterfactual.py — confirm generate_counterfactual() signature
  - explainability/what_if.py — confirm predict_modified() signature
  - explainability/fairness_audit.py — confirm run_fairness_audit() signature
  - explainability/model_card_generator.py — confirm generate_model_card() signature
  - explainability/calibration.py — confirm compute_calibration() signature
  - explainability/plain_english.py — confirm generate_explanation() / explain_instance()
  - explainability/adverse_action.py — confirm generate_adverse_action()
  - agents/explainability_agent.py — confirm if handle_followup() exists

If ANY signature differs from what the spec assumes, write an adapter shim in dashboard/components/ex_*_adapter.py. NEVER modify the backend module.

Then implement in this build order:

1. specs/01_layout_and_audience.md → ex_audience_switcher.py + ex_section_tabs.py + CSS
2. specs/02_global_shap.md → ex_global_shap.py + ex_plain_english.py + CSS
3. specs/03_interaction_network.md → ex_interaction_network.py + CSS (the force-directed SVG graph)
4. specs/04_local_explanations.md → ex_local_explanations.py + CSS (waterfall + counterfactual stories)
5. specs/05_whatif_playground.md → ex_whatif_playground.py + CSS (sliders + animated gauge)
6. specs/06_fairness_audit.md → ex_fairness_audit.py + ex_adverse_action.py + CSS
7. specs/07_model_card_calibration.md → ex_model_card.py + ex_calibration.py + CSS
8. specs/08_chat_and_actions.md → ex_chat_composer.py + ex_action_bar.py + CSS
9. specs/09_integration.md → Rewrite pages/06_explainability.py + project_service additions

10. Smoke test:
    - streamlit run dashboard/app.py
    - Login → existing project with trained model → navigate to Explainability.
    - Spinner: "Computing explainability suite..." → all 7 tabs populate.
    - Click each tab: Global SHAP (bar chart + plain English) → Interactions (network graph) → Local (waterfall + counterfactual) → What-If (sliders + gauge) → Fairness (3 metrics + bars) → Model Card (document) → Calibration (diagram + metrics).
    - Audience switcher: Technical → Business → Regulatory.
    - What-If: drag charlson slider → gauge updates smoothly.
    - Local: pick high-risk instance → counterfactual story card renders.
    - Continue to Predict → sidebar updates.

11. Theme test: light mode → all 7 tabs render correctly.
12. Regression: pytest tests/ passes.

Hard rules:
- Do NOT modify anything in explainability/, agents/, domains/, core/, evaluation/, validation/, reports/, serving/, data_connectors/.
- Do NOT modify other dashboard pages.
- All CSS uses `ex-*` prefix. All components use `ex_*` prefix. All session_state keys use `ex_*` prefix.
- Additive CSS only in shared_css.py.

When finished, report: files created/modified, pytest output, API mismatches resolved, deviations.
```

---

## Optional: stage-by-stage

```
Read explainability_handoff/00_START_HERE.md and explainability_handoff/specs/0X_<spec_name>.md.
Implement only that spec. Report files changed and test results.
```
