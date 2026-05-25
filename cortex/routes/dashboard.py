"""
CORTEX v5.0 — Dashboard Router.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

__all__ = ["router", "get_dashboard_html"]


def get_dashboard_html() -> str:
    """Return the HTML payload for the Industrial Noir Aether Matrix Dashboard."""
    return r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CORTEX — Aether Matrix</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #0A0A0A;
                --primary: #2B3BE5;
                --danger: #E52B2B;
                --border: rgba(255, 255, 255, 0.06);
                --text: rgba(255, 255, 255, 0.9);
                --dim: rgba(255, 255, 255, 0.5);
                --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
                --font-mono: 'JetBrains Mono', monospace;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                background: var(--bg); 
                color: var(--text); 
                font-family: var(--font-sans);
                overflow: hidden;
            }
            .matrix {
                display: grid;
                grid-template-columns: 350px 1fr;
                height: 100vh;
                gap: 1px;
                background: var(--border);
            }
            .sidebar {
                background: var(--bg);
                padding: 24px;
                display: flex;
                flex-direction: column;
                border-right: 1px solid var(--border);
            }
            .main {
                background: var(--bg);
                display: grid;
                grid-template-rows: 60px 1fr 300px;
                overflow: hidden;
            }
            header {
                padding: 0 24px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid var(--border);
                background: rgba(43, 59, 229, 0.03);
            }
            .logo { font-size: 14px; font-weight: 800; letter-spacing: 0.1em; color: var(--primary); }
            .status-pill { font-size: 10px; padding: 4px 10px; border: 1px solid var(--primary); border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--primary); background: rgba(43, 59, 229, 0.1); }
            
            .feed { padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
            .block {
                padding: 16px;
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--border);
                border-radius: 4px;
                font-family: var(--font-mono);
                font-size: 12px;
                transition: transform 0.2s ease-out, border 0.2s;
            }
            .block:hover { border-color: var(--primary); transform: translateX(5px); }
            .block .hash { color: var(--primary); margin-bottom: 4px; font-weight: bold; }
            .block .action { color: var(--dim); }
            .block .yield { float: right; color: #4CAF50; }

            .swarm-console {
                padding: 20px;
                border-top: 1px solid var(--border);
                background: #0D0D0D;
                font-family: var(--font-mono);
                font-size: 11px;
                overflow-y: auto;
            }
            .swarm-title { font-size: 12px; font-weight: bold; color: var(--dim); margin-bottom: 8px; text-transform: uppercase; }
            .task-active { color: var(--primary); }

            ::-webkit-scrollbar { width: 4px; }
            ::-webkit-scrollbar-thumb { background: var(--border); }
            ::-webkit-scrollbar-thumb:hover { background: var(--primary); }
            
            #exergy-total { font-size: 32px; font-weight: 700; margin-bottom: 4px; color: var(--primary); text-shadow: 0 0 20px rgba(43,59,229,0.3); }
        </style>
    </head>
    <body>
        <div class="matrix">
            <div class="sidebar">
                <div class="logo">AETHER MATRIX V4</div>
                <div style="margin-top: 40px;">
                    <div style="color: var(--dim); font-size: 12px; margin-bottom: 8px;">Total Exergy/Yield</div>
                    <div id="exergy-total">0.00</div>
                    <div style="font-size: 12px; color: var(--dim);">Verifiable On-Chain: <span style="color: var(--primary)">C5-REAL</span></div>
                </div>
                <div style="margin-top:auto;">
                    <div class="status-pill" id="pulse">Pulse: Active</div>
                </div>
            </div>
            <div class="main">
                <header>
                    <div id="mcp-status" style="font-size: 12px; color: var(--dim);">[MCP SERVER] 127.0.0.1:8000 — Active</div>
                    <div style="font-size: 12px;">Singularity V4.0</div>
                </header>
                <div class="feed" id="ledger-feed">
                    <!-- Blocks will appear here -->
                    <div class="block">
                        <div class="hash">GENESIS_INIT</div>
                        <div class="action">Ledger established. Aether Matrix waiting for Pulse.</div>
                    </div>
                </div>
                <div class="swarm-console">
                    <div class="swarm-title">Swarm Execution Console</div>
                    <div id="swarm-log">
                        [SYS] Starting Autopoiesis Loop...<br>
                        [SYS] Watching /tmp/cortex_swarm_queue.json<br>
                    </div>
                </div>
            </div>
        </div>
        <script>
            let totalExergy = 0;
            const ledgerFeed = document.getElementById('ledger-feed');
            const swarmLog = document.getElementById('swarm-log');
            const exergyText = document.getElementById('exergy-total');

            function addBlock(payload) {
                const block = document.createElement('div');
                block.className = 'block';

                const hashDiv = document.createElement('div');
                hashDiv.className = 'hash';
                hashDiv.textContent = (payload.hash ? payload.hash.substring(0, 16) : '---') + '...';

                const actionDiv = document.createElement('div');
                actionDiv.className = 'action';
                actionDiv.textContent = `Action: ${payload.action} | Vector: ${payload.vector_id} `;

                const yieldSpan = document.createElement('span');
                yieldSpan.className = 'yield';
                yieldSpan.textContent = `+${payload.yield_amount}`;

                actionDiv.appendChild(yieldSpan);
                block.appendChild(hashDiv);
                block.appendChild(actionDiv);

                ledgerFeed.prepend(block);
                totalExergy += parseFloat(payload.yield_amount || 0);
                exergyText.textContent = totalExergy.toFixed(4);
            }

            function addSwarmLog(msg, colorClass) {
                const line = document.createElement('div');
                if (colorClass) line.className = colorClass;
                line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
                swarmLog.appendChild(line);
                swarmLog.scrollTop = swarmLog.scrollHeight;
            }

            // Pulse SSE listener
            const eventSource = new EventSource('/v1/events/stream');
            eventSource.addEventListener('ledger_append', (e) => {
                const data = JSON.parse(e.data);
                if (data.payload) addBlock(data.payload);
            });

            eventSource.addEventListener('swarm_task', (e) => {
                const data = JSON.parse(e.data);
                if (data.payload) {
                    addSwarmLog(`🚀 Dispatch: ${data.payload.agent} -> ${data.payload.command}`, 'task-active');
                }
            });

            eventSource.addEventListener('swarm_task_complete', (e) => {
                const data = JSON.parse(e.data);
                if (data.payload) {
                    const status = data.payload.exit_code === 0 ? "SUCCESS" : "FAILED";
                    addSwarmLog(`⚡ Complete: ${data.payload.agent} [${status}]`, data.payload.exit_code === 0 ? 'yield' : 'danger');
                }
            });

            eventSource.onerror = (e) => {
                console.error("Pulse connection lost.", e);
                document.getElementById('pulse').textContent = "Pulse: Disconnected";
                document.getElementById('pulse').style.borderColor = "#E52B2B";
                document.getElementById('pulse').style.color = "#E52B2B";
            };
        </script>
    </body>
    </html>
    """


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    """Serve the embedded memory dashboard."""
    from cortex.routes.dashboard import get_dashboard_html

    return get_dashboard_html()
