"""Command-line interface for freeswitch."""

import argparse
import sys
import time

from rich.console import Console
from rich.table import Table

import requests

from . import config
from .client import chat
from .models import list_models, get_model

console = Console(force_terminal=True)


def cmd_list(_args) -> None:
    """List all available models in a pretty table."""
    table = Table(
        title="freeswitch - Available Models",
        title_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Alias", style="cyan bold", no_wrap=True)
    table.add_column("Provider", style="magenta")
    table.add_column("Model ID", style="green")
    table.add_column("Free", justify="center")
    table.add_column("Description", style="dim")

    for m in list_models():
        free_icon = "yes" if m["free"] else "$"
        table.add_row(
            m["alias"],
            m["provider"],
            m["model"],
            free_icon,
            m.get("description", ""),
        )
    console.print(table)

    active = config.get_active()
    console.print(f"\n  Active model: [bold cyan]{active}[/]")
    console.print(f"  Switch with:  [dim]fswitch use <alias>[/]\n")


def cmd_use(args) -> None:
    """Set the active model."""
    info = get_model(args.alias)  # validate alias exists (raises KeyError if not)
    config.set_active(args.alias)
    console.print(f"[green]>> Switched to[/] [bold cyan]{args.alias}[/]")
    console.print(f"  [dim]{info.get('description', '')}[/]")


def cmd_config(args) -> None:
    """Show or set configuration."""
    provider = getattr(args, "provider", "openrouter")
    
    if args.key is not None:
        config.set_key(provider, args.key)
        console.print(f"[green]>> Saved {provider.capitalize()} API key.[/]")
        
    console.print(f"\n  Active model: [bold cyan]{config.get_active()}[/]")
    
    # Show status of all configured keys
    console.print("\n  [bold]API Keys:[/]")
    for p in ("openrouter", "google", "mistral", "github", "groq"):
        key = config.get_key(p)
        if key:
            masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "****"
            console.print(f"  {p.capitalize():<12} [green]{masked}[/]")
        else:
            console.print(f"  {p.capitalize():<12} [red]not set[/]")
            
    console.print("\n  [dim]Set a key with: fswitch config --provider <name> --key sk-...[/]")
    print()


def cmd_chat(args) -> None:
    """Send a single prompt to the active (or specified) model."""
    alias = args.model or config.get_active()
    messages = [{"role": "user", "content": args.prompt}]
    info = get_model(alias)
    console.print(f"[dim]Model:[/] [bold cyan]{alias}[/] [dim]({info.get('description', '')})[/]\n")
    try:
        chat(alias, messages, stream=True)
    except (RuntimeError, ValueError, KeyError, requests.RequestException) as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


def cmd_repl(args) -> None:
    """Interactive chat REPL — multi-turn conversation."""
    alias = args.model or config.get_active()
    info = get_model(alias)
    console.print(f"\n[bold cyan]freeswitch interactive chat[/]")
    console.print(f"[dim]Model:[/] [bold]{alias}[/] [dim]- {info.get('description', '')}[/]")
    console.print("[dim]Type 'exit' or 'quit' to leave. '/switch <alias>' to change model.[/]\n")

    messages = []

    while True:
        try:
            prompt = console.input("[bold green]you>[/] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            break

        prompt = prompt.strip()
        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit", "/exit", "/quit"):
            console.print("[dim]Goodbye![/]")
            break
        if prompt.startswith("/switch "):
            new_alias = prompt.split(" ", 1)[1].strip()
            try:
                get_model(new_alias)
                alias = new_alias
                info = get_model(alias)
                config.set_active(alias)
                console.print(f"[green]>> Switched to[/] [bold cyan]{alias}[/]\n")
            except KeyError as e:
                console.print(f"[red]Error: {e}[/]\n")
            continue
        if prompt == "/models":
            cmd_list(None)
            continue

        messages.append({"role": "user", "content": prompt})

        console.print(f"[bold cyan]{alias}>[/] ", end="")
        try:
            reply = chat(alias, messages, stream=True)
            messages.append({"role": "assistant", "content": reply})
        except (RuntimeError, ValueError, KeyError, requests.RequestException) as e:
            console.print(f"[red]Error: {e}[/]")
            messages.pop()  # remove failed user message
        print()


def cmd_benchmark(args) -> None:
    """Benchmark free models by sending the same prompt and timing responses."""
    prompt = args.prompt or "Write a Python function to check if a number is prime."
    free_models = [m for m in list_models() if m["free"] and m["provider"] == "openrouter"]

    console.print(f"\n[bold cyan]Benchmarking {len(free_models)} free models[/]")
    console.print(f"[dim]Prompt: {prompt[:80]}...[/]\n")

    results = []
    for m in free_models:
        alias = m["alias"]
        console.print(f"  [dim]Testing[/] [cyan]{alias}[/]...", end=" ")
        messages = [{"role": "user", "content": prompt}]
        try:
            start = time.time()
            reply = chat(alias, messages, stream=False)
            elapsed = time.time() - start
            results.append({
                "alias": alias,
                "time": elapsed,
                "chars": len(reply),
                "status": "OK",
            })
            console.print(f"[green]{elapsed:.1f}s[/] ({len(reply)} chars)")
        except Exception as e:
            results.append({
                "alias": alias,
                "time": 0,
                "chars": 0,
                "status": "FAIL",
            })
            console.print(f"[red]failed: {e}[/]")

    # Summary table
    console.print()
    table = Table(title="Benchmark Results", border_style="dim")
    table.add_column("Model", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Time", justify="right", style="yellow")
    table.add_column("Output Length", justify="right")

    for r in sorted(results, key=lambda x: x["time"] if x["time"] > 0 else 999):
        table.add_row(
            r["alias"],
            r["status"],
            f"{r['time']:.1f}s" if r['time'] > 0 else "-",
            str(r["chars"]),
        )
    console.print(table)


def cmd_agent(args) -> None:
    """Run the autonomous agent loop to complete a task."""
    alias = args.model or config.get_active()
    from .agent import run_agent_loop
    try:
        run_agent_loop(alias, args.task)
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fswitch",
        description="Switch and chat across free AI models with one command.",
    )
    sub = p.add_subparsers(dest="command")

    # fswitch list
    sub.add_parser("list", help="List available models").set_defaults(func=cmd_list)

    # fswitch use <alias>
    pu = sub.add_parser("use", help="Set the active model")
    pu.add_argument("alias", help="Model alias, e.g. nemotron-ultra")
    pu.set_defaults(func=cmd_use)

    # fswitch config [--key KEY] [--provider PROVIDER]
    pc = sub.add_parser("config", help="Show / set configuration")
    pc.add_argument("--key", help="Set API key for a provider")
    pc.add_argument("--provider", default="openrouter", choices=["openrouter", "google", "mistral", "github", "groq"], help="Provider to set the key for")
    pc.set_defaults(func=cmd_config)

    # fswitch chat "prompt"
    pch = sub.add_parser("chat", help="Send a single prompt to the active model")
    pch.add_argument("prompt", help="The prompt to send")
    pch.add_argument("-m", "--model", help="Override the active model for this request")
    pch.set_defaults(func=cmd_chat)

    # fswitch repl (interactive)
    pr = sub.add_parser("repl", help="Interactive multi-turn chat session")
    pr.add_argument("-m", "--model", help="Override the active model")
    pr.set_defaults(func=cmd_repl)

    # fswitch benchmark
    pb = sub.add_parser("benchmark", help="Benchmark all free models")
    pb.add_argument("--prompt", help="Custom prompt for benchmarking")
    pb.set_defaults(func=cmd_benchmark)

    # fswitch agent "task"
    pa = sub.add_parser("agent", help="Run as an autonomous developer agent to complete a task")
    pa.add_argument("task", help="The goal for the agent to achieve")
    pa.add_argument("-m", "--model", help="Override the active model")
    pa.set_defaults(func=cmd_agent)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
