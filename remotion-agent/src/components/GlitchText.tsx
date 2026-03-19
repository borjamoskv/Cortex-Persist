import React from 'react';
import {useCurrentFrame, interpolate, random} from 'remotion';
import {useBeat} from './BeatReactor';

interface GlitchTextProps {
  text: string;
  boldPhrase: string;
  colorAccent: string;
  fontSize?: number;
}

export const GlitchText: React.FC<GlitchTextProps> = ({
  text,
  boldPhrase,
  colorAccent,
  fontSize = 64,
}) => {
  const frame = useCurrentFrame();
  const {beatPulse, isOnBeat, barPulse} = useBeat();

  // === ENTRANCE: slide up + fade in with stagger ===
  const entranceProgress = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const slideY = interpolate(entranceProgress, [0, 1], [60, 0]);
  const opacity = interpolate(entranceProgress, [0, 0.3, 1], [0, 0.5, 1]);

  // === BEAT-REACTIVE SCALE ===
  const beatScale = 1 + beatPulse * 0.05;

  // === CHROMATIC ABERRATION (beat-synced) ===
  const chromaOffset = 2 + beatPulse * 6;
  const skewX = Math.sin(frame * 0.15) * (1 + beatPulse * 3);

  // === RANDOM GLITCH SLICES ===
  const glitchActive = isOnBeat || random(`glitch-${frame}`) > 0.92;
  const scanlineY = random(`scan-y-${frame % 3}`) * 100;
  const scanlineH = 2 + random(`scan-h-${frame % 3}`) * 8;
  const scanlineOffset = (random(`scan-x-${frame % 3}`) - 0.5) * 30;

  // === TEXT SPLIT ===
  const parts = boldPhrase && text.includes(boldPhrase)
    ? text.split(boldPhrase)
    : [text];

  const textContent = parts.length > 1 ? (
    <>
      {parts[0]}
      <span
        style={{
          color: colorAccent,
          textShadow: `0 0 30px ${colorAccent}, 0 0 60px ${colorAccent}, 0 0 90px ${colorAccent}60`,
          filter: `brightness(${1 + beatPulse * 0.5})`,
        }}
      >
        {boldPhrase}
      </span>
      {parts[1]}
    </>
  ) : (
    text
  );

  const baseStyle: React.CSSProperties = {
    fontFamily: "'Impact', 'Arial Black', sans-serif",
    fontSize,
    fontWeight: 900,
    textTransform: 'uppercase',
    textAlign: 'center',
    maxWidth: '80%',
    lineHeight: 1.2,
    whiteSpace: 'pre-line',
    letterSpacing: '0.02em',
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        opacity,
        transform: `translateY(${slideY}px) scale(${beatScale})`,
        zIndex: 10,
      }}
    >
      {/* Red channel offset */}
      <div
        style={{
          ...baseStyle,
          position: 'absolute',
          color: '#FF0000',
          transform: `translateX(${chromaOffset}px) translateY(${-chromaOffset * 0.3}px) skewX(${skewX}deg)`,
          opacity: 0.5,
          mixBlendMode: 'screen',
        }}
      >
        {text}
      </div>

      {/* Cyan channel offset */}
      <div
        style={{
          ...baseStyle,
          position: 'absolute',
          color: '#00FFFF',
          transform: `translateX(${-chromaOffset}px) translateY(${chromaOffset * 0.3}px) skewX(${-skewX * 0.7}deg)`,
          opacity: 0.4,
          mixBlendMode: 'screen',
        }}
      >
        {text}
      </div>

      {/* Main text */}
      <div
        style={{
          ...baseStyle,
          position: 'relative',
          color: '#FFFFFF',
          textShadow: `
            0 0 20px ${colorAccent},
            0 0 40px ${colorAccent}80,
            0 0 80px ${colorAccent}40,
            0 2px 4px rgba(0,0,0,0.8)
          `,
          transform: `translateX(${(random(`main-ox-${frame % 5}`) - 0.5) * beatPulse * 4}px)`,
        }}
      >
        {textContent}
      </div>

      {/* Scanline glitch slice */}
      {glitchActive && (
        <div
          style={{
            position: 'absolute',
            top: `${scanlineY}%`,
            left: 0,
            width: '100%',
            height: scanlineH,
            backgroundColor: colorAccent,
            opacity: 0.3,
            transform: `translateX(${scanlineOffset}px)`,
            mixBlendMode: 'screen',
            zIndex: 20,
          }}
        />
      )}
    </div>
  );
};
