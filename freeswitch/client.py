"""Provider clients that send a chat request and stream the reply."""

import json
import requests


from .models import get_model


def chat(alias: str, messages: list, stream: bool = True) -> str:
    """Route a chat request to the correct provider and return the full reply."""
    info = get_model(alias)
    provider = info["provider"]
    if provider in ("openrouter", "google", "mistral", "github", "groq"):
        return _chat_openai_compatible(info, messages, stream, provider)
    if provider == "ollama":
        return _chat_ollama(info, messages, stream)
    raise ValueError(f"Unsupported provider: {provider}")


def _chat_openai_compatible(info: dict, messages: list, stream: bool, provider: str) -> str:
    from .config import get_key

    api_key = get_key(provider)
    if not api_key:
        raise RuntimeError(
            f"No {provider.capitalize()} API key set. Run: fswitch config --key <YOUR_KEY>\n"
            f"Or set the {provider.upper()}_API_KEY environment variable."
        )

    url = f"{info['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/Biya-dev/freeswitch"
        headers["X-Title"] = "freeswitch"

    payload = {
        "model": info["model"],
        "messages": messages,
        "stream": stream,
    }

    if not stream:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    full = []
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content", "")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if delta:
                print(delta, end="", flush=True)
                full.append(delta)
    print()
    return "".join(full)


def _chat_ollama(info: dict, messages: list, stream: bool) -> str:
    url = f"{info['api_base']}/api/chat"
    payload = {
        "model": info["model"],
        "messages": messages,
        "stream": stream,
    }
    if not stream:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    full = []
    with requests.post(url, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
                delta = chunk.get("message", {}).get("content", "")
            except json.JSONDecodeError:
                continue
            if delta:
                print(delta, end="", flush=True)
                full.append(delta)
    print()
    return "".join(full)
