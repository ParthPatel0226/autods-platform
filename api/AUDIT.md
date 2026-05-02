# AutoDS API — Final Audit

**Date:** 2026-05-02
**API version:** 1.0.0
**OpenAPI paths:** 47
**pytest:** 18 passed, 1 skipped, 0 failures

---

## a. Endpoint Inventory (47 total)

```
METHOD  PATH                                               OPERATION-ID
-----------------------------------------------------------------------
POST    /auth/signup                                       signup_auth_signup_post
POST    /auth/login                                        login_auth_login_post
GET     /auth/me                                           me_auth_me_get

POST    /projects/                                         create_project_projects__post
GET     /projects/                                         list_projects_projects__get
GET     /projects/{project_id}                             get_project_projects__project_id__get
PATCH   /projects/{project_id}                             update_project_projects__project_id__patch
DELETE  /projects/{project_id}                             delete_project_projects__project_id__delete
POST    /projects/{project_id}/activate                    activate_project_projects__project_id__activate_post

POST    /upload/file                                       upload_file_upload_file_post
GET     /upload/samples                                    list_samples_upload_samples_get
POST    /upload/samples                                    load_sample_upload_samples_post
POST    /upload/connector                                   load_connector_upload_connector_post
POST    /upload/join/suggest                               suggest_join_upload_join_suggest_post
POST    /upload/join/apply                                 apply_join_upload_join_apply_post
GET     /upload/preview/{source_id}                        preview_source_upload_preview__source_id__get

POST    /configure/detect-domain                           detect_domain_configure_detect_domain_post
POST    /configure/set-target                              set_target_configure_set_target_post
POST    /configure/start-pipeline                          start_pipeline_configure_start_pipeline_post

POST    /eda/generate-questions                            generate_questions_eda_generate_questions_post
POST    /eda/answer                                        answer_questions_eda_answer_post
POST    /eda/run                                           run_eda_eda_run_post
GET     /eda/results/{project_id}                          get_results_eda_results__project_id__get

POST    /fe/suggest                                        suggest_decisions_fe_suggest_post
POST    /fe/apply                                          apply_decisions_fe_apply_post
GET     /fe/results/{project_id}                           get_results_fe_results__project_id__get

POST    /modeling/configure                                configure_modeling_modeling_configure_post
POST    /modeling/train                                    train_models_modeling_train_post
POST    /modeling/select-best                              select_best_modeling_select_best_post
GET     /modeling/leaderboard/{project_id}                 get_leaderboard_modeling_leaderboard__project_id__get

POST    /explain/shap                                      compute_shap_explain_shap_post
POST    /explain/fairness                                  fairness_audit_explain_fairness_post
POST    /explain/whatif                                    whatif_explain_whatif_post
GET     /explain/model-card/{project_id}                   get_model_card_explain_model_card__project_id__get

POST    /predict/single                                    predict_single_predict_single_post
POST    /predict/batch                                     predict_batch_predict_batch_post

POST    /chat/message                                      send_message_chat_message_post
GET     /chat/history/{project_id}                         get_history_chat_history__project_id__get
DELETE  /chat/history/{project_id}                         clear_history_chat_history__project_id__delete

POST    /download/report                                   generate_report_download_report_post
GET     /download/file/{report_id}                         download_file_download_file__report_id__get

GET     /jobs/{job_id}                                     get_job_status_jobs__job_id__get
GET     /jobs/{job_id}/result                              get_job_result_jobs__job_id__result_get
GET     /jobs/{job_id}/stream                              stream_job_jobs__job_id__stream_get
DELETE  /jobs/{job_id}                                     cancel_job_jobs__job_id__delete

GET     /meta/tools                                        list_tools_meta_tools_get
GET     /meta/tools/{tool_name}                            get_tool_meta_tools__tool_name__get
GET     /meta/domains                                      get_domain_configs_meta_domains_get
GET     /meta/agent-prompts                                get_agent_prompts_meta_agent_prompts_get
GET     /meta/pipeline-log/{project_id}                    get_pipeline_log_meta_pipeline_log__project_id__get
GET     /meta/costs/{project_id}                           get_cost_summary_meta_costs__project_id__get

GET     /health                                            health_health_get
GET     /                                                  root__get
```

---

## b. Files Changed Outside api/ and frontend/lib/

```
.gitignore
```

Only change: two Windows-reserved filename entries (`nul`, `NUL`) added to prevent
accidental commits of reserved filesystem names on Windows. No functional code
outside the API layer was touched.

---

## c. Backend Modules Imported in api/services/

| Service | Backend module(s) imported |
|---|---|
| `chat_service` | `agents.followup_agent` |
| `eda_service` | `agents.eda_agent` |
| `explainability_service` | `explainability.shap_explainer`, `explainability.fairness_audit`, `explainability.counterfactual`, `explainability.model_card_generator` |
| `fe_service` | `agents.feature_engineer` |
| `meta_service` | `agents.tools.tool_registry`, `configs.loader` |
| `modeling_service` | `agents.modeling_agent`, `evaluation.model_comparator` |
| `predict_service` | `explainability.shap_explainer`, `serving.model_loader` |
| `report_service` | `agents.report_agent`, `reports.generators.*` |
| `state_service` | `session.session_manager` (stdlib only beyond that) |
| `upload_service` | `data_connectors.*`, `agents.domain_detector` |

