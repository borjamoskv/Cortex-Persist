export interface ASTMutation {
  fact_id: number;
  content: string;
  meta: {
    oracle: string;
    file_target: string;
    mutations: string[];
    severity: string;
  };
}

export interface FiatTransaction {
  fact_id: number;
  content: string;
  meta: {
    amount: number;
    currency: string;
    counterparty: string;
    description: string;
    type: 'income' | 'expense';
  };
}

class OracleStream {
  public state = {
    mutationPulse: 0,
    lastFile: '',
    severity: '',
    timestamp: 0,
    totalMutations: 0,
    fiatPulse: 0,
    lastAmount: 0,
    lastCurrency: 'EUR',
    totalVolume: 0,
  };

  private astWs: WebSocket | null = null;
  private fiatWs: WebSocket | null = null;

  private astListeners: Set<(mutation: ASTMutation) => void> = new Set();
  private fiatListeners: Set<(tx: FiatTransaction) => void> = new Set();

  connect() {
    this.connectAST();
    this.connectFiat();
  }

  private connectAST() {
    if (this.astWs) return;
    // Connect to the local FastAPI telemetry endpoint
    const wsUrl = `ws://localhost:8484/telemetry/ast-oracle`;
    console.log(`👁️ Connecting to AST Oracle: ${wsUrl}`);
    
    this.astWs = new WebSocket(wsUrl);
    
    this.astWs.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === 'human_mutation') {
          const mut = payload.data as ASTMutation;
          console.log("AST Oracle Pulse:", mut);
          
          // Update the high-performance mutable state
          this.state.mutationPulse = 1.0; // Decay handled by WebGL
          this.state.lastFile = mut.meta.file_target.split('/').pop() || '';
          this.state.severity = mut.meta.severity;
          this.state.timestamp = performance.now();
          this.state.totalMutations++;

          // Notify UI listeners (for non-WebGL elements)
          this.astListeners.forEach(fn => fn(mut));
        }
      } catch (err) {
        console.error("Failed to parse AST stream", err);
      }
    };
    
    this.astWs.onclose = () => {
      console.log("AST Oracle disconnected. Reconnecting in 2s...");
      this.astWs = null;
      setTimeout(() => this.connectAST(), 2000);
    };
  }

  private connectFiat() {
    if (this.fiatWs) return;
    const wsUrl = `ws://localhost:8484/telemetry/fiat-stream`;
    console.log(`💰 Connecting to Fiat Stream: ${wsUrl}`);
    this.fiatWs = new WebSocket(wsUrl);

    this.fiatWs.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === 'fiat_transaction') {
          const tx = payload.data as FiatTransaction;
          console.log("💰 Fiat Oracle Pulse:", tx);
          
          this.state.fiatPulse = 1.0;
          this.state.lastAmount = tx.meta.amount;
          this.state.lastCurrency = tx.meta.currency;
          this.state.totalVolume += Math.abs(tx.meta.amount);
          this.state.timestamp = performance.now();

          this.fiatListeners.forEach(fn => fn(tx));
        }
      } catch (err) {
        console.error("Failed to parse Fiat stream", err);
      }
    };

    this.fiatWs.onclose = () => {
      console.log("Fiat Stream disconnected. Reconnecting in 5s...");
      this.fiatWs = null;
      setTimeout(() => this.connectFiat(), 5000);
    };
  }

  subscribeAST(callback: (mutation: ASTMutation) => void) {
    this.astListeners.add(callback);
    return () => this.astListeners.delete(callback);
  }

  subscribeFiat(callback: (tx: FiatTransaction) => void) {
    this.fiatListeners.add(callback);
    return () => this.fiatListeners.delete(callback);
  }
}

export const oracleStream = new OracleStream();
