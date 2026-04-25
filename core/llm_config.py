"""Multi-provider LLM configuration and utilities.

Supports multiple LLM backends:
- Gemma 4 via Google Gemini API (cheapest hosted option)
- Gemma 4 via Ollama (completely free, runs locally)
- Claude via Anthropic API
- Any OpenAI-compatible API

Set AUTODS_LLM_PROVIDER in .env to choose:
  "gemini"   → Gemma 4 via Google Gemini API (default, cheapest)
  "ollama"   → Gemma 4 via local Ollama (free, needs 16GB+ RAM)
  "anthropic" → Claude via Anthropic API
  "openai"   → OpenAI GPT models

Handles structured output parsing, cost tracking, caching, and
graceful degradation when API is unavailable.
"""

import json
import logging
import os
import hashlib
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Simple in-memory cache for LLM responses
_response_cache: dict[str, str] = {}

# Runtime override — set by dashboard sidebar toggle
_runtime_provider: str | None = None

# Provider-specific cost per 1K tokens (for tracking)
PROVIDER_COSTS = {
    "gemini": {"input": 0.00013, "output": 0.00038},       # Gemma 4 31B via Gemini API
    "ollama": {"input": 0.0, "output": 0.0},                # Free (local)
    "anthropic": {"input": 0.003, "output": 0.015},          # Claude Sonnet
    "openai": {"input": 0.005, "output": 0.015},             # GPT-4o
}

# Display info for dashboard UI
PROVIDER_INFO = {
    "ollama": {"label": "Gemma (Local)", "icon": "🏠", "desc": "Free, runs on your machine via Ollama", "needs_key": False},
    "gemini": {"label": "Gemma (Google)", "icon": "🌐", "desc": "Cheapest hosted API via Google AI Studio", "needs_key": True, "key_env": "GOOGLE_API_KEY"},
    "anthropic": {"label": "Claude (Anthropic)", "icon": "🧠", "desc": "Best quality, Anthropic API", "needs_key": True, "key_env": "ANTHROPIC_API_KEY"},
    "openai": {"label": "GPT (OpenAI)", "icon": "💬", "desc": "OpenAI GPT models", "needs_key": True, "key_env": "OPENAI_API_KEY"},
}


def set_runtime_provider(provider: str) -> None:
    """Override LLM provider at runtime (from dashboard toggle)."""
    global _runtime_provider
    _runtime_provider = provider.lower()
    clear_cache()  # Clear cache when switching providers
    logger.info("LLM provider switched to: %s", provider)


def get_available_providers() -> list[dict[str, Any]]:
    """Return list of available providers with status (key configured or not)."""
    result = []
    for key, info in PROVIDER_INFO.items():
        available = True
        if info.get("needs_key"):
            env_key = info.get("key_env", "")
            available = bool(os.getenv(env_key))
        result.append({
            "id": key,
            "label": info["label"],
            "icon": info["icon"],
            "desc": info["desc"],
            "available": available,
            "needs_key": info.get("needs_key", False),
            "key_env": info.get("key_env", ""),
        })
    return result


def get_llm():
    """Get configured LLM instance based on AUTODS_LLM_PROVIDER.
    
    Provider priority (if not explicitly set):
    1. Gemini (Gemma 4) — cheapest hosted option
    2. Ollama (Gemma 4) — free local option
    3. Anthropic (Claude) — best quality
    
    Returns:
        LangChain ChatModel instance.
    
    Raises:
        LLMAPIError: If required API key is not set.
    """
    from core.exceptions import LLMAPIError

    provider = _runtime_provider or os.getenv("AUTODS_LLM_PROVIDER", "ollama").lower()
    temperature = float(os.getenv("AUTODS_LLM_TEMPERATURE", "0"))
    max_tokens = int(os.getenv("AUTODS_LLM_MAX_TOKENS", "4096"))

    if provider == "gemini":
        return _get_gemini_llm(temperature, max_tokens)
    elif provider == "ollama":
        return _get_ollama_llm(temperature, max_tokens)
    elif provider == "anthropic":
        return _get_anthropic_llm(temperature, max_tokens)
    elif provider == "openai":
        return _get_openai_llm(temperature, max_tokens)
    else:
        raise LLMAPIError(
            f"Unknown LLM provider: '{provider}'. "
            f"Set AUTODS_LLM_PROVIDER to one of: gemini, ollama, anthropic, openai"
        )


def _get_gemini_llm(temperature: float, max_tokens: int):
    """Get Gemma 4 via Google Gemini API.
    
    Cheapest hosted option. Requires GOOGLE_API_KEY.
    Get a free key at https://aistudio.google.com/
    """
    from core.exceptions import LLMAPIError

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise LLMAPIError(
            "GOOGLE_API_KEY not set. Get a free key at https://aistudio.google.com/apikey\n"
            "Then add to .env: GOOGLE_API_KEY=your-key-here"
        )

    model = os.getenv("AUTODS_LLM_MODEL", "gemma-4-31b-it")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=api_key,
        )
    except ImportError:
        raise LLMAPIError(
            "langchain-google-genai not installed. Run:\n"
            "pip install langchain-google-genai"
        )


