import { motion } from 'framer-motion';
import { useStore } from '../../store';

export function MasterFxDrawer({ onClose }: { onClose: () => void }) {
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
              <input type="range" min="-20" max="20" step="0.5" value={masterFx[key]} onChange={e => updateMasterFx({ [key]: parseFloat(e.target.value) })} className="w-16 h-1" aria-label={lbl} />
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
            <input type="range" min="-60" max="0" step="0.5" value={masterFx.compThreshold} onChange={e => updateMasterFx({ compThreshold: parseFloat(e.target.value) })} className="w-20 h-1" aria-label="Compressor Threshold" />
            <span className="text-[8px] font-mono text-gray-400">{masterFx.compThreshold.toFixed(1)}dB</span>
          </div>
          <div className="flex flex-col items-center space-y-1">
            <span className="text-[8px] font-mono text-gray-500">RATIO</span>
            <input type="range" min="1" max="20" step="0.5" value={masterFx.compRatio} onChange={e => updateMasterFx({ compRatio: parseFloat(e.target.value) })} className="w-16 h-1" aria-label="Compressor Ratio" />
            <span className="text-[8px] font-mono text-gray-400">{masterFx.compRatio.toFixed(1)}:1</span>
          </div>
        </div>

        <button onClick={onClose} className="ml-auto text-gray-600 hover:text-[var(--color-cyber-lime)] font-mono text-xs transition-colors">✕</button>
      </div>
    </motion.div>
  );
}
