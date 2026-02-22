import { useRef, useEffect } from 'react';
import { Activity } from 'lucide-react';
import { masterAnalyzer } from '../../store';

export function MasterMeter() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let raf: number;
    function draw() {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      const values = masterAnalyzer.getValue() as Float32Array;
      const barCount = values.length;
      const barW = W / barCount;

      for (let i = 0; i < barCount; i++) {
        const db = values[i] as number;
        const norm = Math.max(0, (db + 80) / 80);
        const barH = norm * H;

        const ratio = i / barCount;
        const r = Math.round(ratio < 0.5 ? 102 * (1 - ratio * 2) : 204 * (ratio - 0.5) * 2);
        const g = Math.round(ratio < 0.5 ? ratio * 2 * 255 : 255);
        const b = Math.round(ratio < 0.5 ? 255 * (1 - ratio * 2) : 0);

        ctx.fillStyle = `rgba(${r},${g},${b},0.85)`;
        ctx.fillRect(i * barW, H - barH, barW - 1, barH);
      }
      raf = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="flex items-center space-x-2">
      <Activity size={12} className="text-gray-600" />
      <canvas
        ref={canvasRef}
        width={80}
        height={20}
        className="rounded opacity-90"
        style={{ imageRendering: 'pixelated' }}
      />
    </div>
  );
}