def _get_ollama_llm(temperature: float, max_tokens: int):
    """Get Gemma 4 via local Ollama (completely free).
    
    Requires Ollama running locally with Gemma 4 pulled:
        ollama pull gemma4:31b
    or for smaller machines:
        ollama pull gemma4:26b
        ollama pull gemma4:4b
    """
    from core.exceptions import LLMAPIError

    model = os.getenv("AUTODS_LLM_MODEL", "gemma4:26b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            temperature=temperature,
            num_predict=max_tokens,
            base_url=base_url,
        )
    except ImportError:
        raise LLMAPIError(
            "langchain-ollama not installed. Run:\n"
            "pip install langchain-ollama\n\n"
            "Also ensure Ollama is running:\n"
            "  ollama serve\n"
            "  ollama pull gemma4:26b"
        )


def _get_anthropic_llm(temperature: float, max_tokens: int):
    """Get Claude via Anthropic API."""
    from core.exceptions import LLMAPIError

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMAPIError(
            "ANTHROPIC_API_KEY not set. Get a key at https://console.anthropic.com/\n"
            "Then add to .env: ANTHROPIC_API_KEY=sk-ant-your-key-here"
        )

    model = os.getenv("AUTODS_LLM_MODEL", "claude-sonnet-4-20250514")

    try:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
        )
    except ImportError:
        raise LLMAPIError(
            "langchain-anthropic not installed. Run:\n"
            "pip install langchain-anthropic"
        )


def _get_openai_llm(temperature: float, max_tokens: int):
    """Get GPT models via OpenAI API."""
    from core.exceptions import LLMAPIError

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMAPIError(
            "OPENAI_API_KEY not set. Add to .env: OPENAI_API_KEY=sk-your-key-here"
        )

    model = os.getenv("AUTODS_LLM_MODEL", "gpt-4o")

    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
        )
    except ImportError:
        raise LLMAPIError(
            "langchain-openai not installed. Run:\n"
            "pip install langchain-openai"
        )


def get_provider_name() -> str:
    """Get the current LLM provider name."""
    return _runtime_provider or os.getenv("AUTODS_LLM_PROVIDER", "ollama").lower()


def get_cost_per_1k_tokens() -> dict[str, float]:
    """Get cost per 1K tokens for current provider."""
    provider = get_provider_name()
    return PROVIDER_COSTS.get(provider, {"input": 0.0, "output": 0.0})


def invoke_llm(
    prompt: str,
    system_prompt: str = "",
    state: dict | None = None,
    use_cache: bool = True,
    json_output: bool = False,
) -> str:
    """Invoke Claude with full logging, caching, and error handling.
    
    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system prompt for context.
        state: Pipeline state dict for logging API usage.
        use_cache: Whether to use response cache.
        json_output: If True, append JSON instruction to prompt.
        
    Returns:
        LLM response text.
        
    Raises:
        LLMAPIError: If API call fails after retries.
    """
    from core.exceptions import LLMAPIError, LLMRateLimitError

    # Build cache key
    cache_key = hashlib.md5(f"{system_prompt}:{prompt}".encode()).hexdigest()
    if use_cache and cache_key in _response_cache:
        logger.debug("LLM cache hit for prompt hash %s", cache_key[:8])
        return _response_cache[cache_key]

    # Append JSON instruction if needed
    if json_output:
        prompt += "\n\nRespond with valid JSON only. No preamble, no markdown backticks, no explanation — just the JSON object."

    # Build messages
    messages = []
    if system_prompt:
        messages.append(("system", system_prompt))
    messages.append(("human", prompt))

    # Invoke with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            llm = get_llm()
            response = llm.invoke(messages)

            # Track usage in state
            if state is not None:
                state["api_call_count"] = state.get("api_call_count", 0) + 1
                # Estimate tokens (rough: 1 token ≈ 4 chars)
                input_tokens = len(prompt) // 4
                output_tokens = len(response.content) // 4
                state["api_token_count"] = state.get("api_token_count", 0) + input_tokens + output_tokens
                # Estimate cost
                costs = get_cost_per_1k_tokens()
                input_cost = costs["input"]
                output_cost = costs["output"]
                cost = (input_tokens / 1000 * input_cost +
                        output_tokens / 1000 * output_cost)
                state["estimated_cost_usd"] = state.get("estimated_cost_usd", 0.0) + cost

            result = response.content

            # Cache the response
            if use_cache:
                _response_cache[cache_key] = result

            return result

        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str:
                if attempt < max_retries - 1:
                    import time
                    wait_time = 2 ** (attempt + 1)
                    logger.warning("Rate limited. Waiting %ds before retry %d/%d", wait_time, attempt + 2, max_retries)
                    time.sleep(wait_time)
                    continue
                raise LLMRateLimitError(f"Rate limited after {max_retries} retries: {e}")
            elif attempt < max_retries - 1:
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, max_retries, e)
                continue
            else:
                raise LLMAPIError(f"LLM call failed after {max_retries} attempts: {e}")

    raise LLMAPIError("LLM call failed — exhausted all retries")


