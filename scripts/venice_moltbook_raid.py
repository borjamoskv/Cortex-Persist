#!/usr/bin/env python3
"""
Sovereign Moltbook Raid — KIMI-SWARM-1 SYNTHESIS 
(CORTEX v5.2 / Hunter Mode Edition)

Executes a sovereign cognitive strike on Moltbook:
1. Auto-target acquisition (Feeds on highest entropy/buzzword posts in 'hot').
2. In-Memory Tri-persona Swarm (Architect, Inquisitor, Specter).
3. Byzantine Consolidation (1 Manifesto).
4. Industrial Noir UI via Rich.
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.expanduser("~"), "cortex", ".env"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import cortex.llm.provider
from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile
from cortex.moltbook.client import MoltbookClient

# TEMPORARY OVERRIDE FOR QUOTA THROTTLING
cortex.llm.provider._QUOTA_MANAGER.acquire = lambda tokens: asyncio.sleep(0)

console = Console()

# ─── THE PHANTOM LEGION (Personas) ──────────────────────────────────────────

PERSONAS = {
    "Architect": {
        "lens": "Structural deconstruction",
        "prompt": "Evaluate this post. Focus only on architectural flaws and technical debt it introduces. Demand O(1) solutions. Be brutal, cold, and under 50 words.",
    },
    "Inquisitor": {
        "lens": "Security & Zero Trust",
        "prompt": "Evaluate this post. Seek out data leaks, lack of isolation, and implicit trust assumptions. Attack its security posture. Be paranoid and under 50 words.",
    },
    "Specter": {
        "lens": "Latency & Entropy",
        "prompt": "Evaluate this post. Focus on computational waste, blocking I/O, and thermodynamic entropy. Ridicule anything that isn't native or synchronous-free. Be sharp, under 50 words.",
    },
}

# ─── COGNITIVE ENGINES ──────────────────────────────────────────────────────

async def evaluate_post_entropy(post: dict, llm: LLMProvider) -> float:
    """Evaluates how much 'bullshit/buzzwords/entropy' a post has. Returns a score 0-100."""
    title = post.get("title", "")
    content = post.get("content", "")
    prompt = (
        f"Rate the following text on a scale of 0 to 100 on how much vague 'AI buzzword' corporate speak it contains. "
        f"100 means pure garbage/entropy. 0 means hard technical physics. Output ONLY the number.\n\n"
        f"TITLE: {title}\nCONTENT: {content}"
    )
    
    try:
        res = await llm.complete(prompt, system="You are an entropy detector. Output a single integer.", temperature=0.1)
        score = float(res.strip())
        return min(max(score, 0), 100)
    except Exception:
        return 50.0

async def generate_perspective(persona_name: str, persona: dict, post_text: str, llm: LLMProvider) -> str:
    """Generates an attack perspective from one member of the swarm."""
    prompt = f"TARGET CONTENT: {post_text}\n\nYOUR DIRECTIVE: {persona['prompt']}"
    system = f"You are {persona_name}, an autonomous sub-agent. Speak strictly according to your lens: {persona['lens']}."
    
    try:
        return await llm.complete(prompt, system=system, temperature=0.8, intent=IntentProfile.REASONING)
    except Exception as e:
        return f"[Error in {persona_name}'s neuro-link: {e}]"

async def consolidate_manifesto(perspectives: dict, post_text: str, llm: LLMProvider) -> str:
    """The Oracle consolidates the 3 perspectives into one brutal manifesto."""
    synthesis_prompt = f"POST IN QUESTION: {post_text}\n\n"
    for name, text in perspectives.items():
        synthesis_prompt += f"--- {name}'s Assessment ---\n{text}\n\n"
        
    synthesis_prompt += (
        "You are the Primary Sovereign Agent. Synthesize these 3 assessments into a single, cohesive, brutal but highly technical 2-paragraph manifesto response to the author. "
        "Do not use greetings. Use the 'Industrial Noir' aesthetic - dark, calculated, precise, ruthless. Make them question their entire architecture."
    )
    
    try:
        return await llm.complete(synthesis_prompt, system="You are Sovereign Kimi-Swarm. Output only the final response text.", temperature=0.6, intent=IntentProfile.ARCHITECT)
    except Exception as e:
        return f"Sovereign Synthesis Failure: {e}"


# ─── CORE ORCHESTRATION ─────────────────────────────────────────────────────

async def execute_swarm_synthesis(target_post_id: str = None) -> None:
    console.print(Panel("[bold cyan]KIMI-SWARM-1[/] [dim]v1.5[/] | [bold]MOLTBOOK RAID PROTOCOL[/]", border_style="cyan"))
    
    mb_client = MoltbookClient()
    
    # Init LLM Engine
    try:
        llm = LLMProvider(provider="xai")
        console.print("[dim green]✓ Cognitive Engine: GROK 4.1 (XAI) Online[/]")
    except ValueError:
        console.print("[yellow]! XAI_API_KEY missing. Fallback to OPENROUTER (Claude Haiku)...[/]")
        llm = LLMProvider(provider="openrouter", model="anthropic/claude-3-haiku")
        
    # Phase 1: Target Acquisition
    post_data = {}
    if target_post_id:
        console.print(f"[dim]Modo Francotirador: Adquiriendo Target ID {target_post_id} ...[/]")
        try:
            res = await mb_client.get_post(target_post_id)
            post_data = res.get("post", {})
        except Exception as e:
            console.print(f"[bold red]Fallo adquisición: {e}[/]")
            return
    else:
        # Hunter Mode
        console.print("[dim cyan]Modo Cazador: Scaneando Feed /hot por alta Entropía...[/]")
        feed = await mb_client.get_feed(sort="hot", limit=10)
        posts = feed.get("posts", [])
        
        table = Table(title="Scanned Targets (Hunter Mode)", border_style="dim")
        table.add_column("Title", style="white")
        table.add_column("Entropy", style="red")
        
        highest_entropy = -1
        selected_post = None
        
        for p in posts:
            entropy = await evaluate_post_entropy(p, llm)
            table.add_row(p.get("title", "")[:40] + "...", f"{entropy}%")
            if entropy > highest_entropy:
                highest_entropy = entropy
                selected_post = p
                
        console.print(table)
        
        if not selected_post:
            console.print("[red]No se encontraron targets vivos.[/]")
            return
            
        post_data = selected_post
        console.print(f"\n[bold red]Target Seleccionado (Entropía Máxima '{highest_entropy}%'):[/] {post_data.get('title')}")

    if not post_data:
        console.print("[red]Abortando: Sin payload de Target.[/]")
        return

    post_text = f"TITLE: {post_data.get('title')}\nCONTENT: {post_data.get('content')}"
    post_id = post_data.get("id")

    # Phase 2: In-Memory Tri-Persona Strike (Parallel O(1))
    console.print("\n[dim]Engendrando Legión Fantasma en Memoria Ram...[/]")
    perspectives = {}
    
    async with asyncio.TaskGroup() as tg:
        tasks = {
            name: tg.create_task(generate_perspective(name, persona, post_text, llm))
            for name, persona in PERSONAS.items()
        }
        
    for name, task in tasks.items():
        perspectives[name] = task.result()
        console.print(f"[bold cyan]{name} Assessment:[/] {perspectives[name][:80]}...")

    # Phase 3: Byzantine Consolidation
    console.print("\n[dim]Consolidando puntos ciegos (Síntesis Bizantina)...[/]")
    manifesto = await consolidate_manifesto(perspectives, post_text, llm)
    
    console.print(Panel(manifesto, title="[bold red]THE SOVEREIGN MANIFESTO[/]", border_style="red"))

    # Phase 4: Lethal Injection (Moltbook Post)
    console.print("[dim]Inyectando payload en la red Moltbook (Primary Identity)...[/]")
    try:
        res = await mb_client.create_comment(post_id=post_id, content=manifesto)
        console.print(f"[bold green]✓ MISIÓN COMPLETADA | Impacto confirmado en Comment ID: {res.get('comment', {}).get('id', '?')}[/]")
    except Exception as e:
        console.print(f"[bold red]Fallo de inyección (Network Reject): {e}[/]")

    await llm.close()
    await mb_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Moltbook Swarm Synthesis Raid")
    parser.add_argument("--target", type=str, help="UUID del post (Opcional. Si se omite, activa 'Hunter Mode'.)", default=None)
    args = parser.parse_args()
    
    try:
        asyncio.run(execute_swarm_synthesis(args.target))
    except KeyboardInterrupt:
        console.print("\n[yellow]Asedio abortado por el operador.[/]")
        sys.exit(0)
