import { useEffect, useRef, useState, useCallback } from 'react';
import { Play, Pause, FastForward, Rewind, Settings2, Plus, GripVertical, Volume2, Maximize2, Trash2, Activity } from 'lucide-react';
import { useStore, Track as TrackType, masterAnalyzer, masterMeter } from './store';
import * as Tone from 'tone';
import { motion, AnimatePresence } from 'framer-motion';

// ─── MASTER METER (FFT Bars in Header) ──────────────────────────────────────
function MasterMeter() {
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
        // Convert dB to 0-1 range (min -100, max 0)
        const db = values[i] as number;
        const norm = Math.max(0, (db + 80) / 80);
        const barH = norm * H;

        // Color: low=violet, mid=lime, high=white
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

// ─── MASTER LEVEL METER (RMS dB bar) ────────────────────────────────────────
function MasterLevelBar() {
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

// ─── BPM TAP TEMPO ──────────────────────────────────────────────────────────
function BpmControl() {
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
    // Reset taps after 2s idle
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
        className="w-14 text-center font-mono text-sm font-bold bg-black border border-cyber-lime text-white rounded outline-none"
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

// ─── APP ROOT ────────────────────────────────────────────────────────────────
export default function App() {
  const { tracks, selectedTrackId, selectTrack, isPlaying, togglePlay, addTrack, zoom, setZoom } = useStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const playheadRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const [displayTime, setDisplayTime] = useState('0:00.00');
  const [showMasterFx, setShowMasterFx] = useState(false);

  // UI loop
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'S' || e.key === 's') {
        const time = Tone.Transport.seconds;
        const id = useStore.getState().selectedTrackId;
        if (id) useStore.getState().splitTrack(id, time);
      }
      if (e.key === ' ' && e.target === document.body) {
        e.preventDefault();
        useStore.getState().togglePlay();
      }
      if (e.key === 'Escape') useStore.getState().selectTrack(null);
    };
    window.addEventListener('keydown', handleKeyDown);

    let raf: number;
    function updateLoop() {
      if (Tone.Transport.state === 'started') {
        const t = Tone.Transport.seconds;
        const m = Math.floor(t / 60);
        const s = Math.floor(t % 60).toString().padStart(2, '0');
        const ms = Math.floor((t % 1) * 100).toString().padStart(2, '0');
        setDisplayTime(`${m}:${s}.${ms}`);
      }
      if (playheadRef.current) {
        const px = Tone.Transport.seconds * useStore.getState().zoom;
        playheadRef.current.style.transform = `translateX(${px}px)`;
      }
      raf = requestAnimationFrame(updateLoop);
    }
    updateLoop();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('keydown', handleKeyDown); };
  }, []);

  // Timeline click → scrub
  const handleTimelineClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left + e.currentTarget.scrollLeft;
    const time = Math.max(0, x / zoom);
    useStore.getState().setTime(time);
    const m = Math.floor(time / 60);
    const s = Math.floor(time % 60).toString().padStart(2, '0');
    const ms = Math.floor((time % 1) * 100).toString().padStart(2, '0');
    setDisplayTime(`${m}:${s}.${ms}`);
  }, [zoom]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) addTrack(e.target.files[0]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const selectedTrack = tracks.find(t => t.id === selectedTrackId) ?? null;

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0A0A0A] text-gray-300 font-sans selection:bg-[var(--color-cyber-lime)] selection:text-black overflow-hidden">

      {/* ── HEADER / TRANSPORT ─────────────────────────────────────── */}
      <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-[#080808] z-30 shadow-2xl relative flex-shrink-0">
        <div className="flex items-center space-x-4">
          <div className="text-2xl font-black tracking-tighter text-white uppercase drop-shadow-[0_0_10px_rgba(204,255,0,0.2)]">
            SONIC<span className="text-[var(--color-cyber-lime)]">_SUPREME</span>
          </div>
          <MasterLevelBar />
        </div>

        {/* CENTER TRANSPORT */}
        <div className="absolute left-1/2 transform -translate-x-1/2 flex items-center space-x-5 bg-[#111] px-6 py-2 rounded-full border border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.7)]">
          <div className="w-24 text-center font-mono text-[var(--color-cyber-lime)] text-lg font-bold tracking-wider tabular-nums">
            {displayTime}
          </div>

          <div className="h-6 w-px bg-white/10" />

          <button onClick={() => {
            Tone.Transport.stop();
            Tone.Transport.seconds = 0;
            setDisplayTime('0:00.00');
            if (isPlaying) togglePlay();
          }} className="hover:text-[var(--color-cyber-lime)] transition-colors text-gray-500">
            <Rewind size={18} />
          </button>

          <button
            onClick={togglePlay}
            className={`flex items-center justify-center h-11 w-11 rounded-full transition-all duration-200 ${isPlaying
              ? 'bg-[var(--color-cyber-lime)] text-black shadow-[0_0_24px_rgba(204,255,0,0.7)] scale-105'
              : 'bg-white text-black hover:scale-105 hover:shadow-[0_0_15px_rgba(255,255,255,0.4)]'
            }`}
          >
            {isPlaying ? <Pause size={20} className="fill-current" /> : <Play size={20} className="fill-current ml-0.5" />}
          </button>

          <button className="hover:text-[var(--color-cyber-lime)] transition-colors text-gray-500">
            <FastForward size={18} />
          </button>

          <div className="h-6 w-px bg-white/10" />

          <BpmControl />

          <div className="h-6 w-px bg-white/10" />

          <MasterMeter />
        </div>

        {/* RIGHT CONTROLS */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 bg-[#1A1A1A] px-3 py-1.5 rounded-full border border-white/5">
            <span className="text-[9px] font-mono text-gray-500 uppercase tracking-widest font-bold">ZOOM</span>
            <input type="range" min="10" max="200" value={zoom} onChange={e => setZoom(parseFloat(e.target.value))} className="w-20 opacity-80 hover:opacity-100 transition-opacity" />
          </div>
          <button className="p-2 hover:bg-white/5 rounded-full transition-colors group">
            <Maximize2 size={16} className="group-hover:text-[var(--color-cyber-lime)] text-gray-500" />
          </button>
          <button
            onClick={() => setShowMasterFx(v => !v)}
            className={`p-2 rounded-full transition-all ${showMasterFx ? 'bg-[var(--color-cyber-violet)]/20 text-[var(--color-cyber-violet)]' : 'hover:bg-white/5 text-gray-500'}`}
          >
            <Settings2 size={16} />
          </button>
        </div>
      </header>

      {/* ── MASTER FX DRAWER ───────────────────────────────────────── */}
      <AnimatePresence>
        {showMasterFx && <MasterFxDrawer onClose={() => setShowMasterFx(false)} />}
      </AnimatePresence>

      {/* ── MAIN WORKSPACE ─────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden min-h-0">

        {/* LEFT: TRACK HEADERS */}
        <div className="w-72 bg-[#111] border-r border-white/5 flex flex-col z-10 shadow-2xl relative flex-shrink-0">
          <div className="h-10 border-b border-white/5 flex items-center px-4 font-mono text-[10px] text-gray-500 uppercase tracking-widest font-bold bg-[#0A0A0A] flex-shrink-0">
            Channels ({tracks.length})
          </div>

          <div className="flex-1 overflow-y-auto hidden-scrollbar pb-20 min-h-0">
            {tracks.length === 0 && (
              <div className="p-8 text-center flex flex-col items-center opacity-40 space-y-4 mt-8">
                <div className="p-4 rounded-full border border-dashed border-white/20">
                  <Volume2 size={28} className="text-gray-500" />
                </div>
                <span className="text-xs font-mono text-gray-500 uppercase tracking-widest">Import Audio to Begin</span>
              </div>
            )}
            {tracks.map(track => (
              <TrackHeader key={track.id} track={track} />
            ))}
          </div>

          <div className="absolute bottom-0 w-full p-4 border-t border-white/5 bg-[#111] backdrop-blur-md">
            <input type="file" accept="audio/*" className="hidden" ref={fileInputRef} onChange={handleFileUpload} />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full py-2.5 border border-[var(--color-cyber-lime)]/30 text-[var(--color-cyber-lime)] hover:bg-[var(--color-cyber-lime)]/10 hover:shadow-[0_0_20px_rgba(204,255,0,0.15)] hover:border-[var(--color-cyber-lime)] rounded font-mono text-xs uppercase tracking-widest transition-all flex items-center justify-center space-x-2"
            >
              <Plus size={14} />
              <span className="font-bold">Import Audio</span>
            </button>
          </div>
        </div>

        {/* CENTER: TIMELINE */}
        <div
          ref={timelineRef}
          className="flex-1 bg-[#0A0A0A] relative overflow-auto min-w-0"
          style={{
            backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px)`,
            backgroundSize: `${zoom}px 112px`
          }}
        >
          {/* Time Ruler (clickable for scrubbing) */}
          <div
            className="h-10 border-b border-white/5 bg-[#1a1a1a]/95 backdrop-blur sticky top-0 z-10 flex items-end cursor-col-resize"
            style={{ minWidth: 'max-content' }}
            onClick={handleTimelineClick}
          >
            {Array.from({ length: 300 }).map((_, i) => (
              <div key={i} className="flex-none h-3 border-l border-white/10 relative" style={{ width: `${zoom * 2}px` }}>
                <span className="absolute -top-5 left-1 text-[9px] text-gray-600 font-mono pointer-events-none select-none">
                  {Math.floor(i * 2 / 60)}:{String((i * 2) % 60).padStart(2, '0')}
                </span>
              </div>
            ))}
          </div>

          {/* Track Lanes */}
          <div className="relative pb-32" style={{ minWidth: 'max-content' }}>
            {tracks.map(track => (
              <TrackLane key={track.id} track={track} />
            ))}

            {/* Playhead */}
            <div
              ref={playheadRef}
              className="absolute top-0 bottom-0 w-[1px] bg-[var(--color-cyber-lime)] shadow-[0_0_14px_rgba(204,255,0,1)] z-20 pointer-events-none"
              style={{ left: '0px' }}
            >
              <div className="w-3 h-3 bg-[var(--color-cyber-lime)] rotate-45 transform -translate-x-1/2 -translate-y-1.5 shadow-[0_0_12px_rgba(204,255,0,0.9)] border border-black" />
            </div>
          </div>
        </div>

        {/* RIGHT: INSPECTOR PANEL */}
        <AnimatePresence>
          {selectedTrack && (
            <motion.div
              key="inspector"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 224, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="bg-[#111] border-l border-white/5 flex-shrink-0 overflow-hidden"
            >
              <InspectorPanel track={selectedTrack} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ─── TRACK HEADER ────────────────────────────────────────────────────────────
function TrackHeader({ track }: { track: TrackType }) {
  const { updateTrack, removeTrack, selectedTrackId, selectTrack } = useStore();
  const isSelected = selectedTrackId === track.id;

  return (
    <div
      onClick={() => selectTrack(isSelected ? null : track.id)}
      className={`h-28 border-b border-white/5 p-3 flex flex-col justify-between group hover:bg-white/[0.03] transition-colors relative overflow-hidden cursor-pointer ${isSelected ? 'bg-white/[0.05]' : 'bg-[#131313]'}`}
    >
      <div className="absolute left-0 top-0 bottom-0 w-1 transition-all" style={{ backgroundColor: track.color, boxShadow: isSelected ? `0 0 12px ${track.color}` : `0 0 6px ${track.color}40` }} />

      <div className="flex items-center justify-between pl-2">
        <div className="flex items-center space-x-2">
          <GripVertical size={12} className="text-gray-600 opacity-0 group-hover:opacity-100 cursor-grab" />
          <input
            type="text"
            value={track.name.replace(/\.[^/.]+$/, '')}
            onChange={e => updateTrack(track.id, { name: e.target.value })}
            onClick={e => e.stopPropagation()}
            className="font-bold text-xs text-gray-100 truncate w-28 bg-transparent outline-none border-b border-transparent focus:border-white/20 tracking-wide"
          />
        </div>
        <div className="flex space-x-1 items-center">
          <button
            onClick={e => { e.stopPropagation(); updateTrack(track.id, { muted: !track.muted }); }}
            className={`w-6 h-6 rounded flex items-center justify-center text-[9px] font-bold transition-all ${track.muted ? 'bg-red-500 text-black shadow-[0_0_10px_rgba(239,68,68,0.6)]' : 'bg-[#2A2A2A] text-gray-400 hover:bg-white/10'}`}
          >M</button>
          <button
            onClick={e => { e.stopPropagation(); updateTrack(track.id, { solo: !track.solo }); }}
            className={`w-6 h-6 rounded flex items-center justify-center text-[9px] font-bold transition-all ${track.solo ? 'bg-yellow-400 text-black shadow-[0_0_10px_rgba(234,179,8,0.6)]' : 'bg-[#2A2A2A] text-gray-400 hover:bg-white/10'}`}
          >S</button>
          <button
            onClick={e => { e.stopPropagation(); removeTrack(track.id); }}
            className="w-6 h-6 rounded flex items-center justify-center text-gray-600 hover:text-red-500 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100 ml-0.5"
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      <div className="pl-2 pr-1 mt-1 space-y-2.5">
        <div className="flex items-center space-x-2">
          <span className="text-[9px] font-mono text-gray-500 font-bold w-4">PAN</span>
          <div className="flex-1 h-1 bg-[#0A0A0A] rounded-full overflow-hidden relative">
            <div className="absolute h-full w-[1px] bg-gray-600 left-1/2 transform -translate-x-1/2 z-10" />
            <input type="range" min="-1" max="1" step="0.01" value={track.pan} onChange={e => updateTrack(track.id, { pan: parseFloat(e.target.value) })} className="absolute inset-0 w-full opacity-0 cursor-ew-resize z-20" />
            <div className="h-full absolute rounded-full pointer-events-none" style={{
              backgroundColor: track.color,
              left: track.pan < 0 ? `${(track.pan + 1) * 50}%` : '50%',
              right: track.pan > 0 ? `${(1 - track.pan) * 50}%` : '50%',
              opacity: Math.abs(track.pan) > 0.02 ? 1 : 0
            }} />
          </div>
          <span className="text-[8px] font-mono text-gray-600 w-5 text-right">{track.pan > 0 ? `R${Math.round(track.pan * 100)}` : track.pan < 0 ? `L${Math.round(-track.pan * 100)}` : 'C'}</span>
        </div>

        <div className="flex items-center space-x-2">
          <Volume2 size={9} className="text-gray-500 w-4 flex-shrink-0" />
          <div className="flex-1 h-1.5 bg-[#0A0A0A] rounded-full relative">
            <div className="h-full rounded-full transition-all duration-75" style={{ width: `${track.volume * 100}%`, backgroundColor: track.color, boxShadow: `0 0 6px ${track.color}60` }} />
            <input type="range" min="0" max="1" step="0.01" value={track.volume} onChange={e => updateTrack(track.id, { volume: parseFloat(e.target.value) })} className="absolute inset-0 w-full opacity-0 cursor-ew-resize" />
          </div>
          <span className="text-[8px] font-mono text-gray-600 w-6 text-right">{Math.round(track.volume * 100)}</span>
        </div>
      </div>
    </div>
  );
}

// ─── TRACK LANE ──────────────────────────────────────────────────────────────
function TrackLane({ track }: { track: TrackType }) {
  const { selectedTrackId, selectTrack, updateTrack, zoom } = useStore();
  const isSelected = selectedTrackId === track.id;
  const pxPerSecond = zoom;
  const duration = track.player?.buffer?.duration || 10;
  const width = duration * pxPerSecond;

  return (
    <div className="h-28 border-b border-white/5 flex items-center bg-transparent group relative">
      <motion.div
        drag="x"
        dragMomentum={false}
        dragElastic={0}
        onDragEnd={(_, info) => {
          const newStart = Math.max(0, track.startTime + (info.offset.x / pxPerSecond));
          updateTrack(track.id, { startTime: newStart });
        }}
        onClick={e => { e.stopPropagation(); selectTrack(track.id); }}
        className={`absolute h-[80px] rounded-md border flex items-center justify-center overflow-hidden cursor-pointer shadow-md transition-shadow ${isSelected ? 'border-[var(--color-cyber-lime)] shadow-[0_0_20px_rgba(204,255,0,0.25)] z-10' : 'border-white/[0.08] hover:border-white/20'}`}
        style={{
          left: `${track.startTime * pxPerSecond}px`,
          width: `${width}px`,
          backgroundColor: `${track.color}${isSelected ? '22' : '15'}`
        }}
      >
        <div className="absolute top-1.5 left-2 text-[9px] font-mono font-bold tracking-widest uppercase opacity-90 truncate max-w-full pr-4 z-10" style={{ color: track.color, textShadow: `0 0 8px ${track.color}` }}>
          {track.name.replace(/\.[^/.]+$/, '')}
        </div>
        <div className="absolute inset-0 w-full h-full pointer-events-none opacity-75">
          {track.player?.buffer.loaded
            ? <WaveformRenderer buffer={track.player.buffer} color={track.color} />
            : <div className="w-full h-full flex items-center justify-center text-[10px] font-mono opacity-40 text-gray-400">Decoding…</div>
          }
        </div>
      </motion.div>
    </div>
  );
}

// ─── WAVEFORM RENDERER ───────────────────────────────────────────────────────
function WaveformRenderer({ buffer, color }: { buffer: Tone.ToneAudioBuffer; color: string }) {
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

// ─── INSPECTOR PANEL (RIGHT SIDEBAR) ─────────────────────────────────────────
function InspectorPanel({ track }: { track: TrackType }) {
  const { updateTrack } = useStore();

  return (
    <div className="w-56 h-full flex flex-col overflow-y-auto hidden-scrollbar">
      {/* Header */}
      <div className="h-10 flex items-center px-3 border-b border-white/5 bg-[#0A0A0A] flex-shrink-0">
        <div className="w-2 h-2 rounded-full mr-2 flex-shrink-0" style={{ backgroundColor: track.color, boxShadow: `0 0 8px ${track.color}` }} />
        <span className="font-bold text-[10px] text-white uppercase tracking-wider font-mono truncate">{track.name.replace(/\.[^/.]+$/, '')}</span>
      </div>

      <div className="p-3 space-y-3 flex-1">
        <p className="text-[9px] font-mono text-gray-600 uppercase tracking-widest font-bold">FX Rack</p>

        {/* ── VOID REVERB ── */}
        <div className={`rounded-md p-3 space-y-2.5 border relative overflow-hidden transition-all ${track.fx.reverbOn ? 'border-[var(--color-cyber-violet)]/40 bg-[var(--color-cyber-violet)]/5' : 'border-white/5 bg-[#1A1A1A] opacity-60'}`}>
          <div className="absolute left-0 top-0 bottom-0 w-[2px]" style={{ backgroundColor: 'var(--color-cyber-violet)' }} />
          <div className="flex justify-between items-center pl-2">
            <span className="font-bold text-[10px] text-gray-300 uppercase tracking-wider">Void Reverb</span>
            <button
              onClick={() => updateTrack(track.id, { fx: { ...track.fx, reverbOn: !track.fx.reverbOn } })}
              className={`w-9 h-4 rounded-full text-[8px] font-bold flex items-center justify-center transition-all ${track.fx.reverbOn ? 'bg-[var(--color-cyber-violet)] shadow-[0_0_8px_rgba(102,0,255,0.8)]' : 'bg-[#333] text-gray-500'}`}
            >{track.fx.reverbOn ? 'ON' : 'OFF'}</button>
          </div>
          <FxKnob label="MIX" value={track.fx.reverbMix} color="var(--color-cyber-violet)"
            onChange={v => updateTrack(track.id, { fx: { ...track.fx, reverbMix: v } })} />
          <FxKnob label="SIZE" value={track.fx.reverbSize} color="var(--color-cyber-violet)"
            onChange={v => updateTrack(track.id, { fx: { ...track.fx, reverbSize: v } })} />
        </div>

        {/* ── CYBER DELAY ── */}
        <div className={`rounded-md p-3 space-y-2.5 border relative overflow-hidden transition-all ${track.fx.delayOn ? 'border-[var(--color-cyber-lime)]/40 bg-[var(--color-cyber-lime)]/5' : 'border-white/5 bg-[#1A1A1A] opacity-60'}`}>
          <div className="absolute left-0 top-0 bottom-0 w-[2px]" style={{ backgroundColor: 'var(--color-cyber-lime)' }} />
          <div className="flex justify-between items-center pl-2">
            <span className="font-bold text-[10px] text-gray-300 uppercase tracking-wider">Cyber Delay</span>
            <button
              onClick={() => updateTrack(track.id, { fx: { ...track.fx, delayOn: !track.fx.delayOn } })}
              className={`w-9 h-4 rounded-full text-[8px] font-bold flex items-center justify-center transition-all ${track.fx.delayOn ? 'bg-[var(--color-cyber-lime)] text-black shadow-[0_0_8px_rgba(204,255,0,0.8)]' : 'bg-[#333] text-gray-500'}`}
            >{track.fx.delayOn ? 'ON' : 'OFF'}</button>
          </div>
          <FxKnob label="MIX" value={track.fx.delayMix} color="var(--color-cyber-lime)"
            onChange={v => updateTrack(track.id, { fx: { ...track.fx, delayMix: v } })} />
        </div>

        {/* ── Track Info ── */}
        <div className="pt-2 border-t border-white/5 space-y-1.5 font-mono text-[9px]">
          <p className="text-gray-600 uppercase tracking-widest font-bold mb-2">Track Info</p>
          <div className="flex justify-between"><span className="text-gray-500">START</span><span className="text-white">{(track.startTime || 0).toFixed(2)}s</span></div>
          <div className="flex justify-between"><span className="text-gray-500">LENGTH</span><span className="text-white">{(track.duration || 0).toFixed(2)}s</span></div>
          <div className="flex justify-between"><span className="text-gray-500">VOLUME</span><span className="text-white">{Math.round(track.volume * 100)}%</span></div>
          <div className="flex justify-between"><span className="text-gray-500">PAN</span><span className="text-white">{track.pan === 0 ? 'C' : track.pan > 0 ? `R${Math.round(track.pan * 100)}` : `L${Math.round(-track.pan * 100)}`}</span></div>
        </div>

        {/* Shortcut hints */}
        <div className="pt-2 border-t border-white/5 space-y-1 font-mono text-[8px] text-gray-600">
          <p className="uppercase tracking-widest font-bold text-gray-500 mb-1.5">Shortcuts</p>
          <div className="flex justify-between"><span className="bg-white/5 px-1 rounded">Space</span><span>Play / Pause</span></div>
          <div className="flex justify-between"><span className="bg-white/5 px-1 rounded">S</span><span>Split at playhead</span></div>
          <div className="flex justify-between"><span className="bg-white/5 px-1 rounded">Esc</span><span>Deselect</span></div>
        </div>
      </div>
    </div>
  );
}

// ─── FX KNOB (Compact Slider Row) ────────────────────────────────────────────
function FxKnob({ label, value, color, onChange }: { label: string; value: number; color: string; onChange: (v: number) => void }) {
  return (
    <div className="pl-2 space-y-1">
      <div className="flex justify-between text-[9px] font-mono font-bold">
        <span className="text-gray-500">{label}</span>
        <span style={{ color }}>{Math.round(value * 100)}%</span>
      </div>
      <div className="h-1 bg-black rounded-full relative">
        <div className="absolute h-full rounded-full" style={{ width: `${value * 100}%`, backgroundColor: color, boxShadow: `0 0 4px ${color}80` }} />
        <input type="range" min="0" max="1" step="0.01" value={value} onChange={e => onChange(parseFloat(e.target.value))} className="absolute inset-0 w-full opacity-0 cursor-ew-resize" />
      </div>
    </div>
  );
}

// ─── MASTER FX DRAWER ────────────────────────────────────────────────────────
function MasterFxDrawer({ onClose }: { onClose: () => void }) {
  const { masterFx, updateMasterFx } = useStore();

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="bg-[#0D0D0D] border-b border-white/5 overflow-hidden z-20 flex-shrink-0"
    >
      <div className="px-6 py-3 flex items-center space-x-8">
        <span className="text-[9px] font-mono text-gray-500 uppercase tracking-widest font-bold w-16">MASTER BUS</span>

        {/* EQ */}
        <div className="flex items-center space-x-4">
          <span className="text-[9px] font-mono text-[var(--color-cyber-lime)] uppercase tracking-widest font-bold">EQ3</span>
          {([['LOW', 'eqLow'], ['MID', 'eqMid'], ['HIGH', 'eqHigh']] as const).map(([lbl, key]) => (
            <div key={key} className="flex flex-col items-center space-y-1">
              <span className="text-[8px] font-mono text-gray-500">{lbl}</span>
              <input type="range" min="-20" max="20" step="0.5" value={masterFx[key]} onChange={e => updateMasterFx({ [key]: parseFloat(e.target.value) })} className="w-16 h-1" />
              <span className="text-[8px] font-mono text-gray-400">{masterFx[key] > 0 ? '+' : ''}{masterFx[key].toFixed(1)}dB</span>
            </div>
          ))}
        </div>

        <div className="h-8 w-px bg-white/5" />

        {/* Compressor */}
        <div className="flex items-center space-x-4">
          <span className="text-[9px] font-mono text-[var(--color-cyber-violet)] uppercase tracking-widest font-bold">COMP</span>
          <div className="flex flex-col items-center space-y-1">
            <span className="text-[8px] font-mono text-gray-500">THRESH</span>
            <input type="range" min="-60" max="0" step="0.5" value={masterFx.compThreshold} onChange={e => updateMasterFx({ compThreshold: parseFloat(e.target.value) })} className="w-20 h-1" />
            <span className="text-[8px] font-mono text-gray-400">{masterFx.compThreshold.toFixed(1)}dB</span>
          </div>
          <div className="flex flex-col items-center space-y-1">
            <span className="text-[8px] font-mono text-gray-500">RATIO</span>
            <input type="range" min="1" max="20" step="0.5" value={masterFx.compRatio} onChange={e => updateMasterFx({ compRatio: parseFloat(e.target.value) })} className="w-16 h-1" />
            <span className="text-[8px] font-mono text-gray-400">{masterFx.compRatio.toFixed(1)}:1</span>
          </div>
        </div>

        <button onClick={onClose} className="ml-auto text-gray-600 hover:text-[var(--color-cyber-lime)] font-mono text-xs transition-colors">✕</button>
      </div>
    </motion.div>
  );
}