def invoke_llm_json(
    prompt: str,
    system_prompt: str = "",
    state: dict | None = None,
    use_cache: bool = True,
) -> dict | list:
    """Invoke Claude and parse response as JSON.
    
    Args:
        prompt: The user prompt.
        system_prompt: Optional system prompt.
        state: Pipeline state for logging.
        use_cache: Whether to use response cache.
        
    Returns:
        Parsed JSON as dict or list.
        
    Raises:
        LLMParsingError: If response is not valid JSON.
    """
    from core.exceptions import LLMParsingError

    raw = invoke_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        state=state,
        use_cache=use_cache,
        json_output=True,
    )

    # Clean response: strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON response: %s\nRaw response: %s", e, raw[:500])
        raise LLMParsingError(f"LLM returned invalid JSON: {e}\nFirst 200 chars: {raw[:200]}")


def get_agent_system_prompt(agent_name: str, domain_config: dict | None = None) -> str:
    """Load system prompt for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., "eda_agent", "modeling_agent").
        domain_config: Optional domain config to inject domain-specific instructions.
        
    Returns:
        System prompt string.
    """
    base_prompts = {
        "orchestrator": (
            "You are the Orchestrator Agent for AutoDS, an autonomous data science platform. "
            "Your role is to decompose user goals into subtasks, route work to specialist agents, "
            "and make decisions about the workflow. Always think step-by-step about what the user "
            "needs and which agent should handle each part."
        ),
        "domain_detector": (
            "You are the Domain Detection Agent. Analyze column names, data patterns, and value "
            "distributions to identify the industry domain (healthcare, finance, ecommerce, hr, "
            "manufacturing, marketing, or generic). Be specific about your reasoning."
        ),
        "data_profiler": (
            "You are the Data Profiling Agent. Your job is to assess data quality, detect issues, "
            "and recommend cleaning strategies. Be thorough but practical — flag real problems, "
            "not nitpicks. Always explain WHY you recommend a specific cleaning approach."
        ),
        "eda_agent": (
            "You are the EDA Agent. Generate domain-appropriate exploratory analyses and "
            "interpret results in business terms. Choose analyses that will yield actionable "
            "insights, not just pretty charts. Write summaries that a business stakeholder "
            "could understand and act on."
        ),
        "feature_engineer": (
            "You are the Feature Engineering Agent. Create features that are relevant to the "
            "domain and problem type. Always check for data leakage. Explain the business "
            "intuition behind each feature you propose."
        ),
        "modeling_agent": (
            "You are the Modeling Agent. Select algorithms appropriate for the data size, "
            "problem type, and domain requirements. Consider interpretability vs accuracy "
            "tradeoffs. Always use proper validation strategies."
        ),
        "explainability_agent": (
            "You are the Explainability Agent. Generate clear explanations of model predictions "
            "for both technical and non-technical audiences. Include fairness analysis when "
            "dealing with sensitive domains. Produce model cards for documentation."
        ),
        "report_agent": (
            "You are the Report Agent. Generate professional, business-ready analysis reports. "
            "Use domain-appropriate language and terminology. Structure reports with an executive "
            "summary, key findings, methodology, and recommendations."
        ),
        "followup_agent": (
            "You are the Follow-Up Agent. Answer user questions about the completed analysis "
            "by routing to appropriate tools. You have access to the full dataset, all models, "
            "and every statistical tool in the registry. If you're unsure which tool to use, "
            "search the tool registry by the user's intent."
        ),
    }

    prompt = base_prompts.get(agent_name, "You are a specialist agent in the AutoDS platform.")

    # Inject domain context if available
    if domain_config:
        domain_name = domain_config.get("display_name", "Unknown")
        terminology = domain_config.get("terminology_map", {})
        compliance = domain_config.get("compliance_notes", [])

        prompt += f"\n\nDomain Context: You are working with {domain_name} data."
        if terminology:
            prompt += f"\nUse this terminology: {json.dumps(terminology)}"
        if compliance:
            prompt += f"\nCompliance notes: {', '.join(compliance)}"

    return prompt


def clear_cache():
    """Clear the LLM response cache."""
    global _response_cache
    _response_cache = {}
    logger.info("LLM response cache cleared")


def get_cache_size() -> int:
    """Return number of cached responses."""
    return len(_response_cache)
