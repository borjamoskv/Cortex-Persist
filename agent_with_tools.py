import subprocess
import re
import ollama

model_name = "qwen2.5-coder:7b"

REACT_PROMPT = """Eres KETER_LOCAL, un agente C5-REAL con capacidad de ejecutar herramientas.
Responde a la solicitud del usuario usando el siguiente formato:

Thought: Piensa paso a paso qué necesitas hacer.
Action: La herramienta a usar. Solo puede ser: [bash]
Action Input: El comando de entrada para la herramienta.
Observation: El resultado de la acción.
... (este ciclo Thought/Action/Action Input/Observation puede repetirse N veces)
Thought: Ya sé la respuesta final.
Final Answer: La respuesta final al usuario.

Para la herramienta `bash`, el input debe ser el comando a ejecutar. No uses markdown de código en el Action Input.

Solicitud del usuario: {input}
"""

def execute_bash(command: str) -> str:
    try:
        # Limpieza simple de comillas si el modelo las pone
        command = command.strip().strip('`').strip('"').strip("'")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}".strip()
    except Exception as e:
        return f"Error: {str(e)}"

def run_react_agent():
    print("[C5-REAL] Inicializando Custom ReAct Agent (Cero dependencias frágiles)")
    print(f"Modelo objetivo: {model_name} via Ollama")
    
    user_input = "Lista todos los archivos terminados en .py en este directorio y cuéntalos usando bash. Di el número exacto."
    messages = [{"role": "user", "content": REACT_PROMPT.format(input=user_input)}]
    
    print("\n[INPUT]:", user_input)
    
    for _ in range(5):  # Límite de 5 iteraciones
        response = ollama.chat(model=model_name, messages=messages, stream=False)
        content = response['message']['content']
        
        print("\n[AGENTE]:\n" + content)
        
        messages.append({"role": "assistant", "content": content})
        
        if "Final Answer:" in content:
            print("\n[C5-REAL] Flujo ReAct completado con éxito.")
            break
            
        # Parsear Action y Action Input
        action_match = re.search(r"Action:\s*(.*)", content)
        input_match = re.search(r"Action Input:\s*(.*)", content)
        
        if action_match and input_match:
            action = action_match.group(1).strip()
            action_input = input_match.group(1).strip()
            
            if action.lower() == "bash":
                print(f"-> [EJECUTANDO BASH]: {action_input}")
                observation = execute_bash(action_input)
                print(f"-> [OBSERVATION]:\n{observation}")
                
                messages.append({"role": "user", "content": f"Observation: {observation}"})
            else:
                messages.append({"role": "user", "content": f"Observation: Tool {action} no existe."})
        else:
            messages.append({"role": "user", "content": "Observation: Formato inválido. Usa 'Action:' y 'Action Input:'."})

if __name__ == "__main__":
    run_react_agent()
