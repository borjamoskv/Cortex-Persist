import { useEffect, useRef } from 'react';
import { Play, Pause, FastForward, Rewind, Settings2, Plus, GripVertical, Volume2, Maximize2 } from 'lucide-react';
import { useStore } from './store';

export default function App() {
  const { tracks, isPlaying, togglePlay, addTrack } = useStore();

  return (
    <div className="h-screen w-screen flex flex-col bg-noir-900 text-gray-300 font-sans selection:bg-cyber-lime selection:text-black">
      {/* HEADER / TRANSPORT */}
      <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-[#0A0A0A] z-20">
        <div className="flex items-center space-x-4">
          <div className="text-2xl font-black tracking-tighter text-white uppercase drop-shadow-[0_0_10px_rgba(204,255,0,0.2)]">
            SONIC<span className="text-[var(--color-cyber-lime)]">_SUPREME</span>
          </div>
        </div>

        {/* TRANSPORT CONTROLS */}
        <div className="flex items-center space-x-6 glass-panel px-6 py-2 rounded-full border border-white/10 shadow-lg">
          <button className="hover:text-[var(--color-cyber-lime)] transition-colors text-gray-400">
            <Rewind size={20} />
          </button>
          <button 
            onClick={togglePlay}
            className={`flex items-center justify-center h-10 w-10 rounded-full transition-all ${
              isPlaying 
                ? 'bg-[var(--color-cyber-lime)] text-black shadow-[0_0_20px_rgba(204,255,0,0.6)]' 
                : 'bg-white text-black hover:bg-gray-200 hover:shadow-[0_0_15px_rgba(255,255,255,0.4)]'
            }`}
          >
            {isPlaying ? <Pause size={20} className="fill-current" /> : <Play size={20} className="fill-current ml-0.5" />}
          </button>
          <button className="hover:text-[var(--color-cyber-lime)] transition-colors text-gray-400">
            <FastForward size={20} />
          </button>
          
          <div className="h-6 w-px bg-white/10 mx-2"></div>
          
          <div className="flex flex-col items-center">
            <span className="text-[10px] font-mono text-[var(--color-cyber-violet)] uppercase tracking-widest font-bold">BPM</span>
            <span className="text-sm font-bold text-white font-mono tracking-wider">124.0</span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
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
          <div className="h-10 border-b border-white/5 flex items-center px-4 font-mono text-[10px] text-gray-500 uppercase tracking-widest font-bold bg-[#0A0A0A]">
            Channels
          </div>
          <div className="flex-1 overflow-y-auto hidden-scrollbar pb-24">
            {tracks.length === 0 ? (
              <div className="p-8 text-center text-sm font-mono text-gray-600">No tracks loaded</div>
            ) : null}
            {tracks.map(track => (
              <TrackHeader key={track.id} track={track} />
            ))}
          </div>
          
          {/* Add Track Button pinned to bottom */}
          <div className="absolute top-[auto] bottom-0 w-full p-4 border-t border-white/5 bg-[#121212] flex items-center justify-center">
            <button 
              onClick={() => addTrack({})}
              className="w-full py-2.5 border border-[var(--color-cyber-lime)]/30 text-[var(--color-cyber-lime)] hover:bg-[var(--color-cyber-lime)]/10 hover:shadow-[0_0_15px_rgba(204,255,0,0.2)] rounded font-mono text-xs uppercase tracking-widest transition-all flex items-center justify-center space-x-2"
            >
              <Plus size={16} /> <span className="font-bold">Add Track</span>
            </button>
          </div>
        </div>

        {/* TIMELINE / ARRANGEMENT */}
        <div className="flex-1 bg-[#0A0A0A] relative overflow-auto" style={{
            backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)`,
            backgroundSize: `48px 48px`
        }}>
          {/* Time Ruler */}
          <div className="h-10 border-b border-white/5 bg-[#1A1A1A]/90 backdrop-blur sticky top-0 z-0 flex items-end px-4">
            {/* Simple ruler markers */}
            {Array.from({length: 100}).map((_, i) => (
              <div key={i} className="flex-none w-24 h-3 border-l border-white/10 relative">
                <span className="absolute -top-5 left-1 text-[10px] text-gray-600 font-mono">0:{String(i*5).padStart(2, '0')}</span>
              </div>
            ))}
          </div>
          
          {/* Track Lanes */}
          <div className="relative">
            {tracks.map(track => (
              <TrackLane key={track.id} track={track} />
            ))}
            
            {/* Playhead */}
            <div className="absolute top-0 bottom-0 w-[2px] bg-[var(--color-cyber-lime)] shadow-[0_0_12px_rgba(204,255,0,0.9)] z-20 pointer-events-none" style={{ left: '250px' }}>
              <div className="w-4 h-4 bg-[var(--color-cyber-lime)] rotate-45 transform -translate-x-1/2 -translate-y-2 shadow-[0_0_10px_rgba(204,255,0,0.8)] border-2 border-black"></div>
            </div>
          </div>
        </div>
        
        {/* INSPECTOR PANEL (RIGHT SIDEBAR) */}
        <div className="w-80 bg-[#121212] border-l border-white/5 flex flex-col z-10 hidden xl:flex">
          <div className="h-10 border-b border-white/5 flex items-center px-4 font-mono text-[10px] text-gray-500 uppercase tracking-widest font-bold bg-[#0A0A0A]">
            Inspector
          </div>
          <div className="flex-1 p-6 flex flex-col items-center justify-center text-gray-600">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-6">
              <Settings2 size={24} className="opacity-50" />
            </div>
            <p className="text-xs font-mono uppercase tracking-widest text-center">Select a region<br/>to edit properties</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Subcomponents

function TrackHeader({ track }: { track: any }) {
  const { updateTrack } = useStore();
  
  return (
    <div className="h-28 border-b border-white/5 p-3 flex flex-col justify-between group hover:bg-white/5 transition-colors relative bg-[#1A1A1A]">
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: track.color }}></div>
      <div className="flex items-center justify-between pl-2">
        <div className="flex items-center space-x-2">
          <GripVertical size={14} className="text-gray-600 opacity-0 group-hover:opacity-100 cursor-grab" />
          <input 
            type="text" 
            value={track.name}
            onChange={(e) => updateTrack(track.id, { name: e.target.value })}
            className="font-bold text-xs text-gray-200 truncate w-24 bg-transparent outline-none border-b border-transparent focus:border-white/20 uppercase tracking-wider" 
          />
        </div>
        <div className="flex space-x-1">
          <button 
            onClick={() => updateTrack(track.id, { muted: !track.muted })}
            className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold transition-all ${track.muted ? 'bg-red-500/20 text-red-500 border border-red-500/50' : 'bg-[#2A2A2A] text-gray-400 hover:bg-white/10'}`}
          >
            M
          </button>
          <button 
            onClick={() => updateTrack(track.id, { solo: !track.solo })}
            className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold transition-all ${track.solo ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/50' : 'bg-[#2A2A2A] text-gray-400 hover:bg-white/10'}`}
          >
            S
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
            {/* Visual indicator (since actual input is invisible) */}
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
              className="h-full rounded-full transition-all" 
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

function TrackLane({ track }: { track: any }) {
  return (
    <div className="h-28 border-b border-white/5 flex items-center bg-transparent group relative">
      {/* Ghost waveform wrapper (mocking an audio region) */}
      <div 
        className="absolute h-[80px] rounded backdrop-blur-md border border-white/10 flex items-center justify-center overflow-hidden transition-all hover:border-white/30 cursor-pointer shadow-lg" 
        style={{ left: '120px', width: '380px', backgroundColor: `${track.color}15` }}
      >
        {/* Track Label overlaid */}
        <div className="absolute top-1 left-2 text-[9px] font-mono font-bold tracking-widest uppercase opacity-70" style={{ color: track.color }}>
          Audio Region.wav
        </div>

        {/* Mock Waveform */}
        <div className="w-full flex items-center h-12 space-x-[1px] px-1 opacity-80 mt-2">
           {Array.from({length: 120}).map((_, i) => {
             // Generate somewhat organic looking waveform
             const centerDist = Math.abs(60 - i) / 60;
             const h = Math.random() * (1 - centerDist) * 100 + Math.random() * 20;
             return (
               <div 
                 key={i} 
                 className="flex-1 rounded-sm" 
                 style={{ 
                   height: `${Math.max(4, h)}%`,
                   backgroundColor: track.color,
                   boxShadow: `0 0 4px ${track.color}40`
                 }}
               ></div>
             );
           })}
        </div>
        
        {/* Edge drag handles */}
        <div className="absolute left-0 top-0 bottom-0 w-2 hover:bg-white/20 cursor-col-resize transition-colors"></div>
        <div className="absolute right-0 top-0 bottom-0 w-2 hover:bg-white/20 cursor-col-resize transition-colors"></div>
      </div>
    </div>
  );
}
