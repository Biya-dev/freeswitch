"""Agent implementation with tool calling capabilities.

Allows the AI model to read/write files, list directories, and execute shell commands.
"""

import subprocess
import json
import logging
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.syntax import Syntax

from .config import get_key
from .models import get_model

# Configure module‑level logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a string pattern in the workspace files recursively.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The text pattern to search for (case-insensitive)."},
                    "path": {"type": "string", "description": "The directory path to search. Defaults to current directory '.'"}
                },
                "required": ["query"],
            },
        },
    },
]

# Tool implementations
def tool_list_directory(path: str = ".") -> str:
    """Return a JSON payload containing a sorted list of files/folders in *path*.

    The function never raises; errors are captured and reported in the JSON
    ``status`` field.
    """
    try:
        p = Path(path)
        items: List[str] = []
        for child in p.iterdir():
            suffix = "/" if child.is_dir() else ""
            items.append(f"{child.name}{suffix}")
        return json.dumps({"status": "success", "contents": sorted(items)})
    except Exception as e:
        logger.error("list_directory failed: %s", e)
        return json.dumps({"status": "error", "message": str(e)})


def tool_read_file(path):
    try:
        p = Path(path)
        if not p.is_file():
            return json.dumps({"status": "error", "message": f"{path} is not a file."})
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def tool_write_file(path: str, content: str) -> str:
    """Write *content* to *path*, creating parent directories as needed.

    Returns a JSON response indicating success or error.
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({"status": "success", "message": f"Successfully wrote to {path}"})
    except Exception as e:
        logger.error("write_file failed: %s", e)
        return json.dumps({"status": "error", "message": str(e)})


def tool_edit_file(path: str, old_content: str, new_content: str) -> str:
    """Replace a unique *old_content* block with *new_content* in *path*.

    The function validates existence, uniqueness, and returns a JSON response.
    """
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
        logger.error("edit_file failed: %s", e)
        return json.dumps({"status": "error", "message": str(e)})


def tool_run_command(command: str) -> str:
    """Execute *command* in a subprocess and return a JSON payload.

    The command is run with ``shell=True`` for convenience; output, return
    code, and any error are captured. Errors are reported via the ``status``
    field.
    """
    try:
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
        logger.error("run_command timed out for: %s", command)
        return json.dumps({"status": "error", "message": "Command timed out after 60 seconds."})
    except Exception as e:
        logger.error("run_command failed: %s", e)
        return json.dumps({"status": "error", "message": str(e)})


def tool_search_code(query: str, path: str = ".") -> str:
    """Recursively search all text files under *path* for *query* (case‑insensitive).

    Returns a JSON object with either ``matches`` (list of ``file:line: snippet``)
    or a friendly ``message`` when nothing is found.
    """
    try:
        p = Path(path)
        ignore_dirs = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", "dist", "build", ".egg-info"}
        results: List[str] = []
        query_lower = query.lower()
        
        def search_dir(current_path: Path) -> None:
            for child in sorted(current_path.iterdir()):
                if child.is_dir():
                    if child.name in ignore_dirs:
                        continue
                    search_dir(child)
                elif child.is_file():
                    # Skip binary or non‑code assets
                    if child.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz", ".db", ".sqlite", ".pyc"}:
                        continue
                    try:
                        content = child.read_text(encoding="utf-8", errors="replace")
                        for idx, line in enumerate(content.splitlines(), 1):
                            if query_lower in line.lower():
                                try:
                                    rel = child.relative_to(Path.cwd())
                                    path_str = str(rel)
                                except ValueError:
                                    path_str = str(child)
                                results.append(f"{path_str}:{idx}: {line.strip()}")
                    except Exception as exc:
                        logger.debug("Skipping file %s due to read error: %s", child, exc)
        
        search_dir(p)
        if not results:
            return json.dumps({"status": "success", "message": "No matches found."})
        return json.dumps({"status": "success", "matches": results[:100]})
    except Exception as e:
        logger.error("search_code failed: %s", e)
        return json.dumps({"status": "error", "message": str(e)})


def is_outside_workspace(path: Optional[str]) -> bool:
    if not path:
        return False
    try:
        target = Path(path).resolve()
        workspace = Path.cwd().resolve()
        return not (target == workspace or workspace in target.parents)
    except Exception:
        return True


def execute_tool(name, arguments):
    """Router to call local functions and handle safety prompt."""
    if name == "list_directory":
        path = arguments.get("path", ".")
        if is_outside_workspace(path):
            console.print(f"\n[bold red]WARNING: Agent is attempting to access a directory outside the workspace![/]")
            console.print(f"[bold red]Path:[/] {path}")
        console.print(f"\n[bold yellow]Agent Action:[/] List directory [cyan]'{path}'[/]")
        if Confirm.ask("Allow action?"):
            return tool_list_directory(path)
        return json.dumps({"status": "error", "message": "User denied list_directory permission."})

    elif name == "read_file":
        path = arguments.get("path")
        if is_outside_workspace(path):
            console.print(f"\n[bold red]WARNING: Agent is attempting to read outside the workspace![/]")
            console.print(f"[bold red]Path:[/] {path}")
        console.print(f"\n[bold yellow]Agent Action:[/] Read file [cyan]'{path}'[/]")
        if Confirm.ask("Allow action?"):
            return tool_read_file(path)
        return json.dumps({"status": "error", "message": "User denied read_file permission."})

    elif name == "write_file":
        path = arguments.get("path")
        content = arguments.get("content", "")
        if is_outside_workspace(path):
            console.print(f"\n[bold red]WARNING: Agent is attempting to write outside the workspace![/]")
            console.print(f"[bold red]Path:[/] {path}")
        console.print(f"\n[bold yellow]Agent Action:[/] Write file [cyan]'{path}'[/]")
        
        # Preview file contents in syntax panel
        ext = Path(path).suffix.strip(".") if path else "txt"
        syntax = Syntax(content[:500] + ("\n... [truncated]" if len(content) > 500 else ""), ext or "txt", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"Preview: {path}", border_style="dim"))

        if Confirm.ask("Allow action?"):
            return tool_write_file(path, content)
        return json.dumps({"status": "error", "message": "User denied write_file permission."})

    elif name == "edit_file":
        path = arguments.get("path")
        old_content = arguments.get("old_content", "")
        new_content = arguments.get("new_content", "")
        if is_outside_workspace(path):
            console.print(f"\n[bold red]WARNING: Agent is attempting to edit outside the workspace![/]")
            console.print(f"[bold red]Path:[/] {path}")
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

    elif name == "search_code":
        query = arguments.get("query")
        path = arguments.get("path", ".")
        if is_outside_workspace(path):
            console.print(f"\n[bold red]WARNING: Agent is attempting to search outside the workspace![/]")
            console.print(f"[bold red]Path:[/] {path}")
        console.print(f"\n[bold yellow]Agent Action:[/] Search code for [cyan]'{query}'[/] in [cyan]'{path}'[/]")
        if Confirm.ask("Allow action?"):
            return tool_search_code(query, path)
        return json.dumps({"status": "error", "message": "User denied search_code permission."})

    return json.dumps({"status": "error", "message": f"Unknown tool name: {name}"})


def get_workspace_files(max_depth=3) -> list[str]:
    files = []
    ignore_dirs = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", "dist", "build", ".egg-info"}
    
    def traverse(path: Path, depth: int):
        if depth > max_depth:
            return
        try:
            for item in sorted(path.iterdir()):
                if item.is_dir():
                    if item.name in ignore_dirs:
                        continue
                    traverse(item, depth + 1)
                elif item.is_file():
                    try:
                        rel = item.relative_to(Path.cwd())
                        files.append(str(rel))
                    except ValueError:
                        files.append(str(item))
        except Exception:
            pass
            
    traverse(Path.cwd(), 1)
    return files


def is_git_repo() -> bool:
    try:
        res = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def offer_git_commit(alias: str) -> None:
    if not is_git_repo():
        return
        
    res = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if not res.stdout.strip():
        return
        
    console.print("\n[bold green]Changes detected in workspace:[/]")
    console.print(res.stdout)
    
    if Confirm.ask("Would you like to commit these changes?"):
        diff_res = subprocess.run("git diff HEAD", shell=True, capture_output=True, text=True)
        diff_text = diff_res.stdout
        
        console.print("[dim]Generating commit message using active model...[/]")
        prompt = (
            "Write a short, professional, 1-line git commit message for these changes. "
            "Do not include quotes or markdown formatting, just return the raw message.\n\n"
            f"Git status:\n{res.stdout}\n\n"
            f"Git diff:\n{diff_text[:4000]}"
        )
        
        try:
            from .client import chat
            msg = chat(alias, [{"role": "user", "content": prompt}], stream=False).strip()
            msg = msg.strip('"`').replace("Commit message:", "").strip()
        except Exception:
            msg = "feat: updates from fswitch agent"
            
        console.print(f"Commit message: [bold cyan]{msg}[/]")
        if Confirm.ask("Proceed with this commit message?"):
            subprocess.run("git add -A", shell=True)
            subprocess.run(f'git commit -m "{msg}"', shell=True)
            console.print("[green]>> Changes committed successfully![/]")


def run_agent_loop(alias: str, task: str, test_command: Optional[str] = None) -> None:
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
    
    # Automatically add workspace context tree
    workspace_files = get_workspace_files()
    if workspace_files:
        files_str = "\n".join(f"- {f}" for f in workspace_files[:100])
        system_prompt += f"\n\nFiles present in the current workspace directory:\n{files_str}"

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
        
        # Helper: send request with exponential backoff
        def _post_with_retry() -> requests.Response:
            import time
            max_retries = 3
            delay = 1.0
            for attempt in range(max_retries):
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=90)
                    resp.raise_for_status()
                    return resp
                except requests.HTTPError as e:
                    status = e.response.status_code if e.response is not None else 500
                    if attempt == max_retries - 1 or (status != 429 and not (500 <= status < 600)):
                        raise
                    console.print(f"[yellow]Warning: HTTP {status} from provider. Retrying in {delay}s...[/]")
                    time.sleep(delay)
                    delay *= 2
                except requests.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    console.print(f"[yellow]Warning: Request exception ({e}). Retrying in {delay}s...[/]")
                    time.sleep(delay)
                    delay *= 2
            # Should never reach here
            raise RuntimeError("Exhausted retries for provider request")
        
        resp = _post_with_retry()
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
            if test_command:
                console.print(f"\n[bold yellow]>> Running test command:[/] [cyan]'{test_command}'[/]...")
                test_res = subprocess.run(test_command, shell=True, capture_output=True, text=True)
                if test_res.returncode == 0:
                    console.print("[bold green]>> Tests passed successfully![/]")
                    console.print("\n[bold green]>> Agent completed task successfully![/]\n")
                    offer_git_commit(alias)
                    break
                else:
                    console.print(f"[bold red]>> Tests failed with code {test_res.returncode}![/]")
                    error_output = (test_res.stdout + "\n" + test_res.stderr).strip()
                    console.print(Panel(error_output[:1000] + ("\n... [truncated]" if len(error_output) > 1000 else ""), 
                                        title="Test Failure Output", border_style="red"))
                    
                    feedback = (
                        f"The test command '{test_command}' failed with exit code {test_res.returncode}.\n"
                        f"Please examine the test output below, identify the problem, edit the files, and run again to verify.\n\n"
                        f"Test Output:\n{error_output}"
                    )
                    messages.append({"role": "user", "content": feedback})
                    continue
            else:
                console.print("\n[bold green]>> Agent completed task successfully![/]\n")
                offer_git_commit(alias)
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
        offer_git_commit(alias)
