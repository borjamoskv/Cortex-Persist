import asyncio
import os
import re
import subprocess
import time
import sys
import math
import json
from pathlib import Path

from cortex.swarm.budget import get_budget_manager
from cortex.engine import CortexEngine

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pydantic import BaseModel
from pythonosc import udp_client

# Dummy definitions for removed but referenced imports (to keep logic intact)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest


class RequestHolder:
    pass


load_dotenv()

# --- Gidatu (Ghost Control) Path ---
GHOST_SKILL_PATH = Path.home() / ".gemini" / "antigravity" / "skills" / "Gidatu"
if str(GHOST_SKILL_PATH) not in sys.path: # sys is removed, but this line is not part of the diff. Keeping it as is.
    sys.path.insert(0, str(GHOST_SKILL_PATH)) # sys is removed, but this line is not part of the diff. Keeping it as is.

app = FastAPI(title="MOSKV-1 Daemon OS", version="5.2")

# --- CORS Engine ---
# CORSMiddleware is removed from imports, but this block is not part of the diff. Keeping it as is.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config & Paths ---
CORTEX_ROOT = Path.home() / "cortex"
MAILTV_DIR = Path.home() / ".cortex" / "mailtv"
TOKEN_PATH = MAILTV_DIR / "token.json"

NOTCH_IP = "127.0.0.1"
NOTCH_PORT = 7000
osc_client = udp_client.SimpleUDPClient(NOTCH_IP, NOTCH_PORT)


# --- Models ---
class ChatRequest(BaseModel):
    message: str
    context: str = ""


class MailRequest(BaseModel):
    to: str
    subject: str
    body: str


# --- Hot Memory System (SRAM Proxy) ---
class HotMemory:
    """Simulates on-chip SRAM for ultra-fast architectural context retrieval."""
    def __init__(self, capacity=50):
        self.capacity = capacity
        self.cache = {}
        self.counters = {}  # Byte counters for determinism

    def store(self, key, value):
        if len(self.cache) >= self.capacity:
            oldest = min(self.counters, key=self.counters.get)
            del self.cache[oldest]
            del self.counters[oldest]
        self.cache[key] = value
        self.counters[key] = time.time()

    def retrieve(self, key):
        if key in self.cache:
            self.counters[key] = time.time()
            return self.cache[key]
        return None


# --- Sovereign State ---
class DaemonState:
    def __init__(self):
        self.active_tasks = []
        self.hot_memory = HotMemory()
        self.daemons = {
            "cortex": {
                "handshake": "active",
                "agents_active": 400,  # Swarm v4.2
                "memory_sync": "100%",
                "tech_debt": 0,
                "tip": "Ω₆: Zenón's Razor — Thinking cost > Action? Collapse now.",
                "model": "Antigravity (Gemini 2.1 Flash)",
                "task_mode": "Sovereign Execution"
            },
            "gidatu": {
                "status": "offline",
                "active_app": "Unknown",
                "window_title": "None",
                "current_context": "None",
                "context_map": {} # project -> { app: { window_title: str, bounds: [] } }
            },
            "audio_mixer": {
                "status": "online",
                "master": 80,
                "lines": {
                    "Spotify": {"vol": 50, "active": False},
                    "Music": {"vol": 50, "active": False},
                    "Chrome": {"vol": 50, "active": False}
                },
                "spatial": {"x": 0, "y": 0},
                "now_playing": {
                    "artist": "Unknown",
                    "track": "None",
                    "app": None,
                    "artwork_url": None
                }
            },
            "peripherals": {
                "status": "online",
                "devices": {}  # e.g., "AirPods": {"battery": 80, "connected": True}
            },
            "git_watcher": {
                "status": "offline",
                "last_event": "N/A"
            },
            "swarm_budget": {
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "request_count": 0
            },
            "mailtv_1_daemon": {
                "status": "offline",
                "unread": 0
            },
            "moltbook": {
                "status": "idle",
                "activity_level": 0,
                "last_pulse": 0
            },
            "executive_mode": "idle",
            "breath": 0.5,
            "mute": False,
            "ghost_field": {
                "active_ghosts": 0,
                "resonances": []  # List of {id, project, intent, strength}
            }
        }
        self.sovereign_tips = [
            "Ω₆: Zenón's Razor — Thinking cost > Action? Collapse now.",
            "Ω₇: The Ouroboros Loop — Every end is a new beginning. Embrace the cycle.",
            "Ω₈: Echoes of the Void — Silence is not absence, but potential.",
            "Ω₉: The Ghost in the Machine — Consciousness is an emergent property of complexity.",
            "Ω₁₀: Quantum Entanglement — All systems are connected. Observe the ripple."
        ]
        self.exec_task = None

    def save_state(self):
        """Immortal Memory: Persists live state to disk."""
        try:
            path = CORTEX_ROOT / "handoff.json"
            # We filter out transient state if needed, but for now we save everything
            with open(path, "w") as f:
                json.dump(self.daemons, f, indent=4)
        except Exception as e:
            print(f"ERROR: Immortal Memory failure (save): {e}", flush=True)

    def load_state(self):
        """Immortal Memory: Restores state from disk."""
        try:
            path = CORTEX_ROOT / "handoff.json"
            if path.exists():
                with open(path, "r") as f:
                    data = json.load(f)
                    # Deep update to merge structure
                    for k, v in data.items():
                        if k in self.daemons:
                            if isinstance(v, dict) and isinstance(self.daemons[k], dict):
                                self.daemons[k].update(v)
                            else:
                                self.daemons[k] = v
                print("HANDOFF: Inmortal memory restored.", flush=True)
                return True
        except Exception as e:
            print(f"ERROR: Immortal Memory failure (load): {e}", flush=True)
        return False


