"""Config persistence: which model is active + API keys."""

import os
import json
import copy

from . import CONFIG_FILE, ensure_config_dir

DEFAULTS = {
    "active": "nemotron-ultra",
    "keys": {
        "openrouter": "",
        "google": "",
        "mistral": "",
        "github": "",
        "groq": "",
    },
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return copy.deepcopy(DEFAULTS)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    merged = copy.deepcopy(DEFAULTS)
    merged.update(data)
    merged.setdefault("keys", {})
    for provider in DEFAULTS["keys"]:
        merged["keys"].setdefault(provider, "")
    return merged


def save_config(config: dict) -> None:
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_active() -> str:
    return load_config()["active"]


def set_active(alias: str) -> None:
    config = load_config()
    config["active"] = alias
    save_config(config)


def set_key(provider: str, key: str) -> None:
    config = load_config()
    config.setdefault("keys", {})[provider] = key
    save_config(config)


def get_key(provider: str) -> str:
    # Check environment variable first (e.g. OPENROUTER_API_KEY)
    if provider == "github":
        env_key = os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GITHUB_API_KEY", "")
        if env_key:
            return env_key
    env_key = os.environ.get(f"{provider.upper()}_API_KEY", "")
    if env_key:
        return env_key
    return load_config().get("keys", {}).get(provider, "")
