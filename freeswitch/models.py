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
        "model": "nvidia/llama-3.1-nemotron-ultra-253b:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "NVIDIA Nemotron Ultra 253B — best free agentic/coding model",
    },
    "nemotron-super": {
        "provider": "openrouter",
        "model": "nvidia/llama-3.1-nemotron-super-49b:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "NVIDIA Nemotron Super 49B — fast and smart",
    },
    "qwen3-coder": {
        "provider": "openrouter",
        "model": "qwen/qwen3-coder-480b-a35b:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Qwen3 Coder 480B — specialized for code, 1M context",
    },
    "deepseek-r1": {
        "provider": "openrouter",
        "model": "deepseek/deepseek-r1:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "DeepSeek R1 — strong reasoning and coding",
    },
    "llama-3.1-8b": {
        "provider": "openrouter",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Llama 3.1 8B — lightweight and fast",
    },
    "mistral-7b": {
        "provider": "openrouter",
        "model": "mistralai/mistral-7b-instruct:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Mistral 7B — efficient all-rounder",
    },
    "qwen-2.5-7b": {
        "provider": "openrouter",
        "model": "qwen/qwen-2.5-7b-instruct:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Qwen 2.5 7B — great multilingual support",
    },
    "gemini-flash": {
        "provider": "openrouter",
        "model": "google/gemini-2.0-flash-exp:free",
        "api_base": "https://openrouter.ai/api/v1",
        "free": True,
        "description": "Google Gemini 2.0 Flash — fast with vision",
    },

    # ── Paid models (OpenRouter) ──────────────────────────────────
    "gpt-3.5": {
        "provider": "openrouter",
        "model": "openai/gpt-3.5-turbo",
        "api_base": "https://openrouter.ai/api/v1",
        "free": False,
        "description": "OpenAI GPT-3.5 Turbo — requires credits",
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