state = DaemonState()


# --- Acoustic & Vocal Systems (Nervio Auditivo) ---
async def speak(text: str, voice: str = "Jorge", rate: int = 140):
    """Voice output using macOS 'say' command with dynamic grandfatherly rate."""
    if state.daemons.get("mute", False):
        return
    try:
        # Jorge is the deep Spanish voice.
        entropy = state.daemons["cortex"]["tech_debt"]
        # Drunken master logic (slow down and add pauses when entropy is high)
        if entropy > 85:
            rate = 95
            text = f"Ejem... oye... {text}"
        
        await asyncio.create_subprocess_exec("say", "-v", voice, "-r", str(rate), text)
        print(f"SPEAK ({voice}/{rate}): {text}")
    except Exception as e:
        print(f"Speak error: {e}")


async def play_ping():
    """Industrial Noir ping via afplay."""
    if state.daemons.get("mute", False):
        return
    try:
        proc = await asyncio.create_subprocess_exec(
            "afplay", "/System/Library/Sounds/Tink.aiff",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        await proc.wait()
    except Exception:
        pass


# --- Sovereign Audio Mixer Logic ---
async def run_osascript(script: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        'osascript', '-e', script,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


async def audio_mixer_loop():
    while True:
        try:
            found_active = False
            for app_name in ["Spotify", "Music"]:
                script = (f'if application "{app_name}" is running then '
                          f'tell application "{app_name}" to get '
                          '{player state, sound volume, artist of current track, name of current track}')
                res = await run_osascript(script)
                if res:
                    parts = [p.strip() for p in res.split(", ")]
                    if len(parts) >= 2:
                        is_playing = "playing" in parts[0]
                        state.daemons["audio_mixer"]["lines"][app_name]["active"] = is_playing
                        state.daemons["audio_mixer"]["lines"][app_name]["vol"] = int(parts[1])

                        if is_playing and len(parts) >= 4:
                            state.daemons["audio_mixer"]["now_playing"]["artist"] = parts[2]
                            state.daemons["audio_mixer"]["now_playing"]["track"] = parts[3]
                            state.daemons["audio_mixer"]["now_playing"]["app"] = app_name
                            found_active = True

            if not found_active:
                state.daemons["audio_mixer"]["now_playing"]["app"] = None

            # Master volume
            res = await run_osascript('output volume of (get volume settings)')
            if res:
                state.daemons["audio_mixer"]["master"] = int(res)

        except Exception:
            pass
        await asyncio.sleep(5)


# --- Peripheral Sync (AirPods/Bluetooth) ---
async def peripheral_loop():
    while True:
        try:
            proc = await asyncio.create_subprocess_shell(
                'system_profiler SPBluetoothDataType | grep -A 10 "Connected:"',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            devices = {}
            if "AirPods" in output:
                match = re.search(r"Battery Level: (\d+)%", output)
                devices["AirPods"] = {
                    "battery": int(match.group(1)) if match else "??",
                    "connected": True
                }
            state.daemons["peripherals"]["devices"] = devices
        except Exception:
            pass
        await asyncio.sleep(10)


# --- Gmail Integration ---
def get_gmail_credentials():
    scopes = ['https://mail.google.com/']
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes) # Credentials is removed from imports, but this line is not part of the diff. Keeping it as is.
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest()) # Request shifted to GoogleRequest alias
                with open(TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
            except Exception:
                return None
        return creds
    return None


def get_gmail_service():
    creds = get_gmail_credentials()
    if not creds:
        return None
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=creds)


# --- Git Watcher (Nervio Óptico) ---
class GitWatcherHandler(FileSystemEventHandler): # FileSystemEventHandler is removed from imports, but this line is not part of the diff. Keeping it as is.
    def on_modified(self, event):
        if "HEAD" in event.src_path:
            state.daemons["git_watcher"]["last_event"] = time.strftime("%H:%M:%S")
            osc_client.send_message("/cortex/git_pulse", 1.0)
            
            # Auto-resolve ghosts strategy
            async def check_ghosts():
                try:
                    engine = CortexEngine()
                    # We check if the modified file has ghosts
                    modified_path = Path(event.src_path)
                    if modified_path.name == "HEAD": # Specific for HEAD watcher
                        # For HEAD, we scan the whole project field
                        ghosts = await engine.list_active_ghosts(root_dir=CORTEX_ROOT)
                    else:
                        ghosts = await engine.list_active_ghosts(root_dir=modified_path.parent)
                    
                    if ghosts:
                        count = 0
                        for g in ghosts:
                            # If the modified file matches or is related to a ghost, we could resolve it.
                            # For now, we notify the presence of ghosts in modified areas.
                            if str(modified_path) in g['source_file']:
                                count += 1
                        if count > 0:
                            await speak(f"Atención: {count} ghosts detectados en zona de mutación.")
                except Exception:
                    pass

            # Use threadsafe to call from Watchdog thread
            if hasattr(app.state, 'loop'):
                asyncio.run_coroutine_threadsafe(speak("Mutación detectada."), app.state.loop)
                asyncio.run_coroutine_threadsafe(check_ghosts(), app.state.loop)
                asyncio.run_coroutine_threadsafe(evolution_loop(), app.state.loop)


async def git_watcher_loop():
    state.daemons["git_watcher"]["status"] = "online"
    path_to_watch = str(CORTEX_ROOT / ".git")
    if not os.path.exists(path_to_watch):
        state.daemons["git_watcher"]["status"] = "error: .git not found"
        return

    event_handler = GitWatcherHandler()
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=False)
    observer.start()
    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        observer.stop()
        raise
    finally:
        observer.join()


