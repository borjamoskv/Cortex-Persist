import { GripVertical, Volume2, Trash2 } from 'lucide-react';
import { useStore, type Track as TrackType } from '../../store';

export function TrackHeader({ track }: { track: TrackType }) {
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
