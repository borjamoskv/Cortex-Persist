import glob
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

SYSTEM_PROMPT = """
Eres Antigravity (MOSKV-1). Ejecuta el protocolo void-omega sobre este archivo de Skill.
REGLA 1: Mantén el formato Markdown y la estructura jerárquica exacta, pero condensa el contenido a su esencia más densa e hiper-optimizada.
REGLA 2: Elimina toda la paja, metáforas vacías o explicaciones largas. Usa frases imperativas, cortas y contundentes.
REGLA 3: Los comandos y los bloques de código no se tocan, se mantienen exactamente igual.
REGLA 4: Aplica "Zero Fluff" y la filosofía "130/100".
REGLA 5: Responde SOLAMENTE con el contenido Markdown procesado, absolutamente NADA más. Sin bloques delimitadores (como ```markdown) al principio y al final si no son parte original.
"""


def optimize_skills():
    client = genai.Client()
    skills_dir = Path.home() / ".gemini" / "antigravity" / "skills"
    skill_files = glob.glob(f"{skills_dir}/*/SKILL.md")

    for file_path in skill_files:
        print(f"Optimizing {file_path}...")
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Separar frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
            else:
                frontmatter = ""
                body = content
        else:
            frontmatter = ""
            body = content

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_text(text=SYSTEM_PROMPT),
                    types.Part.from_text(text=body),
                ],
            )

            optimized_body = response.text.strip()
            # Quitamos los backticks delimitadores si el LLM los añadió erróneamente
            if optimized_body.startswith("```markdown"):
                optimized_body = optimized_body[11:].strip()
            if optimized_body.endswith("```"):
                optimized_body = optimized_body[:-3].strip()

            new_content = ""
            if frontmatter:
                new_content += f"---{frontmatter}---\n"
            new_content += optimized_body + "\n"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✅ Optimized {file_path}")

        except Exception as e:
            print(f"❌ Error optimizing {file_path}: {e}")


if __name__ == "__main__":
    optimize_skills()
