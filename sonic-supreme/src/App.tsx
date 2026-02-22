import { useEffect, useRef, useState, useCallback } from 'react';
import { Play, Pause, FastForward, Rewind, Settings2, Plus, Volume2, Download } from 'lucide-react';
import { useStore } from './store';
import * as Tone from 'tone';
import { motion, AnimatePresence } from 'framer-motion';

import { MasterMeter } from './components/master/MasterMeter';
import { MasterLevelBar } from './components/master/MasterLevelBar';
import { MasterFxDrawer } from './components/master/MasterFxDrawer';
import { TrackHeader } from './components/track/TrackHeader';
import { TrackLane } from './components/track/TrackLane';
import { InspectorPanel } from './components/fx/InspectorPanel';
import { BpmControl } from './components/layout/BpmControl';

// ─── APP ROOT ────────────────────────────────────────────────────────────────
export default function App() {
  const { tracks, selectedTrackId, isPlaying, togglePlay, addTrack, zoom, setZoom } = useStore();
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
          <button
            onClick={useStore.getState().exportAudio}
            disabled={useStore((s) => s.isExporting)}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border transition-all ${useStore((s) => s.isExporting) ? 'border-[var(--color-cyber-lime)] bg-[var(--color-cyber-lime)]/20 text-[var(--color-cyber-lime)]' : 'border-white/5 bg-[#1A1A1A] text-gray-400 hover:text-white hover:border-white/20'}`}
          >
            {useStore((s) => s.isExporting) ? (
              <span className="text-[9px] font-mono font-bold uppercase tracking-widest animate-pulse">Bouncing...</span>
            ) : (
              <>
                <Download size={14} />
                <span className="text-[9px] font-mono font-bold uppercase tracking-widest">Export</span>
              </>
            )}
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
