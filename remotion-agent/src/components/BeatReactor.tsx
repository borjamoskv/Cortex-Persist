import React, {createContext, useContext, useMemo} from 'react';
import {useCurrentFrame} from 'remotion';
import {BEAT_FRAMES, BAR_FRAMES} from '../lyrics';

interface BeatState {
  frame: number;
  /** 0→1 within current beat */
  beatPhase: number;
  /** 0→1 within current bar (4 beats) */
  barPhase: number;
  /** Eased pulse: 1 at beat start, decays to 0 */
  beatPulse: number;
  /** Stronger pulse on bar boundaries */
  barPulse: number;
  /** Beat index */
  beatIndex: number;
  /** Bar index */
  barIndex: number;
  /** True for first 3 frames of a beat */
  isOnBeat: boolean;
  /** True for first 3 frames of a bar */
  isOnBar: boolean;
}

const BeatContext = createContext<BeatState>({
  frame: 0,
  beatPhase: 0,
  barPhase: 0,
  beatPulse: 0,
  barPulse: 0,
  beatIndex: 0,
  barIndex: 0,
  isOnBeat: false,
  isOnBar: false,
});

export const useBeat = () => useContext(BeatContext);

/** Exponential decay: sharp attack, smooth release */
const decayPulse = (phase: number, sharpness = 6): number => {
  return Math.exp(-phase * sharpness);
};

export const BeatReactor: React.FC<{children: React.ReactNode}> = ({children}) => {
  const frame = useCurrentFrame();

  const state = useMemo<BeatState>(() => {
    const beatPhase = (frame % BEAT_FRAMES) / BEAT_FRAMES;
    const barPhase = (frame % BAR_FRAMES) / BAR_FRAMES;
    const beatIndex = Math.floor(frame / BEAT_FRAMES);
    const barIndex = Math.floor(frame / BAR_FRAMES);
    const beatPulse = decayPulse(beatPhase, 5);
    const barPulse = decayPulse(barPhase * 4, 3); // Slower decay for bars
    const isOnBeat = (frame % Math.round(BEAT_FRAMES)) < 3;
    const isOnBar = (frame % Math.round(BAR_FRAMES)) < 3;

    return {frame, beatPhase, barPhase, beatPulse, barPulse, beatIndex, barIndex, isOnBeat, isOnBar};
  }, [frame]);

  return <BeatContext.Provider value={state}>{children}</BeatContext.Provider>;
};
