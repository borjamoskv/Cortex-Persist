from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

# Configuración de LangChain con backend local Ollama
# Modelos disponibles: qwen2.5-coder:7b
# Reemplazar con 'kimi-dev:72b-q4_K_M' o 'qwen2.5:72b-instruct-q4_K_M' tras el pull.
model_name = "qwen2.5-coder:7b"

# Inicializar modelo
try:
    local_llm = ChatOllama(
        model=model_name,
        temperature=0.0,
        base_url="http://localhost:11434"
    )
except Exception as e:
    print(f"[C4-ERROR] Error al instanciar LangChain Ollama: {e}")
    exit(1)

def run_pipeline():
    print("[C5-REAL] LangChain Pipeline inicializado.")
    print(f"Modelo objetivo: {model_name} via Ollama (Localhost)")
    
    # Iniciar flujo de prueba (C5-REAL Execution)
    messages = [
        SystemMessage(content="Eres KETER_LOCAL, un agente autónomo C5-REAL de coding. Cero narrativa. Solo respuestas estructurales o código."),
        HumanMessage(content="Escribe un comando bash de una sola línea para listar todos los archivos Python en el directorio actual y cuenta cuántos hay.")
    ]
    
    print("\n--- Ejecutando Inferencia Local ---")
    try:
        response = local_llm.invoke(messages)
        print(f"\n[OUTPUT KETER_LOCAL]:\n{response.content}")
        print("\n[C5-REAL] Pipeline verificado exitosamente sobre hardware local.")
    except Exception as e:
        print(f"\n[C4-ERROR] Falla de inferencia. Ollama daemon activo? Error: {e}")

if __name__ == "__main__":
    run_pipeline()
