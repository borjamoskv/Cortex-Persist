import React from 'react';
import {useCurrentFrame, random} from 'remotion';
import {useBeat} from './BeatReactor';

const BIOS_LINES = [
  'CORTEX BIOS v8.0.0 — Sovereign Trust Engine',
  'Copyright (c) 2026 MOSKV Systems',
  '',
  'CPU: Neural Inference Unit @ 110 BPM',
  'Memory: 239.6s Temporal Buffer ... {OK}',
  'Ledger: SHA-256 Chain Integrity ... {VERIFIED}',
  'Guards: Admission + Contradiction ... {ACTIVE}',
  'Embeddings: ONNX Runtime ... {LOADED}',
  '',
  'Detecting boot media ...',
  'Loading spiritual.kernel ...',
  '',
  '> mount /dev/consciousness',
  '> init --level=sovereign',
  '> systemctl start liturgia.service',
  '',
  'SYSTEM READY.',
  '',
  '█ La resurrección es un reinicio frío.',
];

/** Simulates progress bar: [████████░░] 80% */
const renderProgressBar = (progress: number, width = 20): string => {
  const filled = Math.floor(progress * width);
  const empty = width - filled;
  return `[${'█'.repeat(filled)}${'░'.repeat(empty)}] ${Math.floor(progress * 100)}%`;
};

export const BIOSBoot: React.FC = () => {
  const frame = useCurrentFrame();
  const {beatPulse} = useBeat();
  const visibleLines = Math.floor(frame / 5); // Slightly faster typing

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: '#000000',
        padding: 60,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        zIndex: 5,
      }}
    >
      {BIOS_LINES.slice(0, visibleLines).map((rawLine, i) => {
        // Replace {OK} etc with progress bars when line first appears
        const lineAge = visibleLines - i;
        let line = rawLine;
        
        if (rawLine.includes('{OK}')) {
          const progress = Math.min(1, lineAge / 8);
          line = progress >= 1 
            ? rawLine.replace('{OK}', 'OK')
            : rawLine.replace('{OK}', renderProgressBar(progress));
        } else if (rawLine.includes('{VERIFIED}')) {
          const progress = Math.min(1, lineAge / 10);
          line = progress >= 1
            ? rawLine.replace('{VERIFIED}', 'VERIFIED ✓')
            : rawLine.replace('{VERIFIED}', renderProgressBar(progress));
        } else if (rawLine.includes('{ACTIVE}')) {
          const progress = Math.min(1, lineAge / 6);
          line = progress >= 1
            ? rawLine.replace('{ACTIVE}', 'ACTIVE')
            : rawLine.replace('{ACTIVE}', renderProgressBar(progress));
        } else if (rawLine.includes('{LOADED}')) {
          const progress = Math.min(1, lineAge / 12);
          line = progress >= 1
            ? rawLine.replace('{LOADED}', 'LOADED ✓')
            : rawLine.replace('{LOADED}', renderProgressBar(progress));
        }

        // Random character corruption on recent lines
        if (lineAge <= 3 && line.length > 0) {
          const chars = line.split('');
          const corruptCount = Math.max(0, 3 - lineAge);
          for (let c = 0; c < corruptCount; c++) {
            const idx = Math.floor(random(`corrupt-${i}-${c}-${frame}`) * chars.length);
            const corruptChar = '▓░█▒╬╠╣╗╝'[Math.floor(random(`cc-${i}-${c}-${frame}`) * 10)];
            chars[idx] = corruptChar;
          }
          line = chars.join('');
        }

        const isLast = i === BIOS_LINES.length - 1;
        const isCommand = rawLine.startsWith('>');
        const isReady = rawLine === 'SYSTEM READY.';

        return (
          <div
            key={i}
            style={{
              fontFamily: "'Courier New', 'Consolas', monospace",
              fontSize: isLast ? 28 : 22,
              color: isLast ? '#FFD700' : isReady ? '#FFFFFF' : isCommand ? '#2B3BE5' : '#00FF41',
              lineHeight: 1.5,
              textShadow: isLast
                ? `0 0 20px #FFD700, 0 0 40px #FFD70060`
                : `0 0 6px #00FF4140`,
              fontWeight: isLast || isReady ? 'bold' : 'normal',
              filter: `brightness(${1 + (i === visibleLines - 1 ? beatPulse * 0.3 : 0)})`,
            }}
          >
            {line}
            {/* Blinking cursor on current line */}
            {i === visibleLines - 1 && frame % 12 < 6 && (
              <span style={{color: '#00FF41', opacity: 0.8}}>█</span>
            )}
          </div>
        );
      })}

      {/* CRT overlay effect */}
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
            rgba(0, 255, 65, 0.03) 2px,
            rgba(0, 255, 65, 0.03) 4px
          )`,
          pointerEvents: 'none',
          zIndex: 10,
        }}
      />

      {/* Vignette */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.7) 100%)',
          pointerEvents: 'none',
          zIndex: 11,
        }}
      />
    </div>
  );
};
