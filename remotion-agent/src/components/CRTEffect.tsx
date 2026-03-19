import React from 'react';
import {useCurrentFrame, interpolate, random} from 'remotion';
import {useBeat} from './BeatReactor';

interface CRTEffectProps {
  powerOff?: boolean;
  scanlineOpacity?: number;
  colorTint?: string;
}

export const CRTEffect: React.FC<CRTEffectProps> = ({
  powerOff = false,
  scanlineOpacity = 0.15,
  colorTint = '#FF1A1A',
}) => {
  const frame = useCurrentFrame();
  const {beatPulse, isOnBeat} = useBeat();

  // Power-off animation
  const scaleY = powerOff
    ? interpolate(frame, [0, 20, 25, 30], [1, 0.02, 0.02, 0], {extrapolateRight: 'clamp'})
    : 1;
  const brightness = powerOff
    ? interpolate(frame, [0, 15, 30], [1, 3, 0], {extrapolateRight: 'clamp'})
    : 1;

  // Moving scanline offset
  const scanlineOffset = (frame * 3) % 4;

  // Micro-flicker synced to half-beats
  const flickerSeed = random(`flicker-${Math.floor(frame / 8)}`);
  const flicker = flickerSeed > 0.85 ? 0.92 : 1;

  // RGB channel shift amount
  const rgbShift = 1.5 + beatPulse * 3;

  return (
    <>
      {/* Scanlines */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: `repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 0, 0, ${scanlineOpacity}) 2px,
            rgba(0, 0, 0, ${scanlineOpacity}) 4px
          )`,
          transform: `translateY(${scanlineOffset}px)`,
          zIndex: 20,
          pointerEvents: 'none',
        }}
      />

      {/* RGB channel split overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 19,
          pointerEvents: 'none',
          opacity: 0.08 + beatPulse * 0.04,
        }}
      >
        {/* Red channel */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: '#FF0000',
            transform: `translateX(${rgbShift}px)`,
            mixBlendMode: 'screen',
            opacity: 0.3,
          }}
        />
        {/* Blue channel */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: '#0000FF',
            transform: `translateX(${-rgbShift}px)`,
            mixBlendMode: 'screen',
            opacity: 0.3,
          }}
        />
      </div>

      {/* Vignette — barrel distortion feel */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: `radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.5) 75%, rgba(0,0,0,0.9) 100%)`,
          zIndex: 21,
          pointerEvents: 'none',
          borderRadius: '8px',
        }}
      />

      {/* Phosphor glow + flicker */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: colorTint,
          opacity: (0.04 + Math.sin(frame * 0.08) * 0.02 + beatPulse * 0.03) * flicker,
          mixBlendMode: 'screen',
          zIndex: 22,
          pointerEvents: 'none',
        }}
      />

      {/* Horizontal interference line */}
      {isOnBeat && (
        <div
          style={{
            position: 'absolute',
            top: `${random(`crt-line-${frame}`) * 100}%`,
            left: 0,
            width: '100%',
            height: 2,
            backgroundColor: '#FFFFFF',
            opacity: 0.3,
            zIndex: 23,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Power-off effect */}
      {powerOff && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: '#FFFFFF',
            opacity: interpolate(frame, [15, 20, 30], [0, 1, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
            zIndex: 30,
            pointerEvents: 'none',
            transform: `scaleY(${scaleY})`,
            filter: `brightness(${brightness})`,
          }}
        />
      )}
    </>
  );
};
