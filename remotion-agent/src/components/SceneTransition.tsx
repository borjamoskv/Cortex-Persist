import React from 'react';
import {useCurrentFrame, interpolate, random} from 'remotion';

interface SceneTransitionProps {
  /** Duration in frames for the transition */
  duration?: number;
  /** Direction: 'in' for scene entering, 'out' for scene leaving */
  direction: 'in' | 'out';
  children: React.ReactNode;
}

const SLICE_COUNT = 12;

export const SceneTransition: React.FC<SceneTransitionProps> = ({
  duration = 15,
  direction,
  children,
}) => {
  const frame = useCurrentFrame();

  // For 'in': 0→1 over first `duration` frames
  // For 'out': not used (we handle exit in the parent via durationFrames)
  const progress = direction === 'in'
    ? interpolate(frame, [0, duration], [0, 1], {extrapolateRight: 'clamp'})
    : 1;

  // Global opacity
  const opacity = direction === 'in'
    ? interpolate(frame, [0, duration * 0.6], [0, 1], {extrapolateRight: 'clamp'})
    : 1;

  // Glitch-slice displacement during transition
  const sliceIntensity = direction === 'in'
    ? interpolate(frame, [0, duration], [40, 0], {extrapolateRight: 'clamp'})
    : 0;

  // Scale entrance
  const scale = direction === 'in'
    ? interpolate(frame, [0, duration], [1.08, 1], {extrapolateRight: 'clamp'})
    : 1;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        opacity,
        transform: `scale(${scale})`,
        overflow: 'hidden',
      }}
    >
      {children}
      {/* Glitch slices overlay during entrance */}
      {sliceIntensity > 1 && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            zIndex: 50,
            pointerEvents: 'none',
          }}
        >
          {Array.from({length: SLICE_COUNT}, (_, i) => {
            const yPos = (i / SLICE_COUNT) * 100;
            const height = 100 / SLICE_COUNT;
            const offset = (random(`slice-${i}-${frame}`) - 0.5) * sliceIntensity;

            return (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  top: `${yPos}%`,
                  left: 0,
                  width: '100%',
                  height: `${height}%`,
                  transform: `translateX(${offset}px)`,
                  backgroundColor: `rgba(${random(`sr-${i}`) > 0.5 ? '255,0,0' : '0,255,255'}, ${0.05 * (sliceIntensity / 40)})`,
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};
