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

    import time
    max_retries = 3
    delay = 1.0
    
    for attempt in range(max_retries):
        try:
            if not stream:
                resp = requests.post(url, headers=headers, json=payload, timeout=120)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            else:
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
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 500
            if attempt == max_retries - 1 or (status != 429 and not (500 <= status < 600)):
                raise
            time.sleep(delay)
            delay *= 2
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2


def _chat_ollama(info: dict, messages: list, stream: bool) -> str:
    # Translate multimodal OpenAI messages format to Ollama format
    formatted_messages = []
    for msg in messages:
        content = msg.get("content")
        role = msg.get("role")
        if isinstance(content, list):
            text = ""
            images = []
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "")
                elif item.get("type") == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        try:
                            # Extract base64 representation
                            _, base64_data = url.split(";base64,", 1)
                            images.append(base64_data)
                        except ValueError:
                            pass
            msg_data = {"role": role, "content": text}
            if images:
                msg_data["images"] = images
            formatted_messages.append(msg_data)
        else:
            formatted_messages.append({"role": role, "content": content})

    url = f"{info['api_base']}/api/chat"
    payload = {
        "model": info["model"],
        "messages": formatted_messages,
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
