import { useStore, Track as TrackType } from '../../store';

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

export function InspectorPanel({ track }: { track: TrackType }) {
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
