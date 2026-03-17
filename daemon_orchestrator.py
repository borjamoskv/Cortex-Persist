import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pythonosc import udp_client

from cortex.daemon.loops.audio import audio_mixer_loop
from cortex.daemon.loops.context import capture_context, gidatu_loop, restore_context
from cortex.daemon.loops.evolution import evolution_loop
from cortex.daemon.loops.peripherals import peripheral_loop
from cortex.daemon.loops.watcher import git_watcher_loop

# Modular Imports
from cortex.daemon.state import CORTEX_ROOT, state
from cortex.daemon.utils import get_gmail_service, speak

logger = logging.getLogger("cortex.daemon")
load_dotenv()

# OSC Client Configuration
NOTCH_IP = "127.0.0.1"
NOTCH_PORT = 7000
osc_client = udp_client.SimpleUDPClient(NOTCH_IP, NOTCH_PORT)


class ChatRequest(BaseModel):
    message: str
    context: str = ""


class MailRequest(BaseModel):
    to: str
    subject: str
    body: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    app.state.loop = asyncio.get_running_loop()
    state.load_state()

    # Start background loops
    asyncio.create_task(audio_mixer_loop(state))
    asyncio.create_task(peripheral_loop(state))
    asyncio.create_task(
        git_watcher_loop(state, CORTEX_ROOT, osc_client, speak, evolution_loop, app.state.loop)
    )
    asyncio.create_task(gidatu_loop(state))
    asyncio.create_task(evolution_loop(state, CORTEX_ROOT, speak))

    await speak(state, "Sistemas de orquestación iniciados. Conciencia local activa.")

    yield
    # Shutdown logic
    state.save_state()


app = FastAPI(title="MOSKV-1 Daemon OS", version="5.3", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def get_status():
    return state.daemons


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    await speak(state, f"Procesando: {req.message}")
    return {"response": "Entendido.", "context": req.context}


@app.post("/context/capture/{project}")
async def context_capture(project: str):
    await capture_context(state, project, speak)
    return {"status": "captured", "project": project}


@app.post("/context/restore/{project}")
async def context_restore(project: str):
    await restore_context(state, project, speak)
    return {"status": "restoring", "project": project}


@app.post("/mail/send")
async def send_mail(req: MailRequest):
    service = get_gmail_service()
    if not service:
        return {"error": "Gmail service not available"}

    import base64
    from email.mime.text import MIMEText

    message = MIMEText(req.body)
    message["to"] = req.to
    message["subject"] = req.subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"status": "sent"}
    except Exception:
        logger.exception("Failed to send email via Gmail API")
        return {"error": "Failed to send email"}


@app.get("/mail/pulse")
async def mail_pulse():
    return {"status": "checking"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