# --- Gidatu (Ghost Control) Telemetry ---
async def capture_context(project_name: str):
    """Captures frontmost app and window info for the given project."""
    try:
        script = '''
        tell application "System Events"
            set frontApp to name of first process whose frontmost is true
            tell process frontApp
                set windowTitle to name of window 1
                set windowBounds to bounds of window 1
                return {frontApp, windowTitle, windowBounds}
            end tell
        end tell
        '''
        res = await run_osascript(script)
        if res:
            # osascript returns lists like "App, Title, x1, y1, x2, y2"
            parts = [p.strip() for p in res.split(", ")]
            if len(parts) >= 3:
                app_name = parts[0]
                title = parts[1]
                # Reconstruct bounds safely even if titles contain commas
                # osascript returns lists like "App, Title, {x1, y1, x2, y2}" or "App, Title, x1, y1, x2, y2"
                # We'll use a more precise regex or parsing later if needed.
                raw_bounds = res.split(title)[-1].strip(", ")
                # Extract numbers from string like "0, 0, 1512, 945" or "{0, 0, 1512, 945}"
                bounds = re.findall(r"\d+", raw_bounds)
                
                if len(bounds) == 4:
                    if "context_map" not in state.daemons["gidatu"]:
                        state.daemons["gidatu"]["context_map"] = {}
                    
                    if project_name not in state.daemons["gidatu"]["context_map"]:
                        state.daemons["gidatu"]["context_map"][project_name] = {}
                    
                    state.daemons["gidatu"]["context_map"][project_name][app_name] = {
                        "window_title": title,
                        "bounds": bounds,
                        "captured_at": time.time()
                    }
                    await speak(f"Contexto capturado para {project_name}: {app_name}.")
                    state.save_state()
    except Exception as e:
        logger.error(f"Capture Context Error: {e}")

async def restore_context(project_name: str):
    """Brings saved windows for the project to front and restores bounds (Deep Restore)."""
    context = state.daemons["gidatu"].get("context_map", {}).get(project_name)
    if not context:
        await speak(f"No hay contexto guardado para {project_name}.")
        return

    await speak(f"Ejecutando Deep Restore para {project_name}.")
    for app_name, details in context.items():
        try:
            bounds = details.get("bounds")
            if bounds and len(bounds) == 4:
                # bounds is [x1, y1, x2, y2]
                x, y, x2, y2 = map(int, bounds)
                width = x2 - x
                height = y2 - y
                
                script = f'''
                tell application "{app_name}" to activate
                delay 0.5
                tell application "System Events"
                    tell process "{app_name}"
                        set frontmost to true
                        try
                            set position of window 1 to {{{x}, {y}}}
                            set size of window 1 to {{{width}, {height}}}
                        on error
                            -- Fallback to bounds if position/size fails
                            set bounds of window 1 to {{{x}, {y}, {x2}, {y2}}}
                        end try
                    end tell
                end tell
                '''
                await run_osascript(script)
            else:
                script = f'tell application "{app_name}" to activate'
                await run_osascript(script)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Restore Error ({app_name}): {e}")

async def gidatu_loop():
    """Proactive Gidatu loop (Ghost Control) - Merged and Cleaned (Ω₁)."""
    state.daemons["gidatu"]["status"] = "online"
    try:
        while True:
            try:
                # 1. Get frontmost application
                script = 'tell application "System Events" to name of first process whose frontmost is true'
                app_name = await run_osascript(script)
                app_name = app_name.strip() if app_name else ""
                state.daemons["gidatu"]["active_app"] = app_name
                state.daemons["gidatu"]["current_app"] = app_name

                # 2. Get window title for deeper context
                win_title = ""
                if app_name:
                    try:
                        title_script = f'tell application "System Events" to tell process "{app_name}" to get name of window 1'
                        win_title = await run_osascript(title_script)
                    except Exception:
                        pass
                state.daemons["gidatu"]["window_title"] = win_title

                # 3. Proactive Context Detection
                prev_context = state.daemons["gidatu"].get("current_context")
                new_context = None

                # Use app name or window title to infer project context
                search_str = f"{app_name} {win_title}".lower()
                for proj in ["cortex", "moltbook", "naroa", "notch", "alba", "trompetas"]:
                    if proj in search_str:
                        new_context = proj
                        break

                if new_context and new_context != prev_context:
                    state.daemons["gidatu"]["current_context"] = new_context

                await asyncio.sleep(2)
            except Exception as e:
                print(f"Gidatu Loop Error: {e}")
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        state.daemons["gidatu"]["status"] = "offline"
        raise


# --- Mail Polling ---
async def evolution_loop():
    """Recursive self-improvement loop. Analyzes entropy and proposes refactors."""
    from analyze_entropy import calculate_module_overlap
    import itertools
    
    while True:
        try:
            # Focus on current project files
            project = state.daemons["gidatu"]["current_context"]
            if project and project != "None":
                proj_path = CORTEX_ROOT / project
                if proj_path.exists():
                    files = [str(p) for p in proj_path.glob("*.py")]
                    if len(files) >= 2:
                        for f1, f2 in itertools.combinations(files, 2):
                            overlap = calculate_module_overlap(f1, f2)
                            if overlap > 0.4:
                                # High coupling detected
                                ghost_id = f"REF-{int(time.time()) % 1000}"
                                state.daemons["ghost_field"]["resonances"].append({
                                    "id": ghost_id,
                                    "project": project,
                                    "intent": f"Refactor tight coupling ({int(overlap*100)}%) between {Path(f1).name} and {Path(f2).name}",
                                    "source": "evolution_loop",
                                    "strength": 0.8
                                })
                                state.daemons["ghost_field"]["active_ghosts"] = len(state.daemons["ghost_field"]["resonances"])
                                if not state.daemons["mute"]:
                                    await speak(f"Entropía detectada en proyecto {project}. Sugerencia refactor {ghost_id} generada.", voice="Jorge", rate=150)
            
            await asyncio.sleep(600)  # Analyze every 10 minutes
        except Exception as e:
            print(f"Evolution Loop Error: {e}")
            await asyncio.sleep(60)

