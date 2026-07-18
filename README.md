# freeswitch

[![tests](https://github.com/Biya-dev/freeswitch/actions/workflows/tests.yml/badge.svg)](https://github.com/Biya-dev/freeswitch/actions)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](https://python.org)

> **One command. Every free AI model. Zero cost.**

Tired of juggling API keys, rewriting boilerplate, and guessing which free model actually works? `freeswitch` gives you **one CLI** to switch between, chat with, and benchmark free AI models — no vendor lock-in, no credit card.

```bash
pip install freeswitch
fswitch use nemotron-ultra
fswitch chat "write a REST API in Python"
```

<!-- 
TODO: Add a demo GIF here!
![freeswitch demo](./demo.gif)
-->

## Features

- **Free by default** — ships with 8+ free-tier models ready to go
- **One command to switch** — `fswitch use <alias>` and you're done
- **Interactive REPL** — multi-turn conversations with `/switch` between models mid-chat
- **Autonomous agent** — `fswitch agent "build a todo app"` — reads/writes files, runs commands
- **Benchmark mode** — race all free models against each other on the same prompt
- **Local models** — works with Ollama for fully offline, private AI
- **Tiny footprint** — pure Python, just `requests` + `rich`, nothing heavy

## Install

```bash
pip install freeswitch
```

Or from source:

```bash
git clone https://github.com/Biya-dev/freeswitch
cd freeswitch
pip install .
```

## Setup (30 seconds)

1. Get a **free** API key from [openrouter.ai/keys](https://openrouter.ai/keys) (no credit card needed)
2. Tell freeswitch about it:

```bash
fswitch config --key sk-or-v1-your-key-here
```

That's it. You're ready.

## Usage

### List available models

```bash
fswitch list
```

### Switch model

```bash
fswitch use nemotron-ultra
```

### Chat (single prompt)

```bash
fswitch chat "explain quicksort in 3 lines"
fswitch chat -m deepseek-r1 "solve this leetcode problem: two sum"
```

### Interactive REPL (multi-turn)

```bash
fswitch repl
```

Inside the REPL:
- Type naturally to chat
- `/switch deepseek-r1` to change model mid-conversation
- `/models` to list available models
- `exit` to quit

### Autonomous Agent

```bash
fswitch agent "create a Python script that fetches weather data"
fswitch agent -m qwen3-coder "refactor this project to use async"
```

The agent can:
- Read and write files on your machine
- Run shell commands (with your approval)
- Diagnose errors and self-correct
- Complete multi-step coding tasks autonomously

Every action requires your confirmation before executing.

### Benchmark all free models

```bash
fswitch benchmark
fswitch benchmark --prompt "write a binary search in Rust"
```

Races every free model on the same prompt and shows you which is fastest.

## Supported Models

| Alias | Model | Free | Best for |
|-------|-------|:----:|----------|
| `nemotron-ultra` | NVIDIA Nemotron Ultra 253B | Yes | Complex coding, agentic tasks |
| `nemotron-super` | NVIDIA Nemotron Super 49B | Yes | Fast + smart balance |
| `qwen3-coder` | Qwen3 Coder 480B | Yes | Code generation, 1M context |
| `deepseek-r1` | DeepSeek R1 | Yes | Reasoning + math |
| `gemini-flash` | Google Gemini 2.0 Flash | Yes | Fast responses, vision |
| `llama-3.1-8b` | Meta Llama 3.1 8B | Yes | Lightweight tasks |
| `mistral-7b` | Mistral 7B | Yes | Efficient all-rounder |
| `qwen-2.5-7b` | Qwen 2.5 7B | Yes | Multilingual |
| `ollama-llama3` | Llama 3 (local) | Yes | Fully offline |

## Local Models with Ollama

Install [Ollama](https://ollama.com), pull a model, and use it completely offline:

```bash
ollama pull llama3
fswitch use ollama-llama3
fswitch chat "hello local model!"
```

## Environment Variables

You can also set your API key via environment variable instead of `fswitch config`:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

## Contributing

PRs welcome! Here's how to help:

- **Add a model**: edit `freeswitch/models.py` — just add a new dict entry
- **Add a provider**: add a new function in `freeswitch/client.py`
- **Report issues**: [open an issue](https://github.com/Biya-dev/freeswitch/issues)

Please open an issue first for bigger changes.

## License

MIT — do whatever you want with it.

---

**If this saved you time, drop a star on the repo!**
