import { useState, useRef } from 'react';
import { useStore } from '../../store';

export function BpmControl() {
  const { bpm, setBpm } = useStore();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const tapsRef = useRef<number[]>([]);

  const handleTap = () => {
    const now = performance.now();
    tapsRef.current.push(now);
    if (tapsRef.current.length > 8) tapsRef.current.shift();
    if (tapsRef.current.length >= 2) {
      const gaps = [];
      for (let i = 1; i < tapsRef.current.length; i++) {
        gaps.push(tapsRef.current[i] - tapsRef.current[i - 1]);
      }
      const avgGap = gaps.reduce((a, b) => a + b, 0) / gaps.length;
      const newBpm = Math.round(60000 / avgGap);
      if (newBpm > 40 && newBpm < 300) setBpm(newBpm);
    }
    setTimeout(() => {
      if (performance.now() - tapsRef.current[tapsRef.current.length - 1] > 1800) {
        tapsRef.current = [];
      }
    }, 2000);
  };

  if (editing) {
    return (
      <input
        autoFocus
        className="w-14 text-center font-mono text-sm font-bold bg-black border border-[var(--color-cyber-lime)] text-white rounded outline-none"
        aria-label="BPM value"
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={() => {
          const v = parseFloat(draft);
          if (v > 40 && v < 300) setBpm(v);
          setEditing(false);
        }}
        onKeyDown={e => {
          if (e.key === 'Enter') {
            const v = parseFloat(draft);
            if (v > 40 && v < 300) setBpm(v);
            setEditing(false);
          }
          if (e.key === 'Escape') setEditing(false);
        }}
      />
    );
  }

  return (
    <div className="flex flex-col items-center group cursor-pointer" onClick={handleTap} onDoubleClick={() => { setDraft(bpm.toFixed(0)); setEditing(true); }}>
      <span className="text-[9px] font-mono text-[var(--color-cyber-violet)] uppercase tracking-widest font-bold">BPM</span>
      <span className="text-sm font-bold text-white font-mono tracking-wider group-hover:text-[var(--color-cyber-lime)] transition-colors" title="Click: tap tempo | Double-click: type BPM">
        {bpm.toFixed(1)}
      </span>
    </div>
  );
}
