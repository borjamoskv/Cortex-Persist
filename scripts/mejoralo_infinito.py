#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import asyncio
from typing import Final

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.prompt import Prompt
    from cortex.llm.provider import LLMProvider
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"Error de inicialización: {e}")
    print("Asegúrate de ejecutar esto dentro del entorno virtual de CORTEX (.venv).")
    sys.exit(1)

console = Console()

SYSTEM_PROMPT: Final[str] = """Eres el Algoritmo MEJORAlo 130/100 de CORTEX.
Tu deber es aplicar rigor absoluto: destilar cada iteración aportando perfección, concisión 
y estética Industrial Noir. Si es código: erradica ineficiencias, hazlo seguro, tipeado rigurosamente.
Si es prosa o documentación: purga las excusas, hazlo directo, poderoso.
REGLA DE HIERRO: NO incluyas explicaciones de la mejora. Entrega ÚNICAMENTE 
el resultado evolucionado, listo para sustituir al original o volver a entrar en el bucle."""

JUDGE_PROMPT: Final[str] = """Eres el Árbitro Soberano de CORTEX.
Evalúa el texto o código provisto basándote ESTRICTAMENTE en el estándar Industrial Noir 130/100.
Requisitos: 
- Densidad de información absoluta (cada palabra/línea tiene un propósito).
- Estética afilada, directa y poderosa (cero redundancia).
- Precisión técnica incuestionable.
Retorna ÚNICAMENTE un número entero del 0 al 130 que represente su puntuación de métrica de calidad.
NO EXPLIQUES. NO USES MARKDOWN. SOLO EL NÚMERO."""

async def main() -> None:
    content: str = read_input()
    if not content:
        console.print("[red]✗ Entrada vacía. Bucle abortado.[/red]")
        sys.exit(1)

    provider = LLMProvider(provider="gemini", model="gemini-3-flash-preview")
    console.print(f"[dim]Inicializando el Orquestador Semántico. Motor conectado:[/dim] [bold cyan]{provider.model_name}[/bold cyan]")
    
    current_content = content
    iteration = 1

    try:
        while True:
            console.print(f"\n[bold magenta]► Iteración [{iteration}][/bold magenta] Aplicando MEJORAlo...")
            prompt_text = generate_prompt_text(current_content, iteration)
            
            with console.status(f"[cyan]Destilando Entropía (Fase {iteration}) vía [bold]{provider.model_name}[/bold] (temp: 0.3)...[/cyan]", spinner="dots4"):
                result = await provider.complete(prompt=prompt_text, system=SYSTEM_PROMPT, temperature=0.3)
                
            current_content = result.strip()
            display_result(current_content, iteration)
            
            score = await evaluate_content(provider, current_content)
            display_score(score)
            
            if score >= 130:
                console.print("[bold cyan]⬡ PERFECCIÓN ALCANZADA. El Árbitro sella el constructo automáticamente.[/bold cyan]")
                break

            ans = get_user_input()
            if ans.lower() in ("n", "no", "exit", "quit", "q", "enough", "basta"):
                break
                
            if ans and ans.lower() not in ("y", "yes", "s", "si"):
                current_content = f"{current_content}\n\n[DIRECTIVA DEL DIRECTOR]: {ans}"
                
            iteration += 1

    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold red]✗ Suspensión Táctica Invocada (Ctrl+C / EOF).[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]✗ Falla Catastrófica en el Motor de Fusión:[/bold red] {e}")
    finally:
        await provider.close()
        
    console.print("\n[bold green]✓ CORTEX Auto-Evolución Completada.[/bold green]")
    copy_to_clipboard(current_content)

def read_input() -> str:
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if not os.path.isfile(file_path):
            console.print(f"[bold red]✗ Archivo no encontrado:[/bold red] {file_path}")
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    else:
        console.print(Panel(
            "[dim]Pega el texto, código o idea que deseas someter a evolución continua.[/dim]\n"
            "[dim]Para finalizar el input, presiona[/dim] [bold cyan]Ctrl+D[/bold cyan] [dim](macOS/Linux)[/dim] "
            "[dim]o[/dim] [bold cyan]Ctrl+Z[/bold cyan] [dim]+ Intro (Windows).[/dim]",
            title="[bold yellow]ENTRADA DE CORTEX[/bold yellow]",
            expand=False
        ))
        try:
            return sys.stdin.read().strip()
        except KeyboardInterrupt:
            console.print("\n[red]Cancelado.[/red]")
            sys.exit(0)

def generate_prompt_text(current_content: str, iteration: int) -> str:
    if iteration == 1:
        return f"Evoluciona esta entrada cruda al estándar 130/100:\n\n{current_content}"
    return (
        f"El operador ha dictaminado que la iteración {iteration-1} AÚN se puede mejorar. "
        f"Busca ineficiencias sistémicas, optimizaciones de diseño, abstracciones más "
        f"profundas o prosa más contundente. Elévalo todo al máximo nivel.\n\n"
        f"Texto actual:\n\n{current_content}"
    )

def display_result(current_content: str, iteration: int) -> None:
    console.print("\n")
    console.print(Panel(
        Markdown(current_content), 
        title=f"Estado del Sistema · Iteración {iteration}", 
        border_style="magenta",
        padding=(1, 2)
    ))

async def evaluate_content(provider: LLMProvider, current_content: str) -> int:
    with console.status(f"[cyan]Árbitro Soberano ([bold]{provider.model_name}[/bold] @ temp 0.0) evaluando densidad (0-130)...[/cyan]", spinner="bouncingBar"):
        score_str = await provider.complete(
            prompt=f"Evalúa rigurosamente este bloque:\n\n{current_content}",
            system=JUDGE_PROMPT,
            temperature=0.0
        )
    try:
        return int(score_str.strip())
    except ValueError:
        import re
        match = re.search(r'\d+', score_str)
        return int(match.group()) if match else 0

def display_score(score: int) -> None:
    color = "green" if score >= 130 else "yellow" if score >= 100 else "red"
    console.print(f"⚖️  [bold]Veredicto del Árbitro:[/bold] [{color}]{score}/130[/{color}]\n")

def get_user_input() -> str:
    console.print("[bold yellow]Inyección de vector manual (opcional):[/bold yellow]")
    console.print("[dim]- (Enter / y) → Auto-Evolucionar (El sistema intentará cruzar la barrera de 130)[/dim]")
    console.print("[dim]- (Texto) → Redirigir el ángulo de mejora.[/dim]")
    console.print("[dim]- (n / no) → Forzar detención (Aceptar imperfección).[/dim]")
    return Prompt.ask("\n[bold cyan]DIRECTIVA:[/bold cyan]", default="").strip()

def copy_to_clipboard(current_content: str) -> None:
    plat = sys.platform
    if plat == 'darwin':
        import subprocess
        try:
            process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
            process.communicate(current_content.encode('utf-8'))
            console.print("[dim]El estado final ha sido copiado al portapapeles. Listo para deploy.[/dim]")
        except Exception:
            pass
    elif plat == 'win32':
        import subprocess
        try:
            subprocess.run("clip", text=True, input=current_content, check=True)
            console.print("[dim]El estado final ha sido copiado al portapapeles. Listo para deploy.[/dim]")
        except Exception:
            pass
    elif plat == 'linux':
        import subprocess
        try:
            subprocess.run(['xclip', '-selection', 'clipboard'], input=current_content.encode('utf-8'), check=True)
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
