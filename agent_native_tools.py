import subprocess
import json
import ollama

model_name = "qwen2.5-coder:7b"

def execute_bash(command: str) -> str:
    """
    Ejecuta un comando bash en el sistema local y devuelve la salida.
    
    Args:
        command: El comando bash a ejecutar.
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Error executing bash: {str(e)}"

# Mapeo de herramientas
available_tools = {
    'execute_bash': execute_bash
}

def run_native_agent():
    print("[C5-REAL] Inicializando Native Tool Agent (Ollama Client)")
    print(f"Modelo objetivo: {model_name} via Ollama")
    
    messages = [
        {"role": "user", "content": "Lista todos los archivos terminados en .py en este directorio y cuéntalos usando bash."}
    ]
    
    print("\n[INPUT]:", messages[0]["content"])
    
    # 1. Invocación inicial con tools
    response = ollama.chat(
        model=model_name,
        messages=messages,
        tools=[execute_bash]
    )
    
    messages.append(response['message'])
    
    # 2. Ver si el modelo decidió usar una herramienta
    if not response['message'].get('tool_calls'):
        print("\n[OUTPUT FINAL]:", response['message']['content'])
        return
        
    print("\n[TOOL CALL DETECTADO]")
    
    for tool_call in response['message']['tool_calls']:
        tool_name = tool_call['function']['name']
        arguments = tool_call['function']['arguments']
        
        print(f"-> Ejecutando: {tool_name}({arguments})")
        
        if tool_name in available_tools:
            output = available_tools[tool_name](**arguments)
            print(f"-> Resultado:\n{output}")
            
            # 3. Proveer el resultado de la herramienta de vuelta al modelo
            messages.append({
                'role': 'tool',
                'name': tool_name,
                'content': output
            })
            
    # 4. Respuesta final
    final_response = ollama.chat(
        model=model_name,
        messages=messages
    )
    
    print("\n[OUTPUT FINAL]:\n", final_response['message']['content'])
    print("\n[C5-REAL] Native Agent verificado exitosamente.")

if __name__ == "__main__":
    run_native_agent()