All services also import `core.exceptions.AutoDSError` and `api.services.state_service`.

---

## d. TODO Comments in api/

| File | Line | Note |
|---|---|---|
| `api/dependencies.py` | 90 | `get_current_project` stub — Phase 3.5 placeholder; superseded by per-route ownership checks |
| `api/main.py` | 167 | Message-based HTTP routing fallback — remove once `ResourceNotFoundError` / `AuthorizationError` added to `core/exceptions.py` |
| `api/routes/meta.py` | 178 | Cost endpoint role check deferred until roles system exists |
| `api/services/state_service.py` | 28 | Migrate string-based error raises to typed exceptions once upstream adds `ResourceNotFoundError` |

None of these block production deployment. All are tracked for Phase 2.

---

## e. Backend Signature Differences vs. OpenAPI Spec

A pre-build signature audit was committed (`api: backend signature audit`) before any
route was written. No regressions were introduced during implementation. Specific
verified items:

| Function | Declared return type | OpenAPI response_model | Match |
|---|---|---|---|
| `state_service.create_state` | `dict` | Project (mapped via `_state_to_project`) | ✓ |
| `state_service.load_state` | `dict` | Project | ✓ |
| `eda_agent.generate_eda_questions` | `list[dict]` | `list[EDAQuestion]` | ✓ |
| `feature_engineer.suggest_fe_decisions` | `list[dict]` | `list[FESuggestion]` | ✓ |
| `modeling_agent.get_leaderboard` | `dict` | `Leaderboard` | ✓ |
| `shap_explainer.compute_shap_values` | `dict` | nested in `SHAPRequest` response | ✓ |
| `report_agent.generate_reports` | `dict[str, str]` (paths) | `ReportJobResponse` | ✓ |
| `followup_agent.handle_followup` | `str` | `ChatResponse.reply` | ✓ |

Three minor discrepancies fixed during implementation (all in prior session):
- `_state_to_project()`: `user_mode=None` → `or "auto"` fallback
- `_state_to_project()`: `updated_at=None` → falls back to `created_at`
- `dependencies.py`: `dev@local` → `dev@example.com` (Pydantic `EmailStr` validation)

---

## f. Uvicorn / /docs Verification

Server started on port 9999. `/openapi.json` confirmed:

```
PATH COUNT : 47
TAG SECTIONS: auth, chat, configure, download, eda, explainability,
              feature-engineering, jobs, meta, modeling, predict,
              projects, upload
```

All 13 required tag sections present. `/docs` (Swagger UI) renders every section.

---

## g. pytest Final Run

```
platform win32 — Python 3.14.2, pytest 9.0.3
collected 19 items

test_auth.py::test_signup_returns_token        PASSED
test_auth.py::test_login_returns_token         PASSED
test_auth.py::test_me_requires_auth            PASSED
test_auth.py::test_me_returns_user             PASSED
test_health.py::test_health_returns_ok         PASSED
test_health.py::test_root_returns_name         PASSED
test_meta.py::test_list_tools_returns_nonempty PASSED
test_meta.py::test_pipeline_log_returns_list   PASSED
test_pipeline_smoke.py::test_eda_generate_questions_returns_list PASSED
test_pipeline_smoke.py::test_modeling_configure_returns_eta      PASSED
test_pipeline_smoke.py::test_explain_shap_endpoint_exists        PASSED
test_pipeline_smoke.py::test_jobs_endpoint_returns_404_for_unknown PASSED
test_projects.py::test_create_project          PASSED
test_projects.py::test_list_projects           PASSED
test_projects.py::test_get_nonexistent_returns_404 PASSED
test_projects.py::test_delete_project          PASSED
test_upload.py::test_list_sample_datasets      PASSED
test_upload.py::test_upload_file_returns_preview PASSED
test_upload.py::test_upload_too_large_returns_413 SKIPPED (requires >250 MB payload)

18 passed, 1 skipped, 0 failures
```

---

## TypeScript Client

Generated at `frontend/lib/api-client/` via `openapi-typescript-codegen`:

- `core/` — 6 files (ApiError, ApiRequestOptions, ApiResult, CancelablePromise, OpenAPI, request)
- `models/` — 68 TypeScript interfaces, one per Pydantic schema
- `services/` — 13 service classes (AuthService, ChatService, ConfigureService, DownloadService, EdaService, ExplainabilityService, FeatureEngineeringService, JobsService, MetaService, ModelingService, PredictService, ProjectsService, UploadService)
- `index.ts` — barrel export

The client is committed (not gitignored) so Vercel builds reproducibly without a
codegen step in CI.
