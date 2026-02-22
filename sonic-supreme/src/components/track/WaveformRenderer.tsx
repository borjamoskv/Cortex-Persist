import { useEffect, useRef } from 'react';
import * as Tone from 'tone';

export function WaveformRenderer({ buffer, color }: { buffer: Tone.ToneAudioBuffer; color: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !buffer.loaded) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const W = canvas.offsetWidth;
    const H = canvas.offsetHeight;
    ctx.clearRect(0, 0, W, H);

    const channelData = buffer.getChannelData(0);
    const step = Math.ceil(channelData.length / W);
    const amp = H / 2;

    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 3;

    for (let i = 0; i < W; i++) {
      let min = 1.0, max = -1.0;
      for (let j = 0; j < step; j++) {
        const idx = i * step + j;
        if (idx < channelData.length) {
          const d = channelData[idx];
          if (d < min) min = d;
          if (d > max) max = d;
        }
      }
      ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
    }
  }, [buffer, color]);

  return <canvas ref={canvasRef} className="w-full h-full" />;
}
