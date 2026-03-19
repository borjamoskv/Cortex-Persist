import React from 'react';
import {useCurrentFrame, random} from 'remotion';
import {useBeat} from './BeatReactor';

interface DataRainProps {
  color?: string;
  columns?: number;
  speed?: number;
}

const CHARS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF█▓▒░';

export const DataRain: React.FC<DataRainProps> = ({
  color = '#00FF41',
  columns = 50,
  speed = 2,
}) => {
  const frame = useCurrentFrame();
  const {beatPulse, isOnBeat} = useBeat();

  // Beat-reactive speed multiplier
  const speedMult = 1 + beatPulse * 0.8;

  const cols = Array.from({length: columns}, (_, i) => {
    const x = (i / columns) * 100;
    const seed = random(`col-${i}`) * 1000;
    
    // Three speed tiers for parallax depth
    const tier = i % 3; // 0=slow, 1=mid, 2=fast
    const tierSpeed = [0.6, 1.0, 1.6][tier];
    const tierOpacity = [0.2, 0.5, 0.9][tier];
    const tierFontSize = [12, 16, 20][tier];
    
    const yOffset = ((frame * speed * tierSpeed * speedMult + seed) % 160) - 30;
    const charCount = Math.floor(random(`len-${i}`) * 18) + 10;
    const baseOpacity = tierOpacity * (0.7 + random(`op-${i}`) * 0.3);

    const chars = Array.from({length: charCount}, (_, j) => {
      const charIdx = Math.floor(random(`ch-${i}-${j}-${frame % 3}`) * CHARS.length);
      // Aggressive head-to-tail fade
      const charOpacity = j === 0 ? 1 : Math.max(0.05, Math.exp(-j * 0.15));
      return {char: CHARS[charIdx], opacity: charOpacity};
    });

    return {x, yOffset, chars, opacity: baseOpacity, fontSize: tierFontSize, tier};
  });

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
      }}
    >
      {cols.map((col, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${col.x}%`,
            top: `${col.yOffset}%`,
            display: 'flex',
            flexDirection: 'column',
            opacity: col.opacity * (1 + beatPulse * 0.3),
          }}
        >
          {col.chars.map((c, j) => (
            <span
              key={j}
              style={{
                fontFamily: "'Courier New', monospace",
                fontSize: col.fontSize,
                color: j === 0 ? '#FFFFFF' : color,
                opacity: c.opacity,
                textShadow: j === 0
                  ? `0 0 20px ${color}, 0 0 40px ${color}80, 0 0 60px ${color}40`
                  : j < 3
                    ? `0 0 10px ${color}80`
                    : 'none',
                lineHeight: 1.0,
              }}
            >
              {c.char}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
};
