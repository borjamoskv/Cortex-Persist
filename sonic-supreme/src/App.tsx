import { useEffect, useRef, useState } from 'react';
import { Play, Pause, FastForward, Rewind, Settings2, Plus, GripVertical, Volume2, Maximize2, Trash2, Edit3, Type } from 'lucide-react';
import { useStore, Track as TrackType } from './store';
import * as Tone from 'tone';
import { motion } from 'framer-motion';

export default function App() {
  const { tracks, selectedTrackId, selectTrack, isPlaying, togglePlay, addTrack, bpm, zoom, setZoom } = useStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const playheadRef = useRef<HTMLDivElement>(null);
  const [displayTime, setDisplayTime] = useState('0:00');

  useEffect(() => {
    // Keyboard Shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      // 'S' key to split track at playhead
      if (e.key === 'S' || e.key === 's') {
        const time = Tone.Transport.seconds;
        const currentSelectedId = useStore.getState().selectedTrackId;
        if (currentSelectedId) {
          useStore.getState().splitTrack(currentSelectedId, time);
        }
      }
      // Space to play/pause
      if (e.key === ' ' && e.target === document.body) {
        e.preventDefault();
        useStore.getState().togglePlay();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);

    // UI Update Loop for Time
    let animationFrameId: number;
    
    function updateLoop() {
      if (Tone.Transport.state === 'started') {
        const time = Tone.Transport.seconds;
        const m = Math.floor(time / 60);
        const s = Math.floor(time % 60).toString().padStart(2, '0');
        const ms = Math.floor((time % 1) * 100).toString().padStart(2, '0');
        setDisplayTime(`${m}:${s}.${ms}`);
      }
      
      // Always update Playhead UI independently to allow fluid scrubbing rendering
      if (playheadRef.current) {
         const pxtime = Tone.Transport.seconds * useStore.getState().zoom;
         playheadRef.current.style.transform = `translateX(${pxtime}px)`;
      }

      animationFrameId = requestAnimationFrame(updateLoop);
    }
    
    updateLoop();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addTrack(e.target.files[0]);
    }
    // reset input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-noir-900 text-gray-300 font-sans selection:bg-cyber-lime selection:text-black">
      {/* HEADER / TRANSPORT */}
      <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-[#0A0A0A] z-20 shadow-lg relative">
        <div className="flex items-center space-x-4">
          <div className="text-2xl font-black tracking-tighter text-white uppercase drop-shadow-[0_0_10px_rgba(204,255,0,0.2)] cursor-pointer">
            SONIC<span className="text-[var(--color-cyber-lime)]">_SUPREME</span>
          </div>
        </div>

        {/* TRANSPORT CONTROLS */}
        <div className="absolute left-1/2 transform -translate-x-1/2 flex items-center space-x-6 glass-panel px-6 py-2 rounded-full border border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
          <div className="w-24 text-center font-mono text-[var(--color-cyber-lime)] text-xl font-bold tracking-wider">
            {displayTime}
          </div>
          
          <div className="h-6 w-px bg-white/10 mx-2"></div>

          <button 
            onClick={() => {
               Tone.Transport.stop(); 
               Tone.Transport.seconds = 0; 
               setDisplayTime('0:00.00'); 
               if (isPlaying) togglePlay(); // set store to false
            }}
            className="hover:text-[var(--color-cyber-lime)] transition-colors text-gray-400"
          >
            <Rewind size={20} />
          </button>
          
          <button 
            onClick={togglePlay}
            className={`flex items-center justify-center h-12 w-12 rounded-full transition-all duration-300 ${
              isPlaying 
                ? 'bg-[var(--color-cyber-lime)] text-black shadow-[0_0_20px_rgba(204,255,0,0.6)] scale-105' 
                : 'bg-white text-black hover:bg-gray-200 hover:shadow-[0_0_15px_rgba(255,255,255,0.4)] hover:scale-105'
            }`}
          >
            {isPlaying ? <Pause size={22} className="fill-current" /> : <Play size={22} className="fill-current ml-1" />}
          </button>
          
          <button className="hover:text-[var(--color-cyber-lime)] transition-colors text-gray-400">
            <FastForward size={20} />
          </button>
          
          <div className="h-6 w-px bg-white/10 mx-2"></div>
          
          <div className="flex flex-col items-center">
            <span className="text-[10px] font-mono text-[var(--color-cyber-violet)] uppercase tracking-widest font-bold">BPM</span>
            <span className="text-sm font-bold text-white font-mono tracking-wider">{bpm.toFixed(1)}</span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-[#1A1A1A] px-3 py-1.5 rounded-full border border-white/5">
            <span className="text-[9px] font-mono text-gray-500 uppercase tracking-widest font-bold">ZOOM</span>
            <input type="range" min="10" max="200" value={zoom} onChange={(e) => setZoom(parseFloat(e.target.value))} className="w-24 opacity-80 hover:opacity-100 transition-opacity" />
          </div>
          <button className="p-2 hover:bg-white/5 rounded-full transition-colors group">
            <Maximize2 size={18} className="group-hover:text-[var(--color-cyber-lime)]" />
          </button>
          <button className="p-2 hover:bg-white/5 rounded-full transition-colors group">
            <Settings2 size={18} className="group-hover:text-[var(--color-cyber-violet)]" />
          </button>
        </div>
      </header>

      {/* MAIN WORKSPACE */}
      <div className="flex-1 flex overflow-hidden">
        {/* TRACK HEADERS (LEFT SIDEBAR) */}
        <div className="w-72 bg-[#121212] border-r border-white/5 flex flex-col z-10 shadow-2xl relative">
          <div className="h-10 border-b border-white/5 flex items-center px-4 font-mono text-[10px] text-gray-400 uppercase tracking-widest font-bold bg-[#0A0A0A]">
            Channels ({tracks.length})
          </div>
          
          <div className="flex-1 overflow-y-auto hidden-scrollbar pb-24">
            {tracks.length === 0 ? (
              <div className="p-8 text-center flex flex-col items-center opacity-50 space-y-4">
                 <div className="p-4 rounded-full border border-dashed border-white/20">
                    <Volume2 size={32} className="text-gray-500" />
                 </div>
                 <span className="text-sm font-mono text-gray-500 uppercase tracking-widest">Drop Audio Here</span>
              </div>
            ) : null}
            {tracks.map(track => (
              <TrackHeader key={track.id} track={track} />
            ))}
          </div>
          
          {/* Add Track Button pinned to bottom */}
          <div className="absolute top-[auto] bottom-0 w-full p-4 border-t border-white/5 bg-[#121212] flex items-center justify-center backdrop-blur-md">
            <input 
              type="file" 
              accept="audio/*" 
              className="hidden" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
            />
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="w-full py-2.5 border border-[var(--color-cyber-lime)]/30 text-[var(--color-cyber-lime)] hover:bg-[var(--color-cyber-lime)]/10 hover:shadow-[0_0_15px_rgba(204,255,0,0.2)] hover:border-[var(--color-cyber-lime)] rounded font-mono text-xs uppercase tracking-widest transition-all flex items-center justify-center space-x-2"
            >
              <Plus size={16} /> <span className="font-bold">Import Audio</span>
            </button>
          </div>
        </div>

        {/* TIMELINE / ARRANGEMENT */}
        <div className="flex-1 bg-[#0A0A0A] relative overflow-auto" style={{
            backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)`,
            backgroundSize: `${zoom}px ${zoom}px`
        }}>
          {/* Time Ruler */}
          <div className="h-10 border-b border-white/5 bg-[#1A1A1A]/90 backdrop-blur sticky top-0 z-10 flex items-end" style={{ minWidth: 'max-content' }}>
            {Array.from({length: 200}).map((_, i) => (
              <div key={i} className="flex-none h-3 border-l border-white/10 relative" style={{ width: `${zoom * 2}px` }}>
                <span className="absolute -top-5 left-1 text-[10px] text-gray-600 font-mono pointer-events-none">0:{String(i*2).padStart(2, '0')}</span>
              </div>
            ))}
          </div>
          
          {/* Track Lanes */}
          <div className="relative pb-32" style={{ minWidth: 'max-content' }}>
            {tracks.map(track => (
              <TrackLane key={track.id} track={track} />
            ))}
            
            {/* Realtime Playhead */}
            <div ref={playheadRef} className="absolute top-0 bottom-0 w-[1px] bg-[var(--color-cyber-lime)] shadow-[0_0_12px_rgba(204,255,0,0.9)] z-20 pointer-events-none" style={{ left: '0px', transform: 'translateX(0px)' }}>
              <div className="w-3 h-3 bg-[var(--color-cyber-lime)] rotate-45 transform -translate-x-1/2 -translate-y-1.5 shadow-[0_0_10px_rgba(204,255,0,0.8)] border border-black cursor-ew-resize pointer-events-auto"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Subcomponents

function TrackHeader({ track }: { track: TrackType }) {
  const { updateTrack, removeTrack } = useStore();
  
  return (
    <div className="h-28 border-b border-white/5 p-3 flex flex-col justify-between group hover:bg-white/5 transition-colors relative bg-[#1A1A1A] overflow-hidden">
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: track.color, boxShadow: `0 0 10px ${track.color}40` }}></div>
      <div className="flex items-center justify-between pl-2">
        <div className="flex items-center space-x-2">
          <GripVertical size={14} className="text-gray-600 opacity-0 group-hover:opacity-100 cursor-grab hover:text-white transition-colors" />
          <input 
            type="text" 
            value={track.name.replace(/\.[^/.]+$/, "")} // hide extension
            onChange={(e) => updateTrack(track.id, { name: e.target.value })}
            className="font-bold text-xs text-gray-100 truncate w-32 bg-transparent outline-none border-b border-transparent focus:border-white/20 tracking-wider" 
          />
        </div>
        <div className="flex space-x-1 items-center">
          <button 
            onClick={() => updateTrack(track.id, { muted: !track.muted })}
            className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold transition-all ${track.muted ? 'bg-red-500 text-black shadow-[0_0_10px_rgba(239,68,68,0.5)]' : 'bg-[#2A2A2A] text-gray-400 hover:bg-white/10'}`}
          >
            M
          </button>
          <button 
            onClick={() => updateTrack(track.id, { solo: !track.solo })}
            className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold transition-all ${track.solo ? 'bg-yellow-500 text-black shadow-[0_0_10px_rgba(234,179,8,0.5)]' : 'bg-[#2A2A2A] text-gray-400 hover:bg-white/10'}`}
          >
            S
          </button>
          
          <button onClick={() => removeTrack(track.id)} className="w-6 h-6 rounded flex items-center justify-center text-gray-600 hover:text-red-500 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100 ml-1">
             <Trash2 size={12} />
          </button>
        </div>
      </div>
      
      {/* Controls Container */}
      <div className="pl-2 pr-1 mt-2 space-y-3">
        {/* Pan */}
        <div className="flex items-center space-x-2">
          <span className="text-[9px] font-mono text-gray-500 font-bold w-4">PAN</span>
          <div className="flex-1 h-1 bg-[#0A0A0A] rounded-full overflow-hidden relative">
            <div className="absolute h-full w-[2px] bg-gray-500 left-1/2 transform -translate-x-1/2"></div>
            <input 
              type="range" 
              min="-1" 
              max="1" 
              step="0.01"
              value={track.pan}
              onChange={(e) => updateTrack(track.id, { pan: parseFloat(e.target.value) })}
              className="absolute inset-0 w-full opacity-0 cursor-ew-resize"
            />
            <div 
              className="h-full bg-white/80 absolute rounded-full pointer-events-none" 
              style={{ 
                left: track.pan < 0 ? `${(track.pan + 1) * 50}%` : '50%',
                right: track.pan > 0 ? `${(1 - track.pan) * 50}%` : '50%'
              }}
            ></div>
          </div>
        </div>

        {/* Volume */}
        <div className="flex items-center space-x-2">
          <Volume2 size={10} className="text-gray-500 w-4" />
          <div className="flex-1 h-1.5 bg-[#0A0A0A] rounded-full relative group-hover:bg-black transition-colors">
            <div 
              className="h-full rounded-full transition-all duration-75" 
              style={{ width: `${track.volume * 100}%`, backgroundColor: track.color, boxShadow: `0 0 8px ${track.color}80` }}
            ></div>
            <input 
              type="range" 
              min="0" 
              max="1" 
              step="0.01"
              value={track.volume}
              onChange={(e) => updateTrack(track.id, { volume: parseFloat(e.target.value) })}
              className="absolute inset-0 w-full opacity-0 cursor-ew-resize"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function TrackLane({ track }: { track: TrackType }) {
  const { selectedTrackId, selectTrack, updateTrack, zoom } = useStore();
  const isSelected = selectedTrackId === track.id;

  const pxPerSecond = zoom;
  const duration = track.player?.buffer?.duration || 10;
  const width = duration * pxPerSecond;
  
  return (
    <div className="h-28 border-b border-white/5 flex items-center bg-transparent group relative">
      {/* Waveform Wrapper (Draggable) */}
      <motion.div 
        drag="x"
        dragMomentum={false}
        dragElastic={0}
        onDragEnd={(_, info) => {
          // Snap horizontal offset to new start time (approx calculation)
          const offsetPx = info.offset.x;
          const newStart = Math.max(0, track.startTime + (offsetPx / pxPerSecond));
          updateTrack(track.id, { startTime: newStart });
        }}
        onClick={(e) => { e.stopPropagation(); selectTrack(track.id); }}
        className={`absolute h-[80px] rounded-md backdrop-blur-xl border flex items-center justify-center overflow-hidden transition-colors cursor-pointer shadow-lg hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] ${isSelected ? 'border-[var(--color-cyber-lime)] shadow-[0_0_15px_rgba(204,255,0,0.3)] z-10' : 'border-white/10'}`}
        style={{ left: `${track.startTime * pxPerSecond}px`, width: `${width}px`, backgroundColor: `${track.color}${isSelected ? '25' : '18'}` }}
      >
        <div className="absolute top-1 left-2 text-[9px] font-mono font-bold tracking-widest uppercase opacity-80 truncate max-w-full pr-4 z-10" style={{ color: track.color, textShadow: `0 0 10px ${track.color}, 0 0 20px black` }}>
          {track.name}
        </div>

        {/* TRUE WAVEFORM RENDERER via HTML5 Canvas */}
        <div className="absolute inset-0 w-full h-full pointer-events-none opacity-80">
          {track.player?.buffer.loaded ? (
            <WaveformRenderer buffer={track.player.buffer} color={track.color} />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-[10px] font-mono opacity-50">
               Decodificando...
            </div>
          )}
        </div>
        
      </motion.div>
    </div>
  );
}

// True Waveform renderer interacting with raw Float32Array
function WaveformRenderer({ buffer, color }: { buffer: Tone.ToneAudioBuffer, color: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    if (!canvasRef.current || !buffer.loaded) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Resize correctly
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    const width = canvas.offsetWidth;
    const height = canvas.offsetHeight;
    
    ctx.clearRect(0, 0, width, height);
    
    // Render Peaks (Fast approach)
    const channelData = buffer.getChannelData(0); // L channel
    const step = Math.ceil(channelData.length / width);
    const amp = height / 2;
    
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 4;
    
    for (let i = 0; i < width; i++) {
        let min = 1.0;
        let max = -1.0;
        // Find max and min in this pixel's chunk
        for (let j = 0; j < step; j++) {
            const index = (i * step) + j;
            if (index < channelData.length) {
                const datum = channelData[index];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }
        }
        
        // Draw vertical slice
        const y = (1 + min) * amp;
        const h = Math.max(1, (max - min) * amp);
        
        // Render rect for this pixel column
        ctx.fillRect(i, y, 1, h);
    }
  }, [buffer, color]);
  
  return <canvas ref={canvasRef} className="w-full h-full" />;
}

// Inspector specific panel
function InspectorPanel({ trackId }: { trackId: string }) {
  const { tracks, updateTrack } = useStore();
  const track = tracks.find(t => t.id === trackId);

  if (!track) return null;

  return (
    <div className="p-4 space-y-6 text-sm">
      <div className="flex items-center space-x-3 mb-4 border-b border-white/5 pb-4">
        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: track.color, boxShadow: `0 0 10px ${track.color}80` }}></div>
        <h3 className="font-bold text-white uppercase tracking-wider font-mono truncate">{track.name}</h3>
      </div>

      <div className="space-y-4">
        <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-widest font-bold">FX Rack</h4>
        
        {/* Reverb FX Panel */}
        <div className={`glass-panel p-3 rounded-md space-y-3 relative overflow-hidden group transition-all ${track.fx.reverbOn ? 'border-[var(--color-cyber-violet)] border-white/30' : 'opacity-50'}`}>
          <div className="absolute top-0 left-0 w-1 h-full bg-[var(--color-cyber-violet)] opacity-50"></div>
          <div className="flex justify-between items-center pl-2">
            <span className="font-bold text-xs text-gray-300">VOID REVERB</span>
            <button 
              onClick={() => updateTrack(track.id, { fx: { ...track.fx, reverbOn: !track.fx.reverbOn } })}
              className={`w-8 h-4 rounded-full text-[8px] font-bold text-white flex items-center justify-center transition-colors ${track.fx.reverbOn ? 'bg-[var(--color-cyber-violet)] shadow-[0_0_10px_rgba(102,0,255,0.7)]' : 'bg-[#2A2A2A]'}`}
            >
              {track.fx.reverbOn ? 'ON' : 'OFF'}
            </button>
          </div>
          <div className="pl-2 space-y-2 transition-opacity">
            <div className="flex justify-between text-[10px] font-mono text-gray-400 font-bold">
              <span>MIX</span>
              <span className="text-[var(--color-cyber-violet)]">{Math.round(track.fx.reverbMix * 100)}%</span>
            </div>
            <div className="h-1 bg-black rounded-full relative group-hover:bg-[#1A1A1A] transition-colors">
              <div className="absolute h-full bg-[var(--color-cyber-violet)] rounded-full transition-all duration-75" style={{ width: `${track.fx.reverbMix * 100}%` }}></div>
              <input type="range" min="0" max="1" step="0.01" value={track.fx.reverbMix} onChange={(e) => updateTrack(track.id, { fx: { ...track.fx, reverbMix: parseFloat(e.target.value) } })} className="absolute inset-0 w-full opacity-0 cursor-ew-resize" />
            </div>
            <div className="flex justify-between text-[10px] font-mono text-gray-400 font-bold mt-2">
              <span>ROOM SIZE</span>
              <span className="text-[var(--color-cyber-violet)]">{Math.round(track.fx.reverbSize * 100)}%</span>
            </div>
            <div className="h-1 bg-black rounded-full relative group-hover:bg-[#1A1A1A] transition-colors">
              <div className="absolute h-full bg-[var(--color-cyber-violet)] rounded-full transition-all duration-75" style={{ width: `${track.fx.reverbSize * 100}%` }}></div>
              <input type="range" min="0.1" max="1" step="0.01" value={track.fx.reverbSize} onChange={(e) => updateTrack(track.id, { fx: { ...track.fx, reverbSize: parseFloat(e.target.value) } })} className="absolute inset-0 w-full opacity-0 cursor-ew-resize" />
            </div>
          </div>
        </div>

        {/* PingPong Delay FX Panel */}
        <div className={`glass-panel p-3 rounded-md space-y-3 relative overflow-hidden group transition-all mt-3 ${track.fx.delayOn ? 'border-[var(--color-cyber-lime)] border-white/30' : 'opacity-50'}`}>
          <div className="absolute top-0 left-0 w-1 h-full bg-[var(--color-cyber-lime)] opacity-50"></div>
          <div className="flex justify-between items-center pl-2">
            <span className="font-bold text-xs text-gray-300">CYBER DELAY</span>
            <button 
              onClick={() => updateTrack(track.id, { fx: { ...track.fx, delayOn: !track.fx.delayOn } })}
              className={`w-8 h-4 rounded-full text-[8px] font-bold text-white flex items-center justify-center transition-colors ${track.fx.delayOn ? 'bg-[var(--color-cyber-lime)] text-black shadow-[0_0_10px_rgba(204,255,0,0.7)]' : 'bg-[#2A2A2A]'}`}
            >
              {track.fx.delayOn ? 'ON' : 'OFF'}
            </button>
          </div>
          
          <div className="pl-2 space-y-2 transition-opacity">
            <div className="flex justify-between text-[10px] font-mono text-gray-400 font-bold">
              <span>MIX</span>
              <span className="text-[var(--color-cyber-lime)]">{Math.round(track.fx.delayMix * 100)}%</span>
            </div>
            <div className="h-1 bg-black rounded-full relative group-hover:bg-[#1A1A1A] transition-colors">
              <div className="absolute h-full bg-[var(--color-cyber-lime)] rounded-full transition-all duration-75" style={{ width: `${track.fx.delayMix * 100}%` }}></div>
              <input type="range" min="0" max="1" step="0.01" value={track.fx.delayMix} onChange={(e) => updateTrack(track.id, { fx: { ...track.fx, delayMix: parseFloat(e.target.value) } })} className="absolute inset-0 w-full opacity-0 cursor-ew-resize" />
            </div>
          </div>
        </div>

        {/* Track Properties Info */}
        <div className="pt-6 border-t border-white/5 space-y-2 font-mono text-[10px]">
           <div className="flex justify-between"><span className="text-gray-500">START</span><span className="text-white">{(track.startTime || 0).toFixed(2)}s</span></div>
           <div className="flex justify-between"><span className="text-gray-500">LENGTH</span><span className="text-white">{(track.duration || 0).toFixed(2)}s</span></div>
           <div className="flex justify-between"><span className="text-gray-500">FORMAT</span><span className="text-white">WAV 44.1kHz</span></div>
        </div>
      </div>
    </div>
  );
}
