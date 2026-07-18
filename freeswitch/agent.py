"""Agent implementation with tool calling capabilities.

Allows the AI model to read/write files, list directories, and execute shell commands.
"""

import subprocess
import json
import requests
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.syntax import Syntax

from .config import get_key
from .models import get_model

console = Console(force_terminal=True)

# Define the tools available to the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories in a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list. Defaults to current directory '.'",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, creating it if it doesn't exist, or overwriting it if it does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write."},
                    "content": {"type": "string", "description": "The full content to write to the file."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Surgically edit an existing file by replacing a specific unique target block of text with new replacement text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to edit."},
                    "old_content": {"type": "string", "description": "The exact unique string/block of code to be replaced. Must match exactly including whitespace and indentation."},
                    "new_content": {"type": "string", "description": "The new replacement string/block of code."},
                },
                "required": ["path", "old_content", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command. Use this to install dependencies, run tests, or run build scripts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute."}
                },
                "required": ["command"],
            },
        },
    },
]

# Tool implementations
def tool_list_directory(path="."):
    try:
        p = Path(path)
        items = []
        for child in p.iterdir():
            suffix = "/" if child.is_dir() else ""
            items.append(f"{child.name}{suffix}")
        return json.dumps({"status": "success", "contents": sorted(items)})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def tool_read_file(path):
    try:
        p = Path(path)
        if not p.is_file():
            return json.dumps({"status": "error", "message": f"{path} is not a file."})
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def tool_write_file(path, content):
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({"status": "success", "message": f"Successfully wrote to {path}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def tool_edit_file(path, old_content, new_content):
    try:
        p = Path(path)
        if not p.is_file():
            return json.dumps({"status": "error", "message": f"{path} is not a file."})
        content = p.read_text(encoding="utf-8")
        if old_content not in content:
            return json.dumps({"status": "error", "message": "Could not find 'old_content' in the target file. Indentation and characters must match exactly."})
        if content.count(old_content) > 1:
            return json.dumps({"status": "error", "message": "'old_content' matched multiple blocks in the target file. Make 'old_content' more unique."})
        new_text = content.replace(old_content, new_content, 1)
        p.write_text(new_text, encoding="utf-8")
        return json.dumps({"status": "success", "message": f"Successfully edited {path}."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def tool_run_command(command):
    try:
        # Use shell=True for convenience, run in current workspace
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.dumps({
            "status": "success",
            "returncode": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "message": "Command timed out after 60 seconds."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def execute_tool(name, arguments):
    """Router to call local functions and handle safety prompt."""
    if name == "list_directory":
        path = arguments.get("path", ".")
        console.print(f"\n[bold yellow]Agent Action:[/] List directory [cyan]'{path}'[/]")
        if Confirm.ask("Allow action?"):
            return tool_list_directory(path)
        return json.dumps({"status": "error", "message": "User denied list_directory permission."})

    elif name == "read_file":
        path = arguments.get("path")
        console.print(f"\n[bold yellow]Agent Action:[/] Read file [cyan]'{path}'[/]")
        if Confirm.ask("Allow action?"):
            return tool_read_file(path)
        return json.dumps({"status": "error", "message": "User denied read_file permission."})

    elif name == "write_file":
        path = arguments.get("path")
        content = arguments.get("content", "")
        console.print(f"\n[bold yellow]Agent Action:[/] Write file [cyan]'{path}'[/]")
        
        # Preview file contents in syntax panel
        ext = Path(path).suffix.strip(".")
        syntax = Syntax(content[:500] + ("\n... [truncated]" if len(content) > 500 else ""), ext or "txt", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"Preview: {path}", border_style="dim"))

        if Confirm.ask("Allow action?"):
            return tool_write_file(path, content)
        return json.dumps({"status": "error", "message": "User denied write_file permission."})

    elif name == "edit_file":
        path = arguments.get("path")
        old_content = arguments.get("old_content", "")
        new_content = arguments.get("new_content", "")
        console.print(f"\n[bold yellow]Agent Action:[/] Edit file [cyan]'{path}'[/]")
        console.print("[red]- Old Content:[/]")
        console.print(old_content)
        console.print("[green]+ New Content:[/]")
        console.print(new_content)
        if Confirm.ask("Allow action?"):
            return tool_edit_file(path, old_content, new_content)
        return json.dumps({"status": "error", "message": "User denied edit_file permission."})

    elif name == "run_command":
        cmd = arguments.get("command")
        console.print(f"\n[bold red]Agent Action (CRITICAL):[/] Run command [cyan]'{cmd}'[/]")
        if Confirm.ask("Allow action?"):
            return tool_run_command(cmd)
        return json.dumps({"status": "error", "message": "User denied run_command permission."})

    return json.dumps({"status": "error", "message": f"Unknown tool name: {name}"})


def run_agent_loop(alias: str, task: str) -> None:
    """Core loop executing instructions using OpenRouter/OpenAI tool call schema."""
    info = get_model(alias)

    provider = info["provider"]
    if provider in ("openrouter", "google", "mistral", "github", "groq"):
        api_key = get_key(provider)
        if not api_key:
            raise RuntimeError(f"No {provider.capitalize()} API key set. Run: fswitch config --key <YOUR_KEY>")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/Biya-dev/freeswitch"
            headers["X-Title"] = "freeswitch"
    elif provider == "ollama":
        headers = {"Content-Type": "application/json"}
    else:
        raise ValueError(f"Agent mode does not support provider: {provider}")

    system_prompt = (
        "You are an autonomous AI coding assistant. You have access to local file system tools "
        "and command execution. Your task is to complete the user's objective systematically. "
        "Rules:\n"
        "1. Discover directory structure first if needed.\n"
        "2. Do not write dummy placeholders. Implement fully functional code.\n"
        "3. Test your changes by running tests or scripts if possible.\n"
        "4. If a step fails, diagnose the error and correct it.\n"
        "5. Explain what you're doing briefly before calling tools."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    url = f"{info['api_base']}/chat/completions"
    if info["provider"] == "ollama":
        url = f"{info['api_base']}/api/chat"

    console.print(f"\n[bold magenta]>> Starting agent loop...[/]")
    console.print(f"[dim]Task:[/] {task}\n")

    steps_limit = 20
    for step in range(steps_limit):
        payload = {
            "model": info["model"],
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
        }

        console.print(f"[bold cyan]Agent is thinking (Step {step+1}/{steps_limit})...[/]")
        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        res_data = resp.json()

        choice = res_data["choices"][0]
        message = choice["message"]
        messages.append(message)

        # Print reasoning/thinking if present
        if message.get("content"):
            console.print(f"\n[bold magenta]Agent:[/] {message['content']}")

        # Check if the model wants to call tools
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            console.print("\n[bold green]>> Agent completed task successfully![/]\n")
            break

        # Process tool calls
        for tool_call in tool_calls:
            call_id = tool_call.get("id")
            func_name = tool_call["function"]["name"]
            raw_args = tool_call["function"]["arguments"]

            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}

            # Execute tool and append result
            result = execute_tool(func_name, args)
            
            # Print short preview of results
            res_preview = result[:200] + ("..." if len(result) > 200 else "")
            console.print(f"[dim]Result:[/] {res_preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": func_name,
                "content": result,
            })
    else:
        console.print("\n[bold red]Limit of 20 steps reached. Agent stopped.[/]\n")
