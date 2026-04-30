# Spec 07 — Training Execution: Background Thread + MLflow Streaming

> **This is the hardest spec.** Read it twice before writing code. Threading + Streamlit + MLflow has many footguns. The patterns below are battle-tested — don't deviate.

## Mockup reference
**File:** `reference/modeling_mockup.html`
**Section:** `<div class="md-train-status">` near the top of phase 2
**Lines:** ~1666–1715

The mockup shows the *visible* result of training in progress. This spec is about everything *underneath* — the background worker, progress streaming, cancel handling, MLflow integration.

---

## What this spec covers

When the user clicks **Start Training** (spec 06's action bar), the page must:

1. **Switch phase from "configure" to "results"** (a phase-router state flag — see spec 01).
2. **Spin up a background daemon thread** that runs the actual training, so Streamlit's main thread stays responsive.
3. **Stream progress** — current algorithm, current trial, current fold, ETA — into `st.session_state` from the worker.
4. **Render live progress** in the main thread by polling that session state and calling `st.rerun()` every ~2 seconds while training is running.
5. **Read MLflow for completed-model metrics** — metrics, hyperparameters, and artifact paths all live in MLflow runs created by `agents/modeling_agent.py`. The UI never duplicates that data; it reads it.
6. **Handle cancel** — the user can stop training mid-flight; the worker cooperatively checks a cancel flag.
7. **Handle errors** — a single algo failing must NOT kill the whole training run; it's logged and the worker moves on.
8. **Commit results to LangGraph state** — once all algorithms complete, populate `state["trained_models"]`, `state["model_results"]`, `state["best_model"]`, `state["best_model_path"]`.

---

## Architecture diagram

```
┌─────────────────────────── Streamlit MAIN thread ───────────────────────────┐
│                                                                              │
│  pages/05_modeling.py (the page script)                                     │
│      │                                                                       │
│      │ on every script-run:                                                  │
│      ▼                                                                       │
│  md_phase_router → "results"                                                 │
│      │                                                                       │
│      ▼                                                                       │
│  md_train_status.render()    ◄── reads st.session_state["md_progress"]       │
│      │                       ◄── reads st.session_state["md_results"]        │
│      ▼                                                                       │
│  if is_running():                                                            │
│      time.sleep(2)                                                           │
│      st.rerun()  ◄────────── re-triggers the whole script                    │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ writes to session_state from BG thread
                                   │ (only safe because we attach ScriptRunCtx)
                                   ▼
┌──────────────────────────── Background DAEMON thread ────────────────────────┐
│                                                                              │
│  md_training_orchestrator.start(plan, project)                              │
│      │                                                                       │
│      ▼                                                                       │
│  for algo in plan["selected_algorithms"]:                                    │
│      if cancel_event.is_set(): break                                         │
│      try:                                                                    │
│          set_progress(current_algo=algo, status="training")                  │
│          run_id = modeling_agent.train_models(                               │
│              state, algo, hp, search, validation, on_trial=set_progress)     │
│          # ↑ writes to MLflow internally                                     │
│          set_progress(completed=algo)                                        │
│      except Exception as e:                                                  │
│          log_error(algo, e)                                                  │
│          continue                                                            │
│  set_complete()                                                              │
│                                                                              │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ reads/writes
                                   ▼
                            ┌────────────────┐
                            │     MLflow     │
                            │   (file://     │
                            │   ./mlruns)    │
                            └────────────────┘
```

---

## Hard rules

1. **One thread total.** Even if 4 algorithms are queued, train them sequentially in ONE worker thread. Parallelism is hard with Streamlit's session state — don't.
2. **Daemon thread.** `threading.Thread(target=..., daemon=True)`. If the user closes the browser tab, the thread dies with the process.
3. **`add_script_run_ctx(thread)` BEFORE `.start()`.** Without this, the worker can't write to `st.session_state`. Use Streamlit's internal API:
   ```python
   from streamlit.runtime.scriptrunner import add_script_run_ctx
   add_script_run_ctx(thread)
   thread.start()
   ```
4. **Progress writes go through a thread-safe queue OR direct session_state writes.** Direct writes are cheaper and Streamlit's session_state is dict-backed and acceptable for our update frequency. If you choose queue-based, drain the queue from the main thread on each rerun.
5. **MLflow integration is read-only from the UI.** All writes happen inside `modeling_agent.train_models`. The UI calls `mlflow.search_runs(experiment_ids=[...], filter_string=...)` to pull metrics for completed runs.
6. **Cancel is cooperative.** The worker checks `cancel_event.is_set()` between algorithms and (where possible) between trials. We do NOT use `Thread.kill` or signal handlers.
7. **Errors are isolated per algorithm.** Wrap each algo's training in `try/except`, log to `state["pipeline_log"]` and `st.session_state["md_log"]`, then move on.
8. **Polling cadence: 2 seconds.** Not faster — Streamlit reruns are expensive. Not slower — UX feels frozen.
9. **Cleanup on page leave.** If `is_running()` and the user navigates away, set the cancel flag automatically. The daemon will exit on next checkpoint.

---

## Files to create

```
dashboard/components/
  md_training_orchestrator.py      # The main orchestrator — worker thread + state management (~280 lines)
  md_mlflow_reader.py              # Read-only MLflow adapter
  md_train_status.py               # Live progress strip (top of phase 2)
```

No backend files modified. **Note:** `agents/modeling_agent.py` already exists and already calls MLflow internally; we ride on top of it.

---

## File 1 — `md_training_orchestrator.py`

```python
"""
Training orchestrator — runs all selected algorithms in a background daemon thread.
Streams progress and results back to st.session_state so the main thread can render.

This module is the ONLY place that imports `agents.modeling_agent`. The UI components
read from session_state and from MLflow (via md_mlflow_reader); they never call the
modeling agent directly.

Public API:
    start(state, plan, project_id) -> None
    cancel() -> None
    is_running() -> bool
    get_progress() -> ProgressSnapshot
    get_results() -> dict
    get_log() -> list[LogEntry]
    is_complete() -> bool
    reset() -> None
"""

import ast
import logging
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

import streamlit as st

logger = logging.getLogger(__name__)


# ─── Session-state keys (constants — single source of truth) ────────────────

PROGRESS_KEY     = "md_progress"          # ProgressSnapshot
RESULTS_KEY      = "md_results"           # dict[algo_name, dict]
LOG_KEY          = "md_log"               # list[LogEntry]
CANCEL_KEY       = "md_cancel_event"      # threading.Event
THREAD_KEY       = "md_thread"            # threading.Thread (or None)
START_TS_KEY     = "md_start_ts"          # float (time.time() at start)
COMPLETE_KEY     = "md_complete"          # bool
IN_PROGRESS_KEY  = "md_in_progress"       # bool
ERROR_KEY        = "md_run_error"         # str | None — fatal-level error
EXPERIMENT_KEY   = "md_mlflow_experiment_id"   # str (the MLflow exp_id for this session)
SESSION_TAG_KEY  = "md_mlflow_session_tag"     # str (unique tag for filter_string)


# ─── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class ProgressSnapshot:
    """Snapshot of training progress — streamed to UI every ~1s from the worker."""
    current_algo: Optional[str] = None
    current_algo_index: int = 0           # 0-based: which algo in the queue
    total_algos: int = 0
    current_trial: int = 0                # 0-based: trial within current algo's HP search
    total_trials: int = 0                 # total trials configured for this algo
    current_fold: int = 0
    total_folds: int = 0
    completed_count: int = 0
    queued_count: int = 0
    eta_seconds: float = 0.0
    started_at: Optional[float] = None
    cancelled: bool = False
    status: str = "idle"                  # idle | training | cancelling | complete | error
    last_update: Optional[float] = None


@dataclass
class LogEntry:
    """One line in the training log."""
    timestamp: float
    level: str       # INFO | OK | WARN | ERR
    message: str

    def to_dict(self):
        return asdict(self)


# ─── Public API ─────────────────────────────────────────────────────────────

def start(state: dict, plan: dict, project_id: str) -> None:
    """
    Kick off the worker thread.
    `plan` is a frozen snapshot of state["modeling_config"] taken at click time
    (so further UI edits don't affect the in-flight run).
    """
    if is_running():
        logger.warning("Training already in progress — ignoring start()")
        return

    _reset_session_state()
    cancel_event = threading.Event()
    st.session_state[CANCEL_KEY] = cancel_event
    st.session_state[START_TS_KEY] = time.time()
    st.session_state[IN_PROGRESS_KEY] = True
    st.session_state[COMPLETE_KEY] = False
    st.session_state[ERROR_KEY] = None
    st.session_state[PROGRESS_KEY] = ProgressSnapshot(
        total_algos=len(plan.get("selected_algorithms", [])),
        queued_count=len(plan.get("selected_algorithms", [])),
        started_at=time.time(),
        status="training",
        last_update=time.time(),
    )
    st.session_state[RESULTS_KEY] = {}
    st.session_state[LOG_KEY] = []
    st.session_state[SESSION_TAG_KEY] = f"autods_{project_id}_{int(time.time())}"

    _log("INFO", f"Training started — {len(plan.get('selected_algorithms', []))} algorithms queued")

    thread = threading.Thread(
        target=_worker,
        args=(state, plan, project_id, cancel_event),
        name=f"autods-train-{project_id}",
        daemon=True,
    )

    # Critical — attach Streamlit's script-run context so the worker can write
    # to st.session_state. Without this, writes from the worker are silently dropped.
    try:
        from streamlit.runtime.scriptrunner import add_script_run_ctx
        add_script_run_ctx(thread)
    except Exception:
        # On older Streamlit versions, the import path differs. Try the legacy.
        try:
            from streamlit.scriptrunner import add_script_run_ctx  # type: ignore
            add_script_run_ctx(thread)
        except Exception as e:
            logger.error(f"Could not attach ScriptRunContext: {e}. Worker writes may not appear.")

    st.session_state[THREAD_KEY] = thread
    thread.start()


def cancel() -> None:
    """Signal the worker to stop ASAP."""
    ev = st.session_state.get(CANCEL_KEY)
    if ev is not None:
        ev.set()
    progress = st.session_state.get(PROGRESS_KEY)
    if progress:
        progress.status = "cancelling"
        progress.cancelled = True
    _log("WARN", "Cancel requested — stopping after current trial")


def is_running() -> bool:
    return bool(st.session_state.get(IN_PROGRESS_KEY, False))


def is_complete() -> bool:
    return bool(st.session_state.get(COMPLETE_KEY, False))


def get_progress() -> ProgressSnapshot:
    return st.session_state.get(PROGRESS_KEY, ProgressSnapshot())


def get_results() -> dict:
    return st.session_state.get(RESULTS_KEY, {})


def get_log() -> list[LogEntry]:
    return st.session_state.get(LOG_KEY, [])


def reset() -> None:
    """Wipe training state — called when the user clicks Reconfigure."""
    cancel()
    # Wait briefly for the worker to actually exit (best-effort)
    thread = st.session_state.get(THREAD_KEY)
    if thread and thread.is_alive():
        thread.join(timeout=2.0)
    _reset_session_state()


# ─── Worker ─────────────────────────────────────────────────────────────────

def _worker(state: dict, plan: dict, project_id: str, cancel_event: threading.Event) -> None:
    """The thread target. Iterates algorithms and trains them one by one."""
    try:
        # Setup MLflow experiment for this session
        try:
            import mlflow
            exp_name = f"autods_session_{project_id}"
            try:
                exp = mlflow.set_experiment(exp_name)
                st.session_state[EXPERIMENT_KEY] = exp.experiment_id
            except Exception as e:
                _log("WARN", f"MLflow experiment setup failed: {e} — proceeding without experiment.")
        except ImportError:
            _log("WARN", "MLflow not installed — metrics will be in-memory only.")

        algos = plan.get("selected_algorithms", [])
        total = len(algos)

        for idx, algo in enumerate(algos):
            if cancel_event.is_set():
                _log("WARN", f"Cancelled before {algo}")
                break

            _update_progress(
                current_algo=algo,
                current_algo_index=idx,
                total_algos=total,
                queued_count=total - idx,
                status="training",
                last_update=time.time(),
            )
            _log("INFO", f"Training {algo}…")

            try:
                hp_values = _coerce_hp_values(algo, plan)
                search_strategy = plan.get("search_strategy", {}).get(algo, "bayesian")
                validation = plan.get("validation", {})

                # Trial-level callback so the worker can stream search progress
                def on_trial_progress(trial_idx, total_trials, fold_idx=0, total_folds=0):
                    _update_progress(
                        current_algo=algo,
                        current_algo_index=idx,
                        total_algos=total,
                        current_trial=trial_idx,
                        total_trials=total_trials,
                        current_fold=fold_idx,
                        total_folds=total_folds,
                        status="training",
                        last_update=time.time(),
                    )
                    if cancel_event.is_set():
                        raise InterruptedError("User cancelled training")

                run_id = _train_one(state, algo, hp_values, search_strategy, validation,
                                    project_id, on_trial_progress, cancel_event)

                if run_id:
                    metrics = _read_run_metrics(run_id)
                    st.session_state[RESULTS_KEY][algo] = {
                        "run_id": run_id,
                        "metrics": metrics,
                        "status": "done",
                        "completed_at": time.time(),
                    }
                    _log("OK", f"{algo} done — primary metric: {_primary_metric_str(metrics)}")
                else:
                    st.session_state[RESULTS_KEY][algo] = {
                        "run_id": None,
                        "metrics": {},
                        "status": "failed",
                    }
                    _log("ERR", f"{algo} returned no run_id")

                _update_progress(
                    completed_count=st.session_state[PROGRESS_KEY].completed_count + 1,
                    last_update=time.time(),
                )

            except InterruptedError:
                _log("WARN", f"{algo} cancelled mid-search")
                st.session_state[RESULTS_KEY][algo] = {"status": "cancelled"}
                break
            except Exception as e:
                logger.exception(f"Training {algo} failed")
                tb = traceback.format_exc(limit=3)
                st.session_state[RESULTS_KEY][algo] = {
                    "status": "failed",
                    "error": str(e),
                    "traceback": tb,
                }
                _log("ERR", f"{algo} failed: {type(e).__name__}: {e}")
                continue   # don't kill the whole run for one bad algo

        _commit_to_langgraph_state(state)

        progress = st.session_state.get(PROGRESS_KEY)
        if progress and progress.cancelled:
            progress.status = "cancelled"
        elif progress:
            progress.status = "complete"
        st.session_state[COMPLETE_KEY] = True
        st.session_state[IN_PROGRESS_KEY] = False
        _log("OK", "All training complete")

    except Exception as e:
        logger.exception("Worker crashed")
        st.session_state[ERROR_KEY] = f"{type(e).__name__}: {e}"
        st.session_state[IN_PROGRESS_KEY] = False
        _log("ERR", f"Fatal worker error: {e}")


# ─── Training adapter ───────────────────────────────────────────────────────

def _train_one(state, algo, hp, strategy, validation, project_id, on_trial, cancel_event) -> Optional[str]:
    """
    Call into agents.modeling_agent.train_models for a single algorithm.
    The modeling agent is responsible for: fitting the model, running the HP search,
    logging to MLflow, and returning the MLflow run_id.

    If the modeling agent doesn't yet support the (algo, hp, strategy) combination,
    we fall back to a direct sklearn/xgboost call that mirrors the agent's behavior.
    """
    try:
        from agents import modeling_agent
        if hasattr(modeling_agent, "train_models"):
            # Preferred path — let the agent handle MLflow, validation, etc.
            run_id = modeling_agent.train_models(
                state=state,
                algorithm=algo,
                hyperparameters=hp,
                search_strategy=strategy,
                validation=validation,
                session_tag=st.session_state.get(SESSION_TAG_KEY),
                on_trial=on_trial,
                cancel_event=cancel_event,
            )
            return run_id
    except TypeError:
        # Older signature — try a simpler call
        try:
            from agents import modeling_agent
            run_id = modeling_agent.train_models(state, algorithm=algo)
            return run_id
        except Exception as e:
            _log("WARN", f"modeling_agent.train_models legacy call failed: {e}; using fallback")
    except ImportError:
        _log("WARN", "modeling_agent not importable — using direct fallback")
    except Exception as e:
        logger.exception("modeling_agent failed")
        _log("WARN", f"modeling_agent failed for {algo}: {e}; using fallback")

    # Fallback — minimal direct sklearn call so the UI still gets results.
    return _fallback_train(state, algo, hp, validation, on_trial, cancel_event)


def _fallback_train(state, algo, hp, validation, on_trial, cancel_event) -> Optional[str]:
    """Minimal sklearn fallback so the UI never breaks if modeling_agent has issues."""
    try:
        import mlflow
        from agents.tools import ml_tools
    except ImportError:
        return None

    # Try a generic train call from ml_tools if it exists
    for fn_name in ("train_model_generic", f"train_{algo.lower().replace('-', '_')}", "train_model"):
        if hasattr(ml_tools, fn_name):
            try:
                fn = getattr(ml_tools, fn_name)
                with mlflow.start_run(run_name=f"{algo}_fallback") as run:
                    mlflow.log_param("algorithm", algo)
                    mlflow.log_param("session_id", st.session_state.get(SESSION_TAG_KEY, ""))
                    fn(state=state, algorithm=algo, hyperparameters=hp)
                    return run.info.run_id
            except Exception as e:
                logger.exception(f"Fallback train via {fn_name} failed")
                continue
    return None


# ─── HP value coercion ──────────────────────────────────────────────────────

def _coerce_hp_values(algo: str, plan: dict) -> dict:
    """
    Coerce raw string HP values (from session_state) into properly typed Python values
    that the model class will accept.
    """
    raw = plan.get("hyperparameters", {}).get(algo, {})
    schemas = plan.get("hp_schemas", {}).get(algo, [])  # list of param schemas
    schema_by_name = {p["name"]: p for p in schemas}

    coerced = {}
    for name, raw_val in raw.items():
        if isinstance(raw_val, str) and raw_val.strip() == "":
            continue
        schema = schema_by_name.get(name, {"type": "str"})
        try:
            coerced[name] = _coerce_one(raw_val, schema)
        except Exception as e:
            _log("WARN", f"{algo}: could not coerce {name}={raw_val!r} ({e}) — skipping")
            continue
    return coerced


def _coerce_one(raw, schema):
    t = schema.get("type", "str")
    if raw is None or raw == "None":
        return None

    if t == "int":
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            # might be tuple/list-as-string (e.g. for hidden_layer_sizes)
            return ast.literal_eval(str(raw))
    if t == "float":
        if isinstance(raw, str) and raw.lower() in ("none", "null"):
            return None
        try:
            return float(raw)
        except ValueError:
            return ast.literal_eval(str(raw))
    if t == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("true", "1", "yes")
    if t == "choice":
        return str(raw)
    # str / fallback — try literal_eval for tuples/lists, else return as-is
    if isinstance(raw, str) and (raw.startswith("(") or raw.startswith("[")):
        try:
            return ast.literal_eval(raw)
        except Exception:
            return raw
    return raw


# ─── MLflow reads ───────────────────────────────────────────────────────────

def _read_run_metrics(run_id: str) -> dict:
    """Pull metrics for a finished MLflow run."""
    try:
        import mlflow
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        metrics = dict(run.data.metrics) if run.data and run.data.metrics else {}
        params = dict(run.data.params) if run.data and run.data.params else {}
        return {**metrics, "_params": params}
    except Exception as e:
        logger.warning(f"Could not read MLflow run {run_id}: {e}")
        return {}


def _primary_metric_str(metrics: dict) -> str:
    """Extract whichever of the well-known metrics is present, for log display."""
    for key in ("auc_roc", "auc", "f1", "accuracy", "rmse", "mae", "r2"):
        if key in metrics and isinstance(metrics[key], (int, float)):
            return f"{key}={metrics[key]:.4f}"
    return "no metrics"


# ─── State sync ─────────────────────────────────────────────────────────────

def _commit_to_langgraph_state(state: dict) -> None:
    """Write the final results to the LangGraph state object."""
    results = st.session_state.get(RESULTS_KEY, {})

    trained = {}
    metrics = {}
    for algo, info in results.items():
        if info.get("status") == "done" and info.get("run_id"):
            trained[algo] = info["run_id"]
            metrics[algo] = {k: v for k, v in info.get("metrics", {}).items() if not k.startswith("_")}

    state["trained_models"] = trained
    state["model_results"] = metrics

    # Pick best model — primary metric depends on problem type
    best = _select_best(state, metrics)
    if best:
        state["best_model"] = best
        # Path is read from the MLflow run's artifact location (if available)
        try:
            import mlflow
            client = mlflow.tracking.MlflowClient()
            run = client.get_run(trained[best])
            state["best_model_path"] = run.info.artifact_uri + "/model"
        except Exception:
            state["best_model_path"] = None

    state.setdefault("completed_steps", []).append("modeling")
    if "modeling" in state["completed_steps"]:
        # Deduplicate
        state["completed_steps"] = list(dict.fromkeys(state["completed_steps"]))


def _select_best(state, metrics_by_algo) -> Optional[str]:
    if not metrics_by_algo:
        return None
    pt = state.get("problem_type", "binary_classification")
    higher_is_better = pt in ("binary_classification", "multiclass_classification")
    primary = "auc_roc" if higher_is_better else "rmse"

    candidates = []
    for algo, m in metrics_by_algo.items():
        if primary in m:
            candidates.append((algo, m[primary]))
        elif "f1" in m:
            candidates.append((algo, m["f1"]))
        elif "accuracy" in m:
            candidates.append((algo, m["accuracy"]))
    if not candidates:
        return next(iter(metrics_by_algo.keys()))
    candidates.sort(key=lambda x: x[1], reverse=higher_is_better)
    return candidates[0][0]


# ─── Internal helpers ───────────────────────────────────────────────────────

def _update_progress(**kwargs):
    """Apply partial updates to the ProgressSnapshot in session_state."""
    cur = st.session_state.get(PROGRESS_KEY) or ProgressSnapshot()
    for k, v in kwargs.items():
        if hasattr(cur, k):
            setattr(cur, k, v)
    cur.last_update = time.time()
    st.session_state[PROGRESS_KEY] = cur


def _log(level: str, msg: str):
    entry = LogEntry(timestamp=time.time(), level=level, message=msg)
    st.session_state.setdefault(LOG_KEY, []).append(entry)


def _reset_session_state():
    """Clear all training-related session keys."""
    for k in (PROGRESS_KEY, RESULTS_KEY, LOG_KEY, CANCEL_KEY, THREAD_KEY,
              START_TS_KEY, COMPLETE_KEY, IN_PROGRESS_KEY, ERROR_KEY,
              EXPERIMENT_KEY, SESSION_TAG_KEY):
        if k in st.session_state:
            del st.session_state[k]
```

---

## File 2 — `md_mlflow_reader.py`

```python
"""
Read-only MLflow adapter. The UI reads metrics/params/artifacts via this module
ONLY. We never instantiate MLflow runs from the UI — modeling_agent does that.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_run_metrics(run_id: str) -> dict:
    try:
        import mlflow
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        return dict(run.data.metrics) if run.data and run.data.metrics else {}
    except Exception as e:
        logger.warning(f"MLflow get_run_metrics({run_id}) failed: {e}")
        return {}


def get_run_params(run_id: str) -> dict:
    try:
        import mlflow
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        return dict(run.data.params) if run.data and run.data.params else {}
    except Exception as e:
        logger.warning(f"MLflow get_run_params({run_id}) failed: {e}")
        return {}


def search_session_runs(experiment_id: str, session_tag: str) -> list[dict]:
    """List all runs in this session."""
    try:
        import mlflow
        client = mlflow.tracking.MlflowClient()
        runs = client.search_runs(
            experiment_ids=[experiment_id],
            filter_string=f'params.session_id = "{session_tag}"',
            max_results=200,
        )
        return [
            {
                "run_id": r.info.run_id,
                "name": r.info.run_name,
                "status": r.info.status,
                "metrics": dict(r.data.metrics),
                "params": dict(r.data.params),
                "artifact_uri": r.info.artifact_uri,
            }
            for r in runs
        ]
    except Exception as e:
        logger.warning(f"MLflow search_session_runs failed: {e}")
        return []


def get_artifact_path(run_id: str, sub_path: str = "model") -> Optional[str]:
    try:
        import mlflow
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        return f"{run.info.artifact_uri}/{sub_path}"
    except Exception as e:
        logger.warning(f"MLflow get_artifact_path failed: {e}")
        return None
```

---

## File 3 — `md_train_status.py`

```python
"""
Live training status strip — shown at the top of phase 2.
Reads from md_training_orchestrator.get_progress() each time the page renders.
"""

import time
import streamlit as st
from dashboard.components import md_training_orchestrator as orch


def render(state: dict, project_id: str) -> None:
    progress = orch.get_progress()
    is_running = orch.is_running()

    # Build status line
    if progress.status == "training":
        algo_str = progress.current_algo or "preparing…"
        if progress.total_folds > 0 and progress.total_trials > 0:
            mid = (
                f"fold {progress.current_fold} of {progress.total_folds} · "
                f"trial {progress.current_trial} of {progress.total_trials}"
            )
        elif progress.total_trials > 0:
            mid = f"trial {progress.current_trial} of {progress.total_trials}"
        elif progress.total_folds > 0:
            mid = f"fold {progress.current_fold} of {progress.total_folds}"
        else:
            mid = "starting…"
        eta_str = _format_eta(progress.eta_seconds) if progress.eta_seconds > 0 else "computing…"
        status_html = f"""
        <div class="md-train-status running">
          <div class="md-train-spinner"></div>
          <div class="md-train-text">
            Training <strong>{algo_str}</strong> · {mid}
            <span class="md-train-eta">ETA {eta_str}</span>
          </div>
          <div class="md-train-meta">
            {progress.completed_count} of {progress.total_algos} done · session {st.session_state.get(orch.SESSION_TAG_KEY, "")}
          </div>
        </div>
        """
    elif progress.status == "complete":
        status_html = f"""
        <div class="md-train-status complete">
          <div class="md-train-check">✓</div>
          <div class="md-train-text">
            Training complete · <strong>{progress.completed_count}</strong> of {progress.total_algos} models trained
          </div>
        </div>
        """
    elif progress.status == "cancelled":
        status_html = f"""
        <div class="md-train-status cancelled">
          <div class="md-train-text">
            Training cancelled · {progress.completed_count} of {progress.total_algos} completed before stop
          </div>
        </div>
        """
    elif progress.status == "cancelling":
        status_html = """
        <div class="md-train-status cancelling">
          <div class="md-train-spinner"></div>
          <div class="md-train-text">Cancelling… waiting for current trial to finish.</div>
        </div>
        """
    else:
        return  # nothing to render

    st.markdown(status_html, unsafe_allow_html=True)

    # Cancel button (only while running)
    if is_running and progress.status not in ("cancelling",):
        if st.button("Cancel training", key=f"md_cancel_{project_id}"):
            orch.cancel()
            st.rerun()

    # Re-trigger the script in 2 seconds while running
    if is_running:
        time.sleep(2.0)
        st.rerun()


def _format_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
```

---

## CSS additions

Add to `shared_css.py`:

```css
.md-train-status {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 20px; margin-bottom: 24px;
  background: rgba(7,9,26,0.6);
  border: 1px solid var(--border-default); border-radius: 14px;
}
.md-train-status.running { border-color: rgba(34,211,238,0.35); }
.md-train-status.complete { border-color: rgba(74,222,128,0.4); }
.md-train-status.cancelled { border-color: rgba(251,146,60,0.4); }
.md-train-status.cancelling { border-color: rgba(251,191,36,0.4); }

.md-train-spinner {
  width: 14px; height: 14px; flex-shrink: 0;
  border-radius: 50%; border: 2px solid rgba(34,211,238,0.18);
  border-top-color: var(--cyan);
  animation: md-spin 0.9s linear infinite;
}
@keyframes md-spin { to { transform: rotate(360deg); } }

.md-train-check {
  width: 18px; height: 18px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(74,222,128,0.18);
  border-radius: 50%;
  color: var(--green);
  font-size: 11px; font-weight: 700;
}
.md-train-text {
  flex: 1;
  font-family: var(--font-mono); font-size: 12.5px;
  color: var(--text-secondary);
}
.md-train-text strong { color: var(--text-primary); }
.md-train-eta {
  margin-left: 10px; padding: 1px 8px;
  background: rgba(34,211,238,0.1);
  border-radius: 4px;
  color: var(--cyan); font-size: 11px;
}
.md-train-meta {
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--text-faint); flex-shrink: 0;
}
```

---

## Edge cases

| Case | Handling |
|---|---|
| User closes tab mid-training | Daemon thread exits when the process dies. MLflow runs already started will be marked FAILED by MLflow's housekeeping. |
| User refreshes the page | Streamlit creates a new session — old session_state is gone. The daemon thread (still running) will write to the old session_state which is now orphaned. The new session sees no progress. **Document this in 00_START_HERE as a known limitation; recommend MLflow UI for in-flight runs.** |
| `add_script_run_ctx` import fails (very old Streamlit) | Worker still runs but writes to session_state are dropped. Progress strip shows "preparing…" forever. Logged as ERROR. Hard limit: requires Streamlit ≥1.20. |
| MLflow not installed | Worker logs WARN once and proceeds. `_train_one` returns None for run_id; results are marked failed. |
| `agents.modeling_agent` doesn't exist or signature mismatch | Falls back to `_fallback_train` which uses `ml_tools` directly. |
| One algorithm crashes (e.g. SVM-RBF on 1M rows) | `try/except` per algo. Logs ERR, marks that algo failed, moves on. |
| User clicks Start Training twice | Second call is no-op (`is_running()` guard). |
| User clicks Cancel mid-trial | `cancel_event.set()`. Worker checks at next trial boundary and at the top of each algo. Worst-case wait: one trial duration. |
| User clicks Reconfigure (back to phase 1) while training is live | `reset()` is called which sets cancel and joins (timeout 2s). Then session_state is wiped. If thread doesn't exit in 2s, it'll continue but write to orphaned state — harmless. |
| Two algos crash with the same run_id (impossible but defensive) | RESULTS_KEY is keyed by algo name, so collisions are not possible. |
| Progress callback fires faster than 2 Hz | Fine — direct session_state writes are cheap. Streamlit only re-renders every 2s due to our polling rate. |
| `state` dict mutated by background thread while main thread reads | The fields we write (`trained_models`, `model_results`, etc.) are written ONCE at the end of training. Race-free. |
| `data_profile` missing during ETA estimation | `_estimate_eta_minutes` defaults to 1000 rows / 10 features (see spec 06). Worker doesn't compute ETA pre-emptively; only updates after first trial completes. |

---

## How `agents/modeling_agent.train_models` should be called

Expected signature (we ride on top of this — if it doesn't match exactly, the orchestrator falls back):

```python
def train_models(
    state: dict,
    algorithm: str,
    hyperparameters: dict,
    search_strategy: str,            # "bayesian" | "grid" | "random" | "optuna" | "exact"
    validation: dict,                # {"method": "stratified_kfold", "n_splits": 5, ...}
    session_tag: str,                # for MLflow filter_string
    on_trial: Optional[Callable] = None,   # callback(trial_idx, total_trials, fold_idx, total_folds)
    cancel_event: Optional[threading.Event] = None,
) -> str:                            # returns MLflow run_id
    """
    Internally:
      1. mlflow.start_run(run_name=algorithm, tags={"session_id": session_tag})
      2. Configure HP search per strategy (BayesSearchCV / GridSearchCV / Optuna / direct fit)
      3. Run search/fit, calling on_trial(...) at each trial start
      4. mlflow.log_metric() for AUC/Acc/F1/etc.
      5. mlflow.log_param() for HPs
      6. mlflow.sklearn.log_model() for the artifact
      7. Return run_id
    """
```

If the existing `train_models` doesn't accept `on_trial` or `cancel_event`, the orchestrator catches the TypeError and falls back to a non-streaming call (no progress updates per trial, only per-algo completion).

---

## Acceptance criteria

- [ ] Clicking Start Training switches phase to "results" AND launches the worker thread
- [ ] `add_script_run_ctx(thread)` is called BEFORE `thread.start()`
- [ ] Worker iterates `selected_algorithms` sequentially
- [ ] Progress is written to `st.session_state["md_progress"]` from the worker
- [ ] Main thread's `md_train_status.render()` reads progress and re-runs every 2 seconds while training
- [ ] Cancel button sets the cancel event; worker exits cooperatively
- [ ] One failing algo does NOT kill the whole run
- [ ] All errors logged to `st.session_state["md_log"]` with proper level
- [ ] On completion, `state["trained_models"]`, `state["model_results"]`, `state["best_model"]`, `state["best_model_path"]` are populated
- [ ] `state["completed_steps"]` includes "modeling" exactly once
- [ ] MLflow runs are tagged with `session_id` so future filtering works
- [ ] If `agents.modeling_agent.train_models` signature differs, the orchestrator falls back gracefully
- [ ] If MLflow not installed, the orchestrator still completes with limited metrics
- [ ] No modifications outside `dashboard/components/`
