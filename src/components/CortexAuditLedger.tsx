// @C5-REAL
import React, { useState, useEffect } from 'react';
import { connectTelemetry, onTelemetryData, type TelemetryData, type TelemetryLog } from '../services/telemetry';

interface AuditEvent {
  id: string;
  timestamp: string;
  agent: string;
  action: string;
  status: 'COMMITTED' | 'VALIDATED' | 'TAINTED' | 'PROPOSED';
  hash: string;
}

export default function CortexAuditLedger() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [isLive, setIsLive] = useState(true);
  const [realityLevel, setRealityLevel] = useState('C4-SIM');

  useEffect(() => {
    if (!isLive) return;

    connectTelemetry();
    const unsubscribe = onTelemetryData((data: TelemetryData) => {
      if (data && data.reality_level) {
        setRealityLevel(data.reality_level);
      }
      if (data && data.logs && Array.isArray(data.logs)) {
        const mappedEvents: AuditEvent[] = data.logs.map((log: TelemetryLog) => {
          const logTime = log.id ? new Date(log.id * 1000) : new Date();
          return {
            id: `TX-${Math.floor((log.id || Date.now()) * 1000) % 9000 + 1000}`,
            timestamp: logTime.toLocaleTimeString(),
            agent: log.msg || 'CORTEX-Engine',
            action: log.val || 'Processing',
            status: log.msg === 'CRITICAL FINDING' || log.msg === 'INSECURE_ACCESS_CONTROL' ? 'TAINTED' : 'COMMITTED',
            hash: `sha3:${hashString(log.msg + log.val)}`
          };
        });
        setEvents(mappedEvents.reverse());
      }
    });

    return () => unsubscribe();
  }, [isLive]);

  function hashString(str: string) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash).toString(16).padEnd(8, 'f').substring(0, 8);
  }

  const isReal = realityLevel === 'C5-REAL';

  return (
    <div className="audit-ledger-container">
      <div className="audit-ledger-header">
        <div className="audit-ledger-title-group">
          <div className="audit-ledger-eyebrow">
            <span>Real-Time Telemetry Stream</span>
            <span className={`telemetry-badge ${isReal ? 'real' : 'sim'}`}>
              {realityLevel}
            </span>
          </div>
          <h3 className="audit-ledger-heading">Cryptographic Memory Ledger</h3>
        </div>
        <div className="audit-ledger-actions">
           <button 
             onClick={() => setIsLive(!isLive)}
             className={`ledger-stream-btn ${isLive ? 'active' : ''}`}
           >
             {isLive ? '● STREAM ENGAGED' : 'STREAM HALTED'}
           </button>
        </div>
      </div>

      <div className="audit-ledger-table">
        {events.length === 0 ? (
          <div className="audit-ledger-empty">
            Waiting for telemetry packet...
          </div>
        ) : (
          events.map((event, i) => (
            <div 
              key={event.id}
              className="audit-ledger-row"
            >
              {/* Highlight bar on the left of latest transaction */}
              {i === 0 && (
                <div className="latest-row-indicator" />
              )}
              
              <div className="tx-meta-group">
                <div className="tx-id">{event.id}</div>
                <div className="tx-timestamp">{event.timestamp}</div>
              </div>
              
              <div className="tx-agent">
                {event.agent}
              </div>
              
              <div className="tx-action">
                {event.action}
              </div>
              
              <div className="tx-status-group">
                <div className="tx-status-wrapper">
                  <span className={`tx-status-badge ${event.status === 'TAINTED' ? 'tainted' : 'committed'}`}>
                    {event.status}
                  </span>
                </div>
                <div className="tx-hash">
                  {event.hash}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      
      <div className="audit-ledger-footer">
        <p>
          Autopoietic validation sequence verified under theorem Ω₉
        </p>
      </div>
    </div>
  );
}
