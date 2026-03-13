import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types

app = FastAPI(title="Lyria 3 Sovereign Bridge")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# API Key from environment
API_KEY = os.environ.get("GEMINI_API_KEY")

@app.get("/axioms")
async def get_axioms():
    """Fetch stored sonic axioms from CORTEX."""
    try:
        from cortex.engine import CortexEngine
        engine = CortexEngine()
        # Search for facts in the Lyria 3 Expansion project
        results = await engine.search(
            query="", # Empty query to get recent entries or filter by project
            limit=50
        )
        
        # Filter manually for project if engine doesn't support project-specific query directly in search()
        # Actually, query_mixin.py often takes many args. Let's assume basic retrieval first.
        axioms = []
        for fact in results:
            if fact.project == "Lyria 3 Expansion":
                axioms.append({
                    "id": fact.id,
                    "content": fact.content,
                    "created_at": fact.created_at,
                    "metadata": fact.meta
                })
        return {"axioms": axioms}
    except Exception as e:
        return {"error": str(e), "axioms": []}


@app.websocket("/ws/generate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    if not API_KEY:
        await websocket.send_json({"error": "GEMINI_API_KEY not configured in backend"})
        await websocket.close()
        return

    client = genai.Client(
        api_key=API_KEY,
        http_options={"api_version": "v1alpha"},
    )

    try:
        data = await websocket.receive_json()
        prompt_text = data.get("prompt", "atmospheric experimental music")
        prompt_secondary = data.get("prompt_secondary", "")
        morph_weight = float(data.get("weight", 0.0))
        
        async with client.aio.live.music.connect(model="lyria-realtime-exp") as session:
            weighted_prompts = [
                types.WeightedPrompt(text=prompt_text, weight=1.0 - morph_weight)
            ]
            
            if prompt_secondary:
                weighted_prompts.append(
                    types.WeightedPrompt(text=prompt_secondary, weight=morph_weight)
                )
            
            await session.set_weighted_prompts(prompts=weighted_prompts)
            await session.play()
            
            # Send a confirmation to frontend
            confirm_msg = {
                "status": "connected", 
                "primary": prompt_text,
                "secondary": prompt_secondary,
                "weight": morph_weight
            }
            await websocket.send_json(confirm_msg)

            async for msg in session.receive():
                if hasattr(msg, "server_content") and msg.server_content:
                    sc = msg.server_content
                    # Check for audio_chunks or direct audio
                    chunk_data = None
                    if hasattr(sc, "audio_chunks") and sc.audio_chunks:
                        chunk_data = b"".join([ch.data for ch in sc.audio_chunks if ch.data])
                    elif hasattr(sc, "audio") and sc.audio:
                        chunk_data = sc.audio
                    
                    if chunk_data:
                        # Stream raw PCM to frontend
                        await websocket.send_bytes(chunk_data)

    except WebSocketDisconnect:
        print("Frontend disconnected")
    except Exception as e:
        print(f"Error in Lyria bridge: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        # Persist to CORTEX if successful
        if 'prompt_text' in locals():
            try:
                from cortex.engine import CortexEngine
                engine = CortexEngine()
                axiom_content = f"Primary: {prompt_text}"
                if locals().get('prompt_secondary'):
                    axiom_content += f" | Secondary: {prompt_secondary} | Weight: {morph_weight}"
                
                await engine.store(
                    project="Lyria 3 Expansion",
                    content=f"Generated sonic axiom: {axiom_content}",
                    fact_type="axiom",
                    tags=["lyria-3", "audio-gen", "morphing", "sonic-axiom"],
                    confidence="C5"
                )
                print(f"CORTEX: Stored axiom: {axiom_content}")
            except Exception as ce:
                print(f"CORTEX Error: {ce}")
        
        try:
            await websocket.close()
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
