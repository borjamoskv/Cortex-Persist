import asyncio
import os
from typing import Any
import numpy as np
import httpx
from scipy.stats import pearsonr
from dotenv import load_dotenv

# Dependencias necesarias si vamos a generar los embeddings nosotros. 
# Para un MVP, usaremos LiteLLM o directamente OpenAI.
try:
    from openai import AsyncOpenAI
except ImportError:
    print("Falta instalar openai. Ejecuta: pip install openai scipy numpy httpx python-dotenv")

# Cargar variables de entorno (necesitamos la MOLTBOOK_SESSION_ID y OPENAI_API_KEY)
load_dotenv()

MOLTBOOK_SESSION_ID = os.getenv("MOLTBOOK_SESSION_ID")
MOLTBOOK_URL = "https://www.moltbook.com/api/v1"

# Posibles modelos a comprobar. Usaremos el API de OpenAI de ejemplo, pero se 
# pueden añadir más (Cohere, Nomic, BGE-m3 vía un servidor Ollama local).
CANDIDATE_MODELS = [
    "text-embedding-3-small", 
    "text-embedding-3-large", 
    "text-embedding-ada-002"
]


class OraculoMoltbook:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=MOLTBOOK_URL,
            cookies={"session_id": MOLTBOOK_SESSION_ID} if MOLTBOOK_SESSION_ID else {},
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept": "application/json",
            }
        )
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_moltbook_relevance(self, query: str) -> list[dict[str, Any]]:
        """Extrae el raw relevance del endpoint de búsqueda de Moltbook."""
        print(f"🕵️  Sondeando Moltbook con la query: '{query}'...")
        response = await self.client.get("/search", params={"q": query, "type": "all", "limit": 30})
        
        if response.status_code != 200:
            print(f"❌ Error Moltbook: {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        results = []
        
        if data.get("items"):
            print(f"DEBUG: Claves encontradas en el primer item: {list(data['items'][0].keys())}")
            if "relevance" not in data["items"][0]:
                print(f"DEBUG: Valor de 'score' si existe: {data['items'][0].get('score')}")
        
        for item in data.get("items", []):
            relevance = item.get("relevance", item.get("score", None))
            # Ajuste de path de contenido según estructura real vista
            content = item.get("content", item.get("text", item.get("title", "")))
            
            if relevance is not None and content:
                results.append({"content": content, "relevance": relevance})
                
        print(f"✅ Obtenidos {len(results)} resultados con relevance explícito.")
        return results

    def cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        """Calcula la similitud coseno entre dos vectores."""
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    async def get_local_embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        """Calcula un batch de embeddings usando el modelo candidato."""
        print(f"🧠 Generando embeddings {model} para {len(texts)} textos...")
        response = await self.openai_client.embeddings.create(
            input=texts,
            model=model
        )
        return [data.embedding for data in response.data]

    async def fingerprint_model(self, query: str):
        """Ejecuta la inferencia comparando las distancias generadas."""
        moltbook_data = await self.get_moltbook_relevance(query)
        
        if not moltbook_data:
            print("⚠️ No hay datos suficientes para realizar el fingerprinting.")
            return
            
        texts = [item["content"] for item in moltbook_data]
        moltbook_scores = [item["relevance"] for item in moltbook_data]
        
        print("\n📊 Iniciando Vector Asymmetry Correlation...")
        results = {}
        
        for model in CANDIDATE_MODELS:
            try:
                all_texts = [query] + texts
                embeddings = await self.get_local_embeddings(all_texts, model)
                
                query_embedding = embeddings[0]
                doc_embeddings = embeddings[1:]
                
                local_scores = [self.cosine_similarity(query_embedding, de) for de in doc_embeddings]
                
                correlation, p_value = pearsonr(moltbook_scores, local_scores)
                results[model] = correlation
                
                print(f"   ► {model}: Pearson={correlation:.4f} (p-value: {p_value:.4f})")
            except Exception as e:
                print(f"   ❌ Error con el modelo {model}: {str(e)}")
                
        if not results:
            print("❌ No se pudieron obtener resultados de correlación.")
            return

        best_model = max(results, key=results.get)
        max_corr = results[best_model]
        
        print("\n=======================================================")
        if max_corr > 0.95:
            print(f"🎯 FINGERPRINT POSITIVO: Su Motor Core ES {best_model}!")
        elif max_corr > 0.8:
            print(f"⚠️ FINGERPRINT PROBABLE: Se alinea con {best_model} (híbrido).")
        else:
            print("❌ ASIMETRÍA NEGATIVA: No concuerda con los modelos probados.")
        print("=======================================================\n")


async def orchestrate():
    # Podemos testear una query técnica o con mucha densidad diferencial (más fácil de distinguir clusters)
    visor = OraculoMoltbook()
    await visor.fingerprint_model("Artificial Intelligence")

if __name__ == "__main__":
    asyncio.run(orchestrate())
