import { motion } from 'framer-motion';
import { useStore, Track as TrackType } from '../../store';
import { WaveformRenderer } from './WaveformRenderer';

export function TrackLane({ track }: { track: TrackType }) {
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
