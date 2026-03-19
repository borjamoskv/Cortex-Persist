import React from 'react';
import {random} from 'remotion';
import {useBeat} from './BeatReactor';

interface ParticleFieldProps {
  color?: string;
  count?: number;
}

interface Particle {
  x: number;
  y: number;
  size: number;
  speed: number;
  drift: number;
  opacity: number;
  phase: number;
}

export const ParticleField: React.FC<ParticleFieldProps> = ({
  color = '#2B3BE5',
  count = 60,
}) => {
  const {frame, beatPulse} = useBeat();

  const particles: Particle[] = Array.from({length: count}, (_, i) => ({
    x: random(`px-${i}`) * 100,
    y: random(`py-${i}`) * 100,
    size: 1 + random(`ps-${i}`) * 3,
    speed: 0.02 + random(`psp-${i}`) * 0.08,
    drift: (random(`pd-${i}`) - 0.5) * 0.03,
    opacity: 0.1 + random(`po-${i}`) * 0.4,
    phase: random(`pp-${i}`) * Math.PI * 2,
  }));

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        zIndex: 1,
        pointerEvents: 'none',
      }}
    >
      {particles.map((p, i) => {
        const yPos = (p.y + frame * p.speed) % 110 - 5;
        const xPos = p.x + Math.sin(frame * 0.02 + p.phase) * 3 + frame * p.drift;
        const pulsedSize = p.size * (1 + beatPulse * 0.8);
        const pulsedOpacity = p.opacity * (0.6 + beatPulse * 0.6);

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${xPos % 100}%`,
              top: `${yPos}%`,
              width: pulsedSize,
              height: pulsedSize,
              borderRadius: '50%',
              backgroundColor: color,
              opacity: pulsedOpacity,
              boxShadow: `0 0 ${pulsedSize * 3}px ${color}60`,
            }}
          />
        );
      })}
    </div>
  );
};
