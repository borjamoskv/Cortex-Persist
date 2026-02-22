import { useRef, useEffect } from 'react';
import { masterMeter } from '../../store';

export function MasterLevelBar() {
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

      const level = masterMeter.getValue();
      const db = typeof level === 'number' ? level : (level as [number, number])[0];
      const norm = Math.max(0, Math.min(1, (db + 60) / 60));

      const grad = ctx.createLinearGradient(0, H, 0, 0);
      grad.addColorStop(0, '#06D6A0');
      grad.addColorStop(0.7, '#CCFF00');
      grad.addColorStop(1, '#FF3366');
      ctx.fillStyle = grad;
      ctx.fillRect(0, H - norm * H, W, norm * H);

      raf = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(raf);
  }, []);

  return <canvas ref={canvasRef} width={4} height={32} className="rounded-sm" />;
}
