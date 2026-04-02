import { useEffect, useState } from 'react';

// Definitions for the Ouroboros Exergy Protocol (Sovereign V6.0 - Binary Membrane)
export interface LedgerEntry {
  id: string;
  type: 'hit' | 'yield' | 'scan' | 'error' | 'remediation';
  amount?: number;
  timestamp: string;
  source: string;
  value?: string;
}

export interface SwarmStats {
  totalScanned: number;
  hitsFound: number;
  totalExergy: number;
  activeNodes: number;
  cycleCount: number;
  isHealing: boolean;
}

export function useOuroborosStream(
  sseUrl: string = 'http://localhost:8000/stream',
  wsUrl: string = 'ws://localhost:8000/ws'
) {
  const [stats, setStats] = useState<SwarmStats>({
    totalScanned: 0,
    hitsFound: 0,
    totalExergy: 0,
    activeNodes: 10000,
    cycleCount: 0,
    isHealing: false
  });

  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let socket: WebSocket | null = null;

    // 1. WebSocket: High-Frequency Binary Membrane (Axiom Ω₆)
    const connectWS = () => {
        socket = new WebSocket(wsUrl);
        socket.binaryType = 'arraybuffer';
        
        socket.onopen = () => console.log("🌐 Binary Membrane Active");
        
        socket.onmessage = (event) => {
            if (event.data instanceof ArrayBuffer) {
                // Dispatch raw buffer to WebGL - ZERO PARSE OVERHEAD
                window.dispatchEvent(new CustomEvent('ouroboros-binary-event', { 
                    detail: new Float32Array(event.data) 
                }));
            }
        };

        socket.onclose = () => {
            setTimeout(connectWS, 3000);
        };
    };

    // 2. SSE: Metadata & Lifecycle (Mica-Noir UI)
    try {
      eventSource = new EventSource(sseUrl);
      
      eventSource.onopen = () => {
        setIsConnected(true);
        connectWS();
      };

      eventSource.onmessage = (event) => {
        try {
          const state = JSON.parse(event.data);
          
          // Note: We no longer dispatch 'ouroboros-event' for agent_states here to save CPU
          
          const logs = state.logs || [];
          const isHealing = logs.some((l: any) => l.msg.includes('SURGEON') || l.msg.includes('HEALING') && !l.msg.includes('NEUTRALIZED'));

          setStats({
            totalScanned: state.cycle_count * 100,
            hitsFound: logs.filter((l: any) => l.msg.includes('FINDING')).length,
            totalExergy: state.global_yield || 0,
            activeNodes: 10000,
            cycleCount: state.cycle_count || 0,
            isHealing
          });

          if (logs.length > 0) {
            const mappedLedger: LedgerEntry[] = logs.map((l: any) => ({
              id: l.id.toString(),
              type: l.msg.includes('CRITICAL') ? 'hit' : l.msg.includes('SURGEON') ? 'remediation' : l.msg.includes('CYCLE') ? 'yield' : 'scan',
              amount: l.msg.includes('YIELD') ? 100.0 : 0, 
              timestamp: new Date(l.id * 1000).toISOString(),
              source: l.msg,
              value: l.val
            }));
            setLedger(mappedLedger.reverse().slice(0, 50));
          }
        } catch (e) {
          console.error("SSE Parse Error", e);
        }
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource?.close();
      };
    } catch (e) {
      console.error("Stream init failure", e);
    }

    return () => {
      if (eventSource) eventSource.close();
      if (socket) socket.close();
    };
  }, [sseUrl, wsUrl]);

  return { stats, ledger, isConnected };
}
