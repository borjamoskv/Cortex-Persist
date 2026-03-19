import React from 'react';
import {useCurrentFrame, interpolate, random} from 'remotion';
import {useBeat} from './BeatReactor';

interface StrobeFlashProps {
  color?: string;
  intensity?: number;
}

export const StrobeFlash: React.FC<StrobeFlashProps> = ({
  color = '#FFFFFF',
  intensity = 1,
}) => {
  const frame = useCurrentFrame();
  const {beatPulse, isOnBeat, barPulse} = useBeat();

  // Multi-layer flash: sharp attack on beat, exponential decay
  const flashOpacity = isOnBeat ? 0.8 * intensity : beatPulse * 0.15 * intensity;

  // Random flicker for chaos
  const randomFlash = random(`strobe-${frame}`) > 0.88;
  const randomOpacity = randomFlash ? 0.25 * intensity : 0;

  // Color flash (offset by 1 frame from white)
  const colorFlashFrame = (frame - 1);
  const isColorFlash = (colorFlashFrame % Math.round(16.36)) < 2;

  // Afterimage: inverted color ghost for 3 frames post-flash
  const afterimageFrame = (frame - 3);
  const isAfterimage = (afterimageFrame % Math.round(16.36)) < 3;

  return (
    <>
      {/* Primary white flash */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: '#FFFFFF',
          opacity: flashOpacity + randomOpacity,
          mixBlendMode: 'screen',
          zIndex: 15,
          pointerEvents: 'none',
        }}
      />

      {/* Color flash (1 frame delay) */}
      {isColorFlash && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: color,
            opacity: 0.4 * intensity,
            mixBlendMode: 'screen',
            zIndex: 14,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Afterimage (inverted) */}
      {isAfterimage && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: '#000000',
            opacity: 0.15 * intensity,
            mixBlendMode: 'multiply',
            zIndex: 13,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Horizontal light bars on bar hits */}
      {barPulse > 0.5 && (
        <>
          <div
            style={{
              position: 'absolute',
              top: '48%',
              left: 0,
              width: '100%',
              height: 4,
              backgroundColor: color,
              opacity: barPulse * 0.6 * intensity,
              boxShadow: `0 0 40px ${color}, 0 0 80px ${color}60`,
              zIndex: 16,
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: '52%',
              left: 0,
              width: '100%',
              height: 2,
              backgroundColor: '#FFFFFF',
              opacity: barPulse * 0.4 * intensity,
              boxShadow: `0 0 30px #FFFFFF80`,
              zIndex: 16,
              pointerEvents: 'none',
            }}
          />
        </>
      )}
    </>
  );
};
