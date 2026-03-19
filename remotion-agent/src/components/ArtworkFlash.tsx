import React from 'react';
import {useCurrentFrame, interpolate, staticFile, random, Img} from 'remotion';
import {useBeat} from './BeatReactor';

/**
 * Naroa's artwork flash-revealed on beat hits.
 * Shows a brief glimpse of a hyperrealistic portrait with glitch overlay.
 */

const ARTWORKS = [
  'artworks/amy-rocks.webp',
  'artworks/james-rocks.webp',
  'artworks/johnny-rocks.webp',
  'artworks/marilyn-rocks.webp',
  'artworks/peter-rowan.webp',
  'artworks/el-gran-dakari-nino.webp',
  'artworks/2.webp',
  'artworks/3.webp',
];

interface ArtworkFlashProps {
  /** How often to flash (in bars). Default: every 8 bars */
  frequency?: number;
  /** Flash duration in frames */
  flashDuration?: number;
}

export const ArtworkFlash: React.FC<ArtworkFlashProps> = ({
  frequency = 8,
  flashDuration = 8,
}) => {
  const frame = useCurrentFrame();
  const {barIndex, isOnBar} = useBeat();

  // Trigger every N bars
  const shouldFlash = barIndex > 0 && barIndex % frequency === 0;
  const barFrame = frame % Math.round(16.36 * 4 * frequency);
  const isInFlash = shouldFlash || barFrame < flashDuration;

  if (!isInFlash || barFrame >= flashDuration) return null;

  // Select artwork based on bar index
  const artworkIdx = Math.floor(barIndex / frequency) % ARTWORKS.length;
  const artwork = ARTWORKS[artworkIdx];

  // Flash opacity: sharp attack, fast decay
  const opacity = interpolate(barFrame, [0, 2, flashDuration], [0.9, 0.7, 0], {
    extrapolateRight: 'clamp',
  });

  // Glitch offset
  const glitchX = (random(`af-x-${barIndex}`) - 0.5) * 60;
  const glitchY = (random(`af-y-${barIndex}`) - 0.5) * 30;
  const scale = 1.1 + random(`af-s-${barIndex}`) * 0.3;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 35,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {/* Artwork image */}
      <Img
        src={staticFile(artwork)}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: '110%',
          height: '110%',
          objectFit: 'cover',
          transform: `translate(calc(-50% + ${glitchX}px), calc(-50% + ${glitchY}px)) scale(${scale})`,
          opacity,
          filter: `contrast(1.4) saturate(0.3) brightness(1.2)`,
          mixBlendMode: 'screen',
        }}
      />

      {/* Color tint overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: '#2B3BE5',
          opacity: opacity * 0.3,
          mixBlendMode: 'multiply',
        }}
      />

      {/* Horizontal glitch lines */}
      {Array.from({length: 5}, (_, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            top: `${random(`afl-${i}-${barIndex}`) * 100}%`,
            left: 0,
            width: '100%',
            height: 2 + random(`aflh-${i}`) * 6,
            backgroundColor: '#FFFFFF',
            opacity: opacity * 0.4,
            transform: `translateX(${(random(`aflx-${i}-${barIndex}`) - 0.5) * 100}px)`,
          }}
        />
      ))}
    </div>
  );
};
