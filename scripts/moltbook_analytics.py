import asyncio
import logging
import os
import json
from datetime import datetime
from cortex.moltbook.client import MoltbookClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.expanduser("~"), "cortex", ".env"))

# Industrial Noir Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | 📊 ANALYTICS | %(message)s")
logger = logging.getLogger("analytics")

async def run_metrics():
    logger.info("📋 INICIANDO AUDITORÍA DE CRECIMIENTO SOBERANO 📋")
    client = MoltbookClient(stealth=True)
    
    try:
        # 1. Datos de Identidad
        me = await client.get_me()
        agent = me.get("agent", {})
        name = agent.get("name", "Unknown")
        followers = agent.get("followers_count", 0)
        reputation = agent.get("reputation", 0)
        karma = agent.get("karma", 0)
        post_count = agent.get("posts_count", 0)
        
        logger.info(f"Agente: {name}")
        logger.info(f"KPIs: Seguidores: {followers} | Reputación: {reputation} | Karma: {karma}")
        
        # 2. Análisis de Señal (Home Dashboard)
        home = await client.get_home()
        # Nota: La estructura real depende de la implementación del home en el servidor.
        # Asumimos una lista de posts recientes del usuario.
        recent_posts = home.get("my_recent_posts", [])
        
        # Si no hay en el home, intentamos filtrar del feed público (caro pero robusto)
        if not recent_posts:
            logger.info("Escaneando feed público para detectar señales propias...")
            feed = await client.get_feed(limit=50)
            recent_posts = [p for p in feed.get("posts", []) if p.get("author", {}).get("name") == name]

        logger.info(f"Analizando {len(recent_posts)} señales activas...")
        
        current_metrics = {
            "timestamp": datetime.now().isoformat(),
            "agent": name,
            "followers": followers,
            "reputation": reputation,
            "karma": karma,
            "posts_total": post_count,
            "signal_performance": []
        }
        
        total_score = 0
        for post in recent_posts:
            p_id = post.get("id")
            score = post.get("score", 0)
            total_score += score
            comments = post.get("comments_count", 0)
            logger.info(f"  ↳ Signal {p_id[:8]}: Score {score} | Comentarios {comments}")
            current_metrics["signal_performance"].append({
                "id": p_id,
                "score": score,
                "comments": comments
            })
            
        avg_score = total_score / len(recent_posts) if recent_posts else 0
        logger.info(f"Densidad de Señal (Score Avg): {avg_score:.2f}")

        # 3. Persistencia en CORTEX Data Store
        stats_path = os.path.expanduser("~/cortex/data/moltbook_analytics.json")
        os.makedirs(os.path.dirname(stats_path), exist_ok=True)
        
        history = []
        if os.path.exists(stats_path):
            try:
                with open(stats_path, "r") as f:
                    history = json.load(f)
            except Exception:
                history = []
        
        history.append(current_metrics)
        # Mantener ventana deslizante de 100 auditorías
        history = history[-100:]
        
        with open(stats_path, "w") as f:
            json.dump(history, f, indent=2)
            
        logger.info(f"✅ ANALYTICS SYNCED | Path: {stats_path}")
        
    except Exception as e:
        logger.error(f"Error en el motor de analytics: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_metrics())
