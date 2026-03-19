import React from 'react';
import {useCurrentFrame, interpolate, random} from 'remotion';
import {useBeat} from './BeatReactor';

interface VoidFadeProps {
  fadeIn?: boolean;
}

export const VoidFade: React.FC<VoidFadeProps> = ({fadeIn = false}) => {
  const frame = useCurrentFrame();
  const {beatPulse} = useBeat();

  const bgOpacity = fadeIn
    ? interpolate(frame, [0, 60], [1, 0], {extrapolateRight: 'clamp'})
    : interpolate(frame, [0, 90], [0, 1], {extrapolateRight: 'clamp'});

  // Slow spiral rotation for unease
  const rotation = frame * 0.03;

  // Analog TV noise — more particles, faster refresh
  const noisePixels = Array.from({length: 50}, (_, i) => ({
    x: random(`vx-${i}-${frame % 4}`) * 100,
    y: random(`vy-${i}-${frame % 4}`) * 100,
    size: 1 + random(`vs-${i}`) * 4,
    opacity: random(`vo-${i}-${frame % 3}`) * 0.4,
  }));

  // Scattered dissolution particles (expanding from center)
  const dissolveParticles = Array.from({length: 30}, (_, i) => {
    const angle = random(`da-${i}`) * Math.PI * 2;
    const speed = 0.5 + random(`ds-${i}`) * 2;
    const dist = frame * speed;
    const x = 50 + Math.cos(angle) * dist * 0.3;
    const y = 50 + Math.sin(angle) * dist * 0.3;
    const size = 1 + random(`dsize-${i}`) * 2;
    const fadeOut = interpolate(dist, [0, 200], [0.6, 0], {extrapolateRight: 'clamp'});
    return {x, y, size, opacity: fadeOut};
  });

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 5,
      }}
    >
      {/* Base black with slow rotation */}
      <div
        style={{
          position: 'absolute',
          width: '120%',
          height: '120%',
          top: '-10%',
          left: '-10%',
          backgroundColor: '#0A0A0A',
          opacity: bgOpacity,
          transform: `rotate(${rotation}deg)`,
        }}
      />

      {/* Noise texture */}
      {noisePixels.map((p, i) => (
        <div
          key={`n-${i}`}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            backgroundColor: '#FFFFFF',
            opacity: p.opacity * (1 - bgOpacity * 0.7),
          }}
        />
      ))}

      {/* Dissolution particles */}
      {!fadeIn && dissolveParticles.map((p, i) => (
        <div
          key={`d-${i}`}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            backgroundColor: '#2B3BE5',
            opacity: p.opacity * (1 + beatPulse * 0.3),
            boxShadow: `0 0 ${p.size * 4}px #2B3BE540`,
          }}
        />
      ))}

      {/* Subtle radial gradient overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: `radial-gradient(circle at 50% 50%, transparent 0%, rgba(10,10,10,0.8) 100%)`,
          opacity: 0.5,
        }}
      />
    </div>
  );
};
