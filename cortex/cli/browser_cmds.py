import asyncio
import click
from rich.console import Console
from cortex.browser.agent import SovereignBrowserAgent

console = Console()

@click.group()
def browser():
    """BROWSER-Ω: Autonomous Sovereign Web Automation."""
    pass

@browser.command()
@click.argument("url")
@click.option("--objective", "-o", required=True, help="The action BROWSER-Ω should achieve on the page.")
@click.option("--headless", is_flag=True, default=False, help="Run without visible UI.")
@click.option("--provider", default=None, help="LLM Provider override (e.g. ollama, openrouter)")
@click.option("--model", default=None, help="Model override")
def surf(url: str, objective: str, headless: bool, provider: str, model: str):
    """Deploy BROWSER-Ω to a URL with a specific objective."""
    console.print(f"[bold cyan]Deploying BROWSER-Ω[/bold cyan]: {objective}")
    
    # Initialize LLMProvider optionally with user overrides
    kwargs = {}
    if provider: kwargs["provider"] = provider
    if model: kwargs["model"] = model
    
    from cortex.llm.provider import LLMProvider
    llm = LLMProvider(**kwargs)
    
    agent = SovereignBrowserAgent(objective=objective, llm_provider=llm)
    # We optionally could override headless state if we modify engine
    
    try:
        asyncio.run(agent.run(url))
        console.print("[bold green]BROWSER-Ω Execution Complete.[/bold green]")
    except KeyboardInterrupt:
        console.print("[bold yellow]BROWSER-Ω Execution Aborted.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]BROWSER-Ω Error:[/bold red] {e}")

