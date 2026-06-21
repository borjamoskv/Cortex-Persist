// @C5-REAL
import React, { useEffect, useState } from 'react';
import { connectTelemetry, onTelemetryData, type TelemetryData } from '../services/telemetry';

export default function TelemetryWidget() {
  const [data, setData] = useState({ 
    throughput: 0, 
    activeAgents: 0, 
    latency: 0,
    realityLevel: 'C4-SIM'
  });

  useEffect(() => {
    connectTelemetry();
    const unsubscribe = onTelemetryData((telemetry: TelemetryData) => {
      if (telemetry) {
        setData(prev => ({ 
          throughput: telemetry.cycle_count !== undefined ? telemetry.cycle_count : prev.throughput,
          activeAgents: telemetry.active_agents_count !== undefined 
            ? telemetry.active_agents_count 
            : (telemetry.agent_states ? telemetry.agent_states.length : 10000),
          latency: telemetry.global_yield !== undefined ? telemetry.global_yield : prev.latency,
          realityLevel: telemetry.reality_level || 'C4-SIM'
        }));
      }
    });
    return unsubscribe;
  }, []);

  const isReal = data.realityLevel === 'C5-REAL';

  return (
    <div className="telemetry-widget">
      <div className="telemetry-header">
        <span className="telemetry-title">
          <span className="telemetry-pulse-container">
            <span className={`telemetry-ping ${isReal ? 'real' : 'sim'}`}></span>
            <span className={`telemetry-dot ${isReal ? 'real' : 'sim'}`}></span>
          </span>
          CORTEX Link
        </span>
        <span className={`telemetry-badge ${isReal ? 'real' : 'sim'}`}>
          {data.realityLevel}
        </span>
      </div>
      
      <div className="telemetry-row">
        <span className="telemetry-label">Throughput</span>
        <span className="telemetry-value">
          {data.throughput.toLocaleString()}{' '}
          <span className="telemetry-unit">/s</span>
        </span>
      </div>
      
      <div className="telemetry-row">
        <span className="telemetry-label">Swarm</span>
        <span className="telemetry-value">
          {data.activeAgents.toLocaleString()}{' '}
          <span className="telemetry-unit">AGTS</span>
        </span>
      </div>
      
      <div className="telemetry-row">
        <span className="telemetry-label">Latency O(1)</span>
        <span className={`telemetry-value highlight ${isReal ? 'real' : 'sim'}`}>
          {data.latency.toFixed(3)}{' '}
          <span className="telemetry-unit">ms</span>
        </span>
      </div>
    </div>
  );
}
