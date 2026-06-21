// @C5-REAL
/* ═══════════════════════════════════════════════════════════
   CORTEX-Persist — Telemetry Service
   ───────────────────────────────────────────────────────────
   SSE bridge to the CORTEX-X100 FastAPI engine.
   Reality level: C5-REAL with C4-SIM fallback simulation.
   ═══════════════════════════════════════════════════════════ */

export interface TelemetryLog {
  id: number;
  msg: string;
  val: string;
}

export interface TelemetryData {
  reality_level: string;
  is_running?: boolean;
  cycle_count?: number;
  global_yield?: number;
  active_agents_count?: number;
  agent_states?: number[];
  logs?: TelemetryLog[];
}

type TelemetryCallback = (data: TelemetryData) => void;

let sse: EventSource | null = null;
const API_URL = import.meta.env.PUBLIC_CORTEX_API_URL || 'http://localhost:8000';
const listeners = new Set<TelemetryCallback>();
let retryTimeout: ReturnType<typeof setTimeout> | null = null;
let simulationInterval: ReturnType<typeof setInterval> | null = null;
let isConnected = false;

// Mock data generator for C4-SIM fallback
let simCycleCount = 425980;
const mockLogs = [
  { msg: "CORE_RAYON_INIT", val: "Zero-Copy memory mapped" },
  { msg: "VSA_HYPERVECTOR", val: "Dimension D=1024 Phase space loaded" },
  { msg: "IMMUNE_MEMBRANE", val: "Axiom validation thresholds engaged" },
  { msg: "FUZZ_CRUCIBLE", val: "Slither-Sim configured for contract target" },
  { msg: "LEDGER_BOOT", val: "L3 cryptographic root verified" },
];

function generateMockTelemetry(): TelemetryData {
  simCycleCount += Math.floor(Math.random() * 5) + 1;
  
  if (Math.random() > 0.4) {
    const agents = ["ReentrancyHunter", "AuthBypassSimulator", "InvariantBreaker", "CORTEX-Guard", "AestheticOmega"];
    const actions = ["Confirming state isolation", "Computing Merkle proof", "Verifying phase similarity", "Assuring C5-REAL continuity", "Scanning entrypoint graph"];
    mockLogs.push({
      msg: agents[Math.floor(Math.random() * agents.length)],
      val: actions[Math.floor(Math.random() * actions.length)]
    });
    if (mockLogs.length > 30) mockLogs.shift();
  }

  return {
    reality_level: "C4-SIM",
    is_running: Math.random() > 0.2,
    cycle_count: simCycleCount,
    global_yield: 0.4 + Math.random() * 0.3,
    active_agents_count: 10000,
    agent_states: [], // Removed 10k allocation
    logs: mockLogs.map((log, idx) => ({
      id: (Date.now() - (mockLogs.length - idx) * 1000) / 1000,
      msg: log.msg,
      val: log.val
    }))
  };
}

function startSimulation(): void {
  if (simulationInterval) return;
  simulationInterval = setInterval(() => {
    if (!isConnected) {
      const mockData = generateMockTelemetry();
      listeners.forEach(cb => cb(mockData));
    }
  }, 1000);
}

function stopSimulation(): void {
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
  }
}

export function connectTelemetry(): void {
  if (sse) return;

  try {
    sse = new EventSource(`${API_URL}/stream`);
    
    sse.onopen = () => {
      isConnected = true;
      stopSimulation();
      console.log('[TELEMETRY] C5-REAL Connection established');
    };
    
    sse.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as TelemetryData;
        data.reality_level = "C5-REAL";
        listeners.forEach(cb => cb(data));
      } catch (e) {
        console.error('[TELEMETRY] Parse error:', e);
      }
    };

    sse.onerror = () => {
      isConnected = false;
      if (sse) {
        sse.close();
        sse = null;
      }
      startSimulation();
      _scheduleRetry();
    };
  } catch (e) {
    isConnected = false;
    startSimulation();
    _scheduleRetry();
  }
}

function _scheduleRetry(): void {
  if (retryTimeout) return;
  retryTimeout = setTimeout(() => {
    retryTimeout = null;
    connectTelemetry();
  }, 5000);
}

export function onTelemetryData(callback: TelemetryCallback): () => boolean {
  listeners.add(callback);
  if (!isConnected) {
    callback(generateMockTelemetry());
  }
  return () => listeners.delete(callback);
}