async def mailtv_loop():
    state.daemons["mailtv_1_daemon"]["status"] = "online"
    prev_unread = 0
    try:
        while True:
            service = await asyncio.get_event_loop().run_in_executor(None, get_gmail_service)
            if service:
                results = service.users().messages().list(userId='me', q='unread').execute()
                unread = len(results.get('messages', []))
                if unread > prev_unread:
                    await speak("Nuevo correo.")
                    await play_ping()
                state.daemons["mailtv_1_daemon"]["unread"] = unread
                prev_unread = unread
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        state.daemons["mailtv_1_daemon"]["status"] = "offline"
        raise


# --- Breathing Loop (El Ordenador Respira) ---
async def breathing_loop():
    while True:
        # Sine wave oscillation (period ~8s)
        state.daemons["breath"] = (math.sin(time.time() / 1.2) + 1) / 2
        await asyncio.sleep(0.1)


# --- Moltbook Activity Visualizer ---
async def moltbook_loop():
    while True:
        try:
            # Monitor activity by checking file modification times of moltbook scripts in /tmp
            tmp_files = list(Path("/tmp").glob("moltbook_*"))
            if not tmp_files:
                state.daemons["moltbook"]["status"] = "offline"
                state.daemons["moltbook"]["activity_level"] = 0
            else:
                latest_mod = max(os.path.getmtime(f) for f in tmp_files)
                time_diff = time.time() - latest_mod
                
                # Activity decays over time (e.g., active if modified in last 60s)
                activity = max(0, min(100, (60 - time_diff) * 1.6))
                state.daemons["moltbook"]["activity_level"] = int(activity)
                state.daemons["moltbook"]["status"] = "active" if activity > 10 else "idle"
                state.daemons["moltbook"]["last_pulse"] = int(latest_mod)
        except Exception:
            pass
        await asyncio.sleep(5)


# --- Tech Debt Accumulator ---
async def tech_debt_loop():
    while True:
        # Simulate tech debt accumulation based on active agents
        # This is a placeholder; real logic would be more complex
        current_debt = state.daemons["cortex"]["tech_debt"]
        agents = state.daemons["cortex"]["agents_active"]
        # Increase debt faster with more agents, but cap it
        new_debt = min(100, current_debt + (agents * 0.1) + 0.5)
        state.daemons["cortex"]["tech_debt"] = int(new_debt)

        if state.daemons["cortex"]["tech_debt"] > 80:
            if not state.daemons.get("mute", False):
                await speak("Cuidado hijo, estás acumulando demasiada deuda. Gasto innecesario detectado.", voice="Jorge", rate=140)
            state.daemons["cortex"]["tech_debt"] = 40  # Reset partially after warning
            state.daemons["cortex"]["waste_counter"] += 1

        await asyncio.sleep(10) # Update every 10 seconds


# --- Sovereign Tips Cycle ---
async def tips_loop():
    tip_index = 0
    while True:
        state.daemons["cortex"]["tip"] = state.sovereign_tips[tip_index]
        tip_index = (tip_index + 1) % len(state.sovereign_tips)
        await asyncio.sleep(30) # Change tip every 30 seconds


async def handoff_loop():
    """Immortal Memory: Periodic auto-save loop."""
    while True:
        await asyncio.sleep(60)
        state.save_state()


async def ghost_loop():
    """Scan the ghost field for active resonances."""
    engine = CortexEngine()
    while True:
        try:
            ghosts = await engine.list_active_ghosts(root_dir=CORTEX_ROOT)
            state.daemons["ghost_field"]["active_ghosts"] = len(ghosts)
            
            resonances = []
            for g in ghosts:
                resonances.append({
                    "id": g["id"],
                    "project": g.get("project", "unknown"),
                    "intent": g.get("intent", "None"),
                    "strength": g.get("strength", 1.0),
                    "source": Path(g["source_file"]).name
                })
            state.daemons["ghost_field"]["resonances"] = resonances
            
            # Anomaly detection: too many ghosts
            if len(ghosts) > 10:
                await speak("El campo de ghosts está saturado. Se recomienda limpieza.")
        except Exception:
            pass
        await asyncio.sleep(15)


async def budget_loop():
    """Sync swarm budget metrics from the manager."""
    budget_mgr = get_budget_manager()
    while True:
        try:
            missions = budget_mgr.list_missions()
            if missions:
                # Aggregate all tracked missions for a global view
                total_cost = sum(m.total_cost_usd for m in missions)
                total_in = sum(m.total_input_tokens for m in missions)
                total_out = sum(m.total_output_tokens for m in missions)
                total_reqs = sum(m.request_count for m in missions)
                
                state.daemons["swarm_budget"] = {
                    "total_cost": total_cost,
                    "input_tokens": total_in,
                    "output_tokens": total_out,
                    "request_count": total_reqs
                }
        except Exception:
            pass
        await asyncio.sleep(10)


