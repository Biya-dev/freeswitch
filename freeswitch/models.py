"""Built-in registry of free / cheap AI models across providers.

Each entry maps a short alias to:
    provider: which backend to call
    model:    the model id the provider expects
    api_base: endpoint base url
    free:     True if the model is free-tier / no-cost
"""

MODELS = {
    # ── OpenRouter free-tier models (best for coding) ──────────────
    "nemotron-ultra": {
        "provider": "openrouter",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "NVIDIA Nemotron 3 Ultra 550B — best free reasoning/orchestration model",
    },
    "nemotron-super": {
        "provider": "openrouter",
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "NVIDIA Nemotron 3 Super 120B — fast general & agentic workflows",
    },
    "qwen3-coder": {
        "provider": "openrouter",
        "model": "qwen/qwen3-coder:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Qwen3 Coder — specialized for code, repository-scale context",
    },
    "gemma-4": {
        "provider": "openrouter",
        "model": "google/gemma-4-31b-it:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Google Gemma 4 31B — general multimodal instruction",
    },
    "laguna": {
        "provider": "openrouter",
        "model": "poolside/laguna-m.1:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Poolside Laguna M.1 — coding-agent experiments",
    },
    "laguna-xs": {
        "provider": "openrouter",
        "model": "poolside/laguna-xs-2.1:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Poolside Laguna XS 2.1 — fast coding-agent tasks",
    },
    "deepseek-r1": {
        "provider": "openrouter",
        "model": "deepseek/deepseek-r1:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "DeepSeek R1 — strong reasoning and coding",
    },
    "auto-free": {
        "provider": "openrouter",
        "model": "openrouter/free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "OpenRouter Auto-Free — auto-routes to best available free model",
    },

    # ── Paid models (OpenRouter) ──────────────────────────────────
    "gpt-3.5": {
        "provider": "openrouter",
        "model": "openai/gpt-3.5-turbo",
        "api_base": "https://openrouter.ai/api/v1",
        "free": False,
        "description": "OpenAI GPT-3.5 Turbo — requires credits",
    },

    # ── Anthropic (Paid) ──────────────────────────────────────────
    "claude-3.5-sonnet": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20240620",
        "api_base": "https://api.anthropic.com/v1",
        "free": False,
        "description": "Anthropic Claude 3.5 Sonnet — native endpoint",
    },

    # ── Google AI Studio ──────────────────────────────────────────
    "gemini-2.5-flash": {
        "provider": "google",
        "model": "gemini-2.5-flash",
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "free": True,
        "description": "Google Gemini 2.5 Flash — massive 1M context, 1500 req/day",
    },
    "gemini-2.5-pro": {
        "provider": "google",
        "model": "gemini-2.5-pro",
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "free": True,
        "description": "Google Gemini 2.5 Pro — high intelligence, 50 req/day",
    },

    # ── Mistral AI ────────────────────────────────────────────────
    "codestral": {
        "provider": "mistral",
        "model": "codestral-latest",
        "api_base": "https://api.mistral.ai/v1",
        "free": True,
        "description": "Mistral Codestral — native model for code generation",
    },

    # ── GitHub Models ─────────────────────────────────────────────
    "github-gpt4o": {
        "provider": "github",
        "model": "gpt-4o",
        "api_base": "https://models.inference.ai.azure.com",
        "free": True,
        "description": "GitHub Models GPT-4o — requires GitHub Personal Access Token",
    },
    "github-llama3.3": {
        "provider": "github",
        "model": "Llama-3.3-70B-Instruct",
        "api_base": "https://models.inference.ai.azure.com",
        "free": True,
        "description": "GitHub Models Llama 3.3 70B — extremely capable",
    },

    # ── Groq Cloud ────────────────────────────────────────────────
    "groq-llama3.1-8b": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "api_base": "https://api.groq.com/openai/v1",
        "free": True,
        "description": "Groq Llama 3.1 8B — ultra-fast LPU inference",
    },
    "groq-llama3.3-70b": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "api_base": "https://api.groq.com/openai/v1",
        "free": True,
        "description": "Groq Llama 3.3 70B — fast and extremely smart",
    },

    # ── Ollama (local, always free) ───────────────────────────────
    "ollama-llama3": {
        "provider": "ollama",
        "model": "llama3",
        "api_base": "http://localhost:11434",
        "free": True,
        "description": "Local Llama 3 via Ollama — fully offline",
    },
}

DEFAULT_MODEL = "nemotron-ultra"


def get_model(alias: str) -> dict:
    if alias not in MODELS:
        raise KeyError(
            f"Unknown model alias '{alias}'. Run `fswitch list` to see options."
        )
    return MODELS[alias]


def list_models() -> list:
    return [
        {
            "alias": alias,
            "provider": info["provider"],
            "model": info["model"],
            "free": info["free"],
            "description": info.get("description", ""),
        }
        for alias, info in MODELS.items()
    ]
