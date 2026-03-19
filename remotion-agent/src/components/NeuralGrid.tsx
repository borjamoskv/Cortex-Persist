import React from 'react';
import {useCurrentFrame, interpolate, random} from 'remotion';
import {useBeat} from './BeatReactor';
import {BEAT_FRAMES} from '../lyrics';

interface NeuralGridProps {
  nodeCount?: number;
  color?: string;
}

interface Node {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
}

export const NeuralGrid: React.FC<NeuralGridProps> = ({
  nodeCount = 40,
  color = '#9B59B6',
}) => {
  const frame = useCurrentFrame();
  const {beatPulse, isOnBeat} = useBeat();

  // Nodes with Brownian drift
  const nodes: Node[] = Array.from({length: nodeCount}, (_, i) => {
    const baseX = random(`nx-${i}`) * 1920;
    const baseY = random(`ny-${i}`) * 1080;
    const vx = (random(`nvx-${i}`) - 0.5) * 0.8;
    const vy = (random(`nvy-${i}`) - 0.5) * 0.8;
    return {
      x: baseX + Math.sin(frame * 0.01 + i) * 30 + frame * vx,
      y: baseY + Math.cos(frame * 0.013 + i * 0.7) * 25 + frame * vy,
      r: 3 + random(`nr-${i}`) * 5,
      vx,
      vy,
    };
  });

  // Edges with cascade firing
  const edges: Array<{from: Node; to: Node; opacity: number; firing: boolean}> = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x;
      const dy = nodes[i].y - nodes[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 450) {
        const fireFrame = Math.floor(random(`fire-${i}-${j}`) * 40);
        // Cascade: connected nodes fire 5 frames after source
        const cascadeDelay = Math.floor(random(`cascade-${i}-${j}`) * 5);
        const isFiring = ((frame + fireFrame) % 40) < (6 + cascadeDelay);
        edges.push({
          from: nodes[i],
          to: nodes[j],
          opacity: isFiring ? 0.7 + beatPulse * 0.3 : 0.08,
          firing: isFiring,
        });
      }
    }
  }

  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 2,
      }}
      viewBox="0 0 1920 1080"
    >
      {/* SVG filter for bloom */}
      <defs>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <filter id="strongGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Edges */}
      {edges.map((edge, i) => (
        <line
          key={`e-${i}`}
          x1={edge.from.x}
          y1={edge.from.y}
          x2={edge.to.x}
          y2={edge.to.y}
          stroke={color}
          strokeWidth={edge.firing ? 2.5 : 0.5}
          opacity={edge.opacity}
          filter={edge.firing ? 'url(#glow)' : undefined}
        />
      ))}

      {/* Nodes */}
      {nodes.map((node, i) => {
        const nodePulse = 1 + beatPulse * 0.6;
        const isBright = (frame + i * 7) % 30 < 8;
        return (
          <circle
            key={`n-${i}`}
            cx={node.x}
            cy={node.y}
            r={node.r * nodePulse}
            fill={color}
            opacity={isBright ? 0.9 : 0.4}
            filter={isBright ? 'url(#strongGlow)' : undefined}
          />
        );
      })}
    </svg>
  );
};