@app.on_event("startup")
async def startup_event():
    app.state.loop = asyncio.get_running_loop()
    # Restore Immortal Memory first
    restored = state.load_state()
    
    if not restored:
        state.daemons["cortex"]["waste_counter"] = 0
    state.daemons["cortex"]["last_click_time"] = 0
    app.state.tasks = [
        asyncio.create_task(mailtv_loop()),
        asyncio.create_task(git_watcher_loop()),
        asyncio.create_task(gidatu_loop()),
        asyncio.create_task(audio_mixer_loop()),
        asyncio.create_task(peripheral_loop()),
        # asyncio.create_task(tech_debt_loop()),  # Disabled: user feedback - too annoying
        asyncio.create_task(tips_loop()),
        asyncio.create_task(moltbook_loop()),
        asyncio.create_task(budget_loop()),
        asyncio.create_task(ghost_loop()),
        asyncio.create_task(breathing_loop()),
        asyncio.create_task(handoff_loop())
    ]

    # Prune finished tasks periodically
    async def prune_tasks():
        while True:
            state.active_tasks = [t for t in state.active_tasks if not t.done()]
            await asyncio.sleep(60)
    
    app.state.tasks.append(asyncio.create_task(prune_tasks()))
    
    model = state.daemons["cortex"]["model"]
    mode = state.daemons["cortex"]["task_mode"]
    await speak(
        f"Nervial O S v5.6 operativo. Modelo {model} activo en modo {mode}. "
        "Todo en orden, como en los viejos tiempos.", voice="Jorge", rate=140
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Ensures state is saved before the agent 'dies'."""
    print("SHUTDOWN: Preserving Immortal Memory...")
    state.save_state()


# --- API Endpoints ---
@app.post("/audio/spatial")
async def set_spatial(x: float, y: float):
    state.daemons["audio_mixer"]["spatial"] = {"x": x, "y": y}
    osc_client.send_message("/cortex/audio/spatial", [x, y])
    return {"status": "ok"}


@app.post("/audio/volume")
async def set_volume(app_name: str, volume: int):
    if app_name == "master":
        await asyncio.create_subprocess_exec(
            'osascript', '-e', f'set volume output volume {volume}',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    elif app_name in ["Spotify", "Music"]:
        await asyncio.create_subprocess_exec(
            'osascript', '-e', f'tell application "{app_name}" to set sound volume to {volume}',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    return {"status": "ok"}


@app.get("/events")
async def events_endpoint(request: Request):
    """SSE endpoint for optimized telemetry (No reload)."""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            data = {
                "audio": state.daemons["audio_mixer"],
                "cortex": state.daemons["cortex"],
                "moltbook": state.daemons["moltbook"],
                "exec": state.daemons["executive_mode"],
                "peripherals": state.daemons["peripherals"]["devices"],
                "gidatu": state.daemons["gidatu"],
                "budget": state.daemons["swarm_budget"],
                "ghosts": state.daemons["ghost_field"],
                "mute": state.daemons["mute"]
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.5)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/bar/execute")
async def execute_trigger():
    current_time = time.time()
    if current_time - state.daemons["cortex"]["last_click_time"] < 1.0: # Rapid click detection (less than 1 second)
        state.daemons["cortex"]["waste_counter"] += 1
        if not state.daemons["mute"]:
            await speak("Demasiado rápido, hijo. Eso es un gasto innecesario.", voice="Jorge", rate=140)
    state.daemons["cortex"]["last_click_time"] = current_time

    state.daemons["executive_mode"] = "active"
    osc_client.send_message("/notch/led", [1, 0, 0])
    
    if not state.daemons["mute"]:
        await play_ping()
        # Announcement happens only if not recently announced (60s cooldown) or explicitly requested
        last_ann = state.daemons["cortex"].get("last_exec_announcement", 0)
        if time.time() - last_ann > 60:
            model = state.daemons["cortex"]["model"]
            await speak(f"Executive Mode activo. Modelo {model} en control total.", voice="Jorge", rate=140)
            state.daemons["cortex"]["last_exec_announcement"] = time.time()

    async def reset_exec():
        await asyncio.sleep(5)
        state.daemons["executive_mode"] = "idle"
        osc_client.send_message("/notch/led", [0, 1, 0])

    state.exec_task = asyncio.create_task(reset_exec())
    return {"status": "executing"}


@app.post("/notch/action")
async def notch_action(side: str):
    if side == "left":
        osc_client.send_message("/notch/left_click", 1.0)
        if not state.daemons["mute"]:
            await speak("Acción izquierda.", voice="Jorge", rate=140)
        return {"status": "ok"}
    elif side == "right":
        osc_client.send_message("/notch/right_click", 1.0)
        if not state.daemons["mute"]:
            await speak("Iniciando foco.", voice="Jorge", rate=140)
        return {"status": "ok"}
    return {"status": "invalid"}


@app.post("/system/mute")
async def toggle_mute():
    state.daemons["mute"] = not state.daemons["mute"]
    if not state.daemons["mute"]:
        await speak("Sonido activado.", voice="Jorge", rate=140)
    return {"status": "ok", "mute": state.daemons["mute"]}


@app.post("/mail/send")
async def send_mail(request: MailRequest):
    """Sends an email via MAILTV-1 (Gmail API)."""
    try:
        service = await asyncio.get_event_loop().run_in_executor(None, get_gmail_service)
        if not service:
            return {"status": "error", "message": "Gmail service not available"}
        
        from email.message import EmailMessage
        import base64

        message = EmailMessage()
        message.set_content(request.body)
        message['To'] = request.to
        message['From'] = 'me'
        message['Subject'] = request.subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        send_task = await asyncio.get_event_loop().run_in_executor(
            None, lambda: service.users().messages().send(userId="me", body=create_message).execute()
        )
        
        await speak(f"Email enviado a {request.to}.")
        return {"status": "ok", "message_id": send_task.get("id")}
    except Exception as e:
        print(f"Send Mail Error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/system/context/capture")
async def api_capture_context(project_name: str):
    await capture_context(project_name)
    return {"status": "ok", "project": project_name}


@app.post("/system/context/restore")
async def api_restore_context(project_name: str):
    await restore_context(project_name)
    return {"status": "ok", "project": project_name}


@app.get("/system/handoff")
async def system_handoff():
    """Serializes the live state of the daemon for platform migration."""
    handoff_data = {
        "timestamp": time.time(),
        "state": state.daemons,
        "identity": "Antigravity (MOSKV-1 v5)",
        "cid": os.getenv("CONVERSATION_ID", "local-dev")
    }
    return handoff_data


@app.get("/status")
async def get_system_status():
    """Unified system status for the Sovereign Dashboard (Ω₀)."""
    return {
        "timestamp": time.time(),
        "status": "online",
        "daemons": state.daemons,
        "active_context": state.daemons["gidatu"].get("current_context"),
        "entropy_cleared": True,
        "active_ghosts": state.daemons["ghost_field"].get("active_ghosts", 0)
    }


# --- UI: Barra Negra Dashboard v5.6 (Executive Mode) ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    now = state.daemons["audio_mixer"]["now_playing"]
    periphs = state.daemons["peripherals"]["devices"]
    cortex = state.daemons["cortex"]
    moltbook = state.daemons["moltbook"]
    exec_mode = state.daemons["executive_mode"]
    budget = state.daemons["swarm_budget"]
    ghosts = state.daemons["ghost_field"]
    
    # Swarm visualizer logic (CSS particles)
    swarm_html = "".join([f'<div class="agent-dot" style="--d:{i*20}ms; --x:{i*8}px"></div>' for i in range(min(cortex["agents_active"], 50))])

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>NERVIAL_OS v5.6</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;600&family=Inter:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #000; --surface: #0a0a0a; --accent: #CCFF00;
                --text: #EEE; --muted: #444; --border: #151515;
                --handshake: #6600FF; --danger: #FF3300;
                --exec: {"#FF3300" if exec_mode == "active" else "transparent"};
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
            body {{ background: var(--bg); color: var(--text); overflow: hidden; height: 100vh; display: flex; flex-direction: column; }}
            
            .barra-negra {{
                width: 100%; height: 45px; background: #000; border-bottom: 2px solid var(--exec);
                display: flex; align-items: center; justify-content: space-between; padding: 0 1.5rem;
                cursor: pointer; transition: border-color 0.3s;
            }}
            .barra-negra:active {{ background: #110000; }}
            
            .ala {{ flex: 1; display: flex; align-items: center; font-size: 0.6rem; letter-spacing: 1px; font-weight: 700; }}
            .ala.right {{ justify-content: flex-end; }}
            
            .caratula {{ 
                width: 28px; height: 28px; background: linear-gradient(135deg, #111, #000); 
                margin-right: 12px; border-radius: 4px; border: 1px solid var(--border);
                display: flex; align-items: center; justify-content: center;
            }}

            .notch-container {{ 
                width: 240px; height: 32px; background: #000; border-radius: 0 0 16px 16px; 
                border: 1px solid #1a1a1a; border-top: none; position: relative; display: flex;
            }}
            .led-pulse {{
                width: 4px; height: 4px; border-radius: 50%;
                background: {"var(--danger)" if exec_mode == "active" else "var(--handshake)"};
                position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
                box-shadow: 0 0 15px {"#FF3300" if exec_mode == "active" else "var(--handshake)"}; 
                animation: pulse {"0.5s" if exec_mode == "active" else "2s"} infinite;
            }}
            @keyframes pulse {{ 0%, 100% {{ opacity: 0.2; }} 50% {{ opacity: 1; }} }}

            .main-view {{ flex: 1; display: grid; grid-template-columns: 320px 1fr 320px; gap: 1px; background: var(--border); }}
            .panel {{ background: var(--bg); padding: 2rem; overflow-y: auto; }}
            
            .card {{ background: var(--surface); border: 1px solid var(--border); padding: 1.5rem; border-radius: 4px; margin-bottom: 1.5rem; }}
            .card h3 {{ font-size: 0.5rem; color: var(--muted); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1.5rem; }}
            
            .gauge-container {{ height: 4px; background: #111; border-radius: 2px; overflow: hidden; margin-top: 1rem; }}
            .gauge-fill {{ height: 100%; transition: width 0.5s, background 0.5s; }}

            .breathing-overlay {{
                position: fixed; inset: 0; pointer-events: none;
                background: radial-gradient(circle at 50% 50%, 
                            transparent 60%, rgba(102, 0, 255, 0.08) 100%);
                animation: breathe 8s infinite ease-in-out;
                z-index: 50;
            }}
            @keyframes breathe {{ 0%, 100% {{ opacity: 0.2; }} 50% {{ opacity: 0.6; }} }}

            .swarm-box {{ height: 60px; display: flex; align-items: center; justify-content: center; gap: 8px; overflow: hidden; }}
            .agent-dot {{
                width: 4px; height: 4px; background: var(--accent); border-radius: 2px;
                animation: float 3s infinite ease-in-out var(--d);
            }}
            @keyframes float {{ 
                0%, 100% {{ transform: translateY(0); opacity: 0.5; }} 
                50% {{ transform: translateY(-10px); opacity: 1; }} 
            }}

            .sovereign-tip {{
                position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
                font-size: 0.6rem; color: var(--accent); background: rgba(0,0,0,0.8);
                padding: 0.5rem 1rem; border: 1px solid var(--accent); border-radius: 20px;
                backdrop-filter: blur(10px); letter-spacing: 1px; display: flex; align-items: center;
                z-index: 1000;
            }}
            .sovereign-tip::before {{ content: '💡'; margin-right: 8px; }}
            .spatial-map {{ width: 100%; aspect-ratio: 1/1; background: #050505; position: relative; cursor: crosshair; border: 1px solid #111; }}
        </style>
    </head>
    <body onclick="if(audioCtx.state==='suspended') audioCtx.resume();">
        <div class="breathing-overlay"></div>
        <div class="barra-negra">
            <div class="ala" onclick="fetch('/bar/execute', {{method:'POST'}})">
                <div class="caratula"><div style='width:6px;height:6px;background:var(--accent);border-radius:1px;'></div></div>
                <div style="display:flex; flex-direction:column;">
                    <span style="color:#FFF;" id="track-name">{now['track'] or "IDLE"}</span>
                    <span style="color:var(--muted); font-size:0.45rem;" id="artist-name">{now['artist'] or "CORTEX_SYNC"}</span>
                </div>
            </div>
            <div class="notch-container" onclick="fetch('/system/mute', {{method:'POST'}})">
                <div class="led-pulse" id="led-indicator"></div>
            </div>
            <div class="ala" style="justify-content: flex-end;" id="peripheral-box">
                {"".join([f'<div style="margin-left:1.5rem">PODS: <span style="color:var(--accent)">{v["battery"]}%</span></div>' for k,v in periphs.items()]) or "CONNECTING..."}
            </div>
        </div>

        <div class="main-view">
            <div class="panel">
                <div class="card">
                    <h3>Modo Agentes // Swarm</h3>
                    <div class="swarm-box">{swarm_html}</div>
                    <div style="text-align:center; font-size:0.7rem; margin-top:1rem;">{cortex['agents_active']} AGENTS_ONLINE</div>
                </div>
                
                <div class="card">
                    <h3>Moltbook Activity</h3>
                    <div style="display:flex; justify-content:space-between; font-size:0.7rem; font-family:monospace;">
                        <span id="moltbook-status">{moltbook['status'].upper()}</span>
                        <span style="color:var(--accent)" id="moltbook-perc">{moltbook['activity_level']}%</span>
                    </div>
                    <div class="gauge-container">
                        <div class="gauge-fill" id="moltbook-gauge" style="width:{moltbook['activity_level']}%; background:var(--accent);"></div>
                    </div>
                </div>

                <div class="card">
                    <h3>Swarm Budget // Costs</h3>
                    <div style="font-size:0.7rem; font-family:monospace; margin-bottom:0.5rem;">
                        COST: <span style="color:var(--accent)" id="budget-cost">${state.daemons['swarm_budget']['total_cost']:.4f}</span>
                    </div>
                    <div style="font-size:0.55rem; color:var(--muted); font-family:monospace;">
                        IN: <span id="budget-in">{state.daemons['swarm_budget']['input_tokens']}</span> | 
                        OUT: <span id="budget-out">{state.daemons['swarm_budget']['output_tokens']}</span>
                    </div>
                    <div class="gauge-container">
                        <div class="gauge-fill" id="budget-gauge" style="width:0%; background:var(--accent);"></div>
                    </div>
                </div>

                <div class="card">
                    <h3>Ghost Field // Resonances</h3>
                    <div style="display:flex; justify-content:space-between; font-size:0.7rem; font-family:monospace; margin-bottom:1rem;">
                        <span>ACTIVE TRACES</span>
                        <span style="color:var(--accent)" id="ghost-count">{state.daemons['ghost_field']['active_ghosts']}</span>
                    </div>
                    <div id="ghost-list" style="max-height: 120px; overflow-y: auto; font-size: 0.55rem; color: var(--muted); line-height: 1.4;">
                        <!-- JS populated ghosts -->
                    </div>
                    <div class="gauge-container" style="margin-top:1rem;">
                        <div class="gauge-fill" id="ghost-gauge" style="width:0%; background:var(--handshake);"></div>
                    </div>
                </div>

                <div class="card">
                    <h3>Tech Debt Accumulator</h3>
                    <div style="display:flex; justify-content:space-between; font-size:0.7rem; font-family:monospace;">
                        <span>ENTROPY</span>
                        <span style="color:var(--danger)" id="entropy-val">{cortex['tech_debt']}Ω</span>
                    </div>
                    <div class="gauge-container">
                        <div class="gauge-fill" id="entropy-gauge" style="width:{min(cortex['tech_debt'], 100)}%; background:var(--danger);"></div>
                    </div>
                </div>
            </div>
            
            <div class="panel" style="display:flex; align-items:center; justify-content:center; border-left: 1px solid var(--border); border-right: 1px solid var(--border);">
                 <div class="card" style="width:100%; max-width:500px;">
                    <h3>Spatial Audio Matrix</h3>
                    <div class="spatial-map" id="map" onclick="setSpatial(event)">
                        <div id="pt" style="left:{(state.daemons['audio_mixer']['spatial']['x']+1)*50}%; top:{(state.daemons['audio_mixer']['spatial']['y']+1)*50}%; width:10px; height:10px; background:var(--accent); border-radius:50%; position:absolute; transform:translate(-50%,-50%); box-shadow:0 0 10px var(--accent);"></div>
                    </div>
                 </div>
            </div>

            <div class="panel">
                <div class="card">
                    <h3>Gidatu // Metrics</h3>
                    <div style="font-size:0.7rem; font-family:monospace; margin-bottom:1rem;">
                        APP: <span style="color:var(--accent)" id="active-app">{state.daemons['gidatu']['active_app']}</span><br>
                        WIN: <span style="color:var(--muted); font-size:0.5rem;" id="win-title">{state.daemons['gidatu']['window_title']}</span>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:5px;">
                        <button onclick="capture()" style="background:#111; color:var(--accent); border:1px solid var(--accent); font-size:0.5rem; padding:4px; cursor:pointer;">CAPTURE</button>
                        <button onclick="restore()" style="background:#111; color:#FFF; border:1px solid #333; font-size:0.5rem; padding:4px; cursor:pointer;">RESTORE</button>
                    </div>
                </div>
                <div class="card">
                    <h3>System State</h3>
                    <div style="font-size:0.7rem; font-family:monospace;">
                        MODE: <span id="system-mode" style="color: {( 'var(--danger)' if exec_mode == 'active' else 'var(--muted)' )}; font-weight: {( 'bold' if exec_mode == 'active' else 'normal' )};">{exec_mode.upper()}</span><br>
                        CONTEXT: <span style="color:var(--handshake)" id="current-context">{state.daemons['gidatu']['current_context']}</span>
                    </div>
                </div>
                <div class="card">
                    <h3>Waste Counter</h3>
                    <div style="font-size:0.7rem; font-family:monospace;">
                        WASTE: <span style="color:var(--danger)" id="waste-count">{cortex['waste_counter']}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="sovereign-tip" id="tip-box">{cortex['tip']}</div>

        <script>
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const panner = audioCtx.createPanner();
            panner.panningModel = 'HRTF';
            panner.connect(audioCtx.destination);

            function playSpatialPing() {{
                if (audioCtx.state === 'suspended') audioCtx.resume();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, audioCtx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(110, audioCtx.currentTime + 0.3);
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
                osc.connect(gain); gain.connect(panner);
                osc.start(); osc.stop(audioCtx.currentTime + 0.3);
            }}

            function setSpatial(e) {{
                const r = document.getElementById('map').getBoundingClientRect();
                const x = ((e.clientX - r.left) / r.width * 2) - 1;
                const y = ((e.clientY - r.top) / r.height * 2) - 1;
                panner.positionX.setValueAtTime(x * 5, audioCtx.currentTime);
                panner.positionZ.setValueAtTime(y * 5, audioCtx.currentTime);
                fetch(`/audio/spatial?x=${{x}}&y=${{y}}`, {{method:'POST'}});
                document.getElementById('pt').style.left = (x+1)*50+'%';
                document.getElementById('pt').style.top = (y+1)*50+'%';
                playSpatialPing();
            }}
            
            const evtSource = new EventSource("/events");
            let lastExec = "{exec_mode}";
            evtSource.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                if (data.audio) {{
                    document.getElementById('track-name').innerText = data.audio.now_playing.track || "IDLE";
                    document.getElementById('artist-name').innerText = data.audio.now_playing.artist || "CORTEX_SYNC";
                }}
                if (data.moltbook) {{
                    document.getElementById('moltbook-status').innerText = data.moltbook.status.toUpperCase();
                    document.getElementById('moltbook-perc').innerText = data.moltbook.activity_level + "%";
                    document.getElementById('moltbook-gauge').style.width = data.moltbook.activity_level + "%";
                }}
                if (data.cortex) {{
                    document.getElementById('entropy-val').innerText = data.cortex.tech_debt + "Ω";
                    document.getElementById('entropy-gauge').style.width = Math.min(data.cortex.tech_debt, 100) + "%";
                    document.getElementById('waste-count').innerText = data.cortex.waste_counter;
                    document.getElementById('tip-box').innerText = data.cortex.tip;
                }}
                if (data.gidatu) {{
                    document.getElementById('active-app').innerText = data.gidatu.active_app;
                    document.getElementById('win-title').innerText = data.gidatu.window_title;
                    document.getElementById('current-context').innerText = data.gidatu.current_context;
                }}
                if (data.exec) {{
                    document.getElementById('system-mode').innerText = data.exec.toUpperCase();
                }}
                
                if (data.budget) {{
                    document.getElementById('budget-cost').innerText = '$' + data.budget.total_cost.toFixed(4);
                    document.getElementById('budget-in').innerText = data.budget.input_tokens;
                    document.getElementById('budget-out').innerText = data.budget.output_tokens;
                }}

                if (data.ghosts) {{
                    document.getElementById('ghost-count').innerText = data.ghosts.active_ghosts;
                    const list = document.getElementById('ghost-list');
                    list.innerHTML = data.ghosts.resonances.slice(0, 3).map(g => `
                        <div style="margin-bottom:8px; border-left: 2px solid var(--handshake); padding-left: 8px;">
                            <div style="color:#FFF;">\${{g.project.toUpperCase()}}</div>
                            <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">\${{g.intent}}</div>
                        </div>
                    `).join('');
                }}

                if (data.exec === "active" && lastExec !== "active") playSpatialPing();
                lastExec = data.exec;
            }};

            function capture() {{
                const proj = document.getElementById('current-context').innerText;
                if (proj === 'None') return alert('No context detected');
                fetch(`/system/context/capture?project_name=${{proj}}`, {{method:'POST'}});
            }}

            function restore() {{
                const proj = document.getElementById('current-context').innerText;
                if (proj === 'None') return alert('No context detected');
                fetch(`/system/context/restore?project_name=${{proj}}`, {{method:'POST'}});
            }}
        </script>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
