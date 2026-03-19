import React from 'react';
import {AbsoluteFill, random} from 'remotion';
import {useBeat} from './BeatReactor';

interface CameraShakeProps {
  children: React.ReactNode;
  intensity?: number;
}

export const CameraShake: React.FC<CameraShakeProps> = ({children, intensity = 1}) => {
  const {frame, beatPulse, barPulse, isOnBar} = useBeat();

  // Perlin-like noise via seeded random
  const noiseX = (random(`shake-x-${Math.floor(frame / 2)}`) - 0.5) * 2;
  const noiseY = (random(`shake-y-${Math.floor(frame / 2)}`) - 0.5) * 2;

  // Micro-shake always present
  const baseShake = 1.5 * intensity;
  // Beat-reactive amplification
  const beatAmplify = beatPulse * 4 * intensity;
  // Heavy bar hits
  const barAmplify = barPulse * 8 * intensity;

  const totalAmplitude = baseShake + beatAmplify + barAmplify;

  const tx = noiseX * totalAmplitude;
  const ty = noiseY * totalAmplitude;

  // Zoom pulse on bar hits
  const scale = 1 + barPulse * 0.015 * intensity;
  // Micro rotation on beats
  const rotate = noiseX * beatPulse * 0.3 * intensity;

  return (
    <AbsoluteFill
      style={{
        transform: `translate(${tx}px, ${ty}px) scale(${scale}) rotate(${rotate}deg)`,
        willChange: 'transform',
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
