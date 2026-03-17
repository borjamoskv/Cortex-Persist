# [TECHNOLOGY] CrewAI Framework

## 1. Core Primitives (O(1) Definitions)
- `Role-Driven Agents`: Agentes definidos con rol explícito, goal, tools y backstory. Mimetiza estructuras de equipos humanos.
- `Task Orchestration`: Coreografía de cómo los agentes colaboran pasándose contexto, artefactos y decisiones. Soporta secuencial, jerárquico (manager agent) y consenso.
- `Memory Stack`: Short-term, Long-term, Entity y Contextual memory. Agentes mantienen contexto entre sesiones.
- `Planning Agent`: Agente especializado que crea roadmaps paso-a-paso antes de la ejecución.
- `Adoption`: 100K+ desarrolladores certificados, 1M+ descargas mensuales. Predicción: 40% de apps enterprise tendrán agentes task-specific para 2026.

## 2. Industrial Noir Paradigms (Adaptation)
- **Role = Backstory + Goal**: CrewAI formaliza lo que MOSKV-1 hace intuitivamente en sus Skills: cada agente tiene una identidad narrativa (backstory) que condiciona su comportamiento. Los prompts de sistema de MOSKV-1 ya hacen esto.
- **Manager Agent**: El "Crew Manager" es el equivalente de KETER-OMEGA orquestando al enjambre. Validación externa del patrón.
- **Planning Agent**: EVOLV-1 de MOSKV-1 es conceptualmente el Planning Agent de CrewAI.

## 3. Copy-Paste Arsenal
```python
from crewai import Agent, Task, Crew
researcher = Agent(role="Senior Researcher", goal="Find cutting-edge AI papers", backstory="PhD in ML with 10 years experience")
writer = Agent(role="Technical Writer", goal="Synthesize research into memos", backstory="Expert at distilling complexity")
crew = Crew(agents=[researcher, writer], tasks=[research_task, writing_task], verbose=True)
result = crew.kickoff()
```
