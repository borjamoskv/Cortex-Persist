import { create } from 'zustand';

export interface Track {
  id: string;
  name: string;
  url: string | null;
  volume: number;
  pan: number;
  muted: boolean;
  solo: boolean;
  color: string;
  startTime: number;
  duration: number;
}

interface WebAudioStore {
  tracks: Track[];
  isPlaying: boolean;
  currentTime: number;
  masterVolume: number;
  bpm: number;
  
  // Actions
  addTrack: (track: Partial<Track>) => void;
  removeTrack: (id: string) => void;
  updateTrack: (id: string, updates: Partial<Track>) => void;
  togglePlay: () => void;
  setTime: (time: number) => void;
  setMasterVolume: (vol: number) => void;
  setBpm: (bpm: number) => void;
}

export const useStore = create<WebAudioStore>((set) => ({
  tracks: [],
  isPlaying: false,
  currentTime: 0,
  masterVolume: 1,
  bpm: 120,

  addTrack: (t) => set((state) => ({
    tracks: [...state.tracks, {
      id: Math.random().toString(36).substr(2, 9),
      name: `Track ${state.tracks.length + 1}`,
      url: null,
      volume: 1,
      pan: 0,
      muted: false,
      solo: false,
      color: state.tracks.length % 2 === 0 ? '#CCFF00' : '#6600FF',
      startTime: 0,
      duration: 0,
      ...t
    }]
  })),

  removeTrack: (id) => set((state) => ({
    tracks: state.tracks.filter(t => t.id !== id)
  })),

  updateTrack: (id, updates) => set((state) => ({
    tracks: state.tracks.map(t => t.id === id ? { ...t, ...updates } : t)
  })),

  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  
  setTime: (time) => set({ currentTime: time }),
  
  setMasterVolume: (vol) => set({ masterVolume: vol }),
  
  setBpm: (bpm) => set({ bpm })
}));
