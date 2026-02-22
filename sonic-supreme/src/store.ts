import { create } from 'zustand';
import * as Tone from 'tone';

// ─── MASTER BUS (Singleton Audio Nodes) ─────────────────────────────
export const masterCompressor = new Tone.Compressor({ threshold: -24, ratio: 4 });
export const masterEQ = new Tone.EQ3({ low: 0, mid: 0, high: 0 });
export const masterAnalyzer = new Tone.Analyser('fft', 64);
export const masterMeter = new Tone.Meter({ smoothing: 0.8 });
export const masterBus = new Tone.Channel(0, 0);

// Chain: masterBus → EQ → Compressor → Analyzer + Meter → Destination
masterBus.chain(masterEQ, masterCompressor, masterAnalyzer, masterMeter, Tone.getDestination());

// ─── TRACK COLOR PALETTE ────────────────────────────────────────────
const TRACK_COLORS = [
  '#CCFF00', // Cyber Lime
  '#6600FF', // Electric Violet
  '#FF3366', // Neon Rose
  '#00D4FF', // Cyan Pulse
  '#FF9500', // Amber Core
  '#06D6A0', // Emerald Synth
  '#FF006E', // Magenta Rush
  '#3A86FF', // Cobalt Wave
];

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
  sourceOffset: number;
  
  // Audio Nodes
  player: Tone.Player | null;
  channel: Tone.Channel | null;
  reverb: Tone.Freeverb | null;
  delay: Tone.PingPongDelay | null;
  
  // FX State parameters
  fx: {
    reverbOn: boolean;
    reverbMix: number;
    reverbSize: number;
    delayOn: boolean;
    delayMix: number;
  };
}

interface WebAudioStore {
  tracks: Track[];
  selectedTrackId: string | null;
  isPlaying: boolean;
  currentTime: number;
  masterVolume: number;
  bpm: number;
  zoom: number; // px per second
  
  // Master Processing Node states
  masterFx: {
    eqLow: number;
    eqMid: number;
    eqHigh: number;
    compThreshold: number;
    compRatio: number;
  };
  
  // Actions
  addTrack: (file?: File) => Promise<void>;
  removeTrack: (id: string) => void;
  updateTrack: (id: string, updates: Partial<Track>) => void;
  updateMasterFx: (updates: Partial<WebAudioStore['masterFx']>) => void;
  selectTrack: (id: string | null) => void;
  splitTrack: (id: string, splitTime: number) => void;
  togglePlay: () => Promise<void>;
  setTime: (time: number) => void;
  setMasterVolume: (vol: number) => void;
  setBpm: (bpm: number) => void;
  setZoom: (z: number) => void;
  
  // Export
  isExporting: boolean;
  exportAudio: () => Promise<void>;
}

export const useStore = create<WebAudioStore>((set, get) => ({
  tracks: [],
  selectedTrackId: null,
  isPlaying: false,
  currentTime: 0,
  masterVolume: 1,
  bpm: 120,
  zoom: 50,
  masterFx: {
    eqLow: 0,
    eqMid: 0,
    eqHigh: 0,
    compThreshold: -24,
    compRatio: 4,
  },

  addTrack: async (file) => {
    await Tone.start(); // Ensure audio context is ready
    
    let url: string | null = null;
    let duration = 0;
    let player: Tone.Player | null = null;
    
    const reverb = new Tone.Freeverb({ roomSize: 0.8, wet: 0 });
    const delay = new Tone.PingPongDelay({ delayTime: "8n", feedback: 0.4, wet: 0 });
    const channel = new Tone.Channel(0, 0).connect(masterBus);

    if (file) {
      url = URL.createObjectURL(file);
      player = new Tone.Player({
        url,
        onload: () => {
          duration = player?.buffer.duration || 0;
          set((state) => ({
            tracks: state.tracks.map(t => t.url === url ? { ...t, duration } : t)
          }));
          // Sync correctly after buffer load
          player?.sync().start(0, 0, duration);
        }
      });
      player.chain(reverb, delay, channel);
    }

    const colorIndex = get().tracks.length % TRACK_COLORS.length;

    set((state) => ({
      tracks: [...state.tracks, {
        id: Math.random().toString(36).substr(2, 9),
        name: file ? file.name : `Track ${state.tracks.length + 1}`,
        url,
        volume: 0.8,
        pan: 0,
        muted: false,
        solo: false,
        color: TRACK_COLORS[colorIndex],
        startTime: 0,
        duration,
        sourceOffset: 0,
        player,
        channel,
        reverb,
        delay,
        fx: {
          reverbOn: false,
          reverbMix: 0.4,
          reverbSize: 0.8,
          delayOn: false,
          delayMix: 0.3
        }
      }]
    }));
  },

  removeTrack: (id) => {
    const track = get().tracks.find(t => t.id === id);
    if (track) {
      track.player?.dispose();
      track.channel?.dispose();
      track.reverb?.dispose();
      track.delay?.dispose();
    }
    set((state) => ({
      tracks: state.tracks.filter(t => t.id !== id),
      selectedTrackId: state.selectedTrackId === id ? null : state.selectedTrackId
    }));
  },

  selectTrack: (id) => set({ selectedTrackId: id }),

  updateTrack: (id, updates) => set((state) => {
    return {
      tracks: state.tracks.map(t => {
        if (t.id === id) {
          const updated = { ...t, ...updates };
          
          // Update Transport Sync if timing properties change
          if ((updates.startTime !== undefined || updates.sourceOffset !== undefined || updates.duration !== undefined) && updated.player) {
             updated.player.unsync();
             updated.player.sync().start(updated.startTime, updated.sourceOffset, updated.duration);
          }
          
          // Apply Tone.js core signal updates
          if (updated.channel) {
            if (updates.volume !== undefined) {
              updated.channel.volume.value = Tone.gainToDb(updates.volume);
            }
            if (updates.pan !== undefined) updated.channel.pan.value = updates.pan;
            if (updates.muted !== undefined) updated.channel.mute = updates.muted;
            if (updates.solo !== undefined) updated.channel.solo = updates.solo;
          }
          
          // Apply digital FX routing updates
          if (updates.fx && updated.reverb && updated.delay) {
            const newFx = { ...t.fx, ...updates.fx };
            updated.fx = newFx;
            
            // Reverb
            updated.reverb.wet.value = newFx.reverbOn ? newFx.reverbMix : 0;
            updated.reverb.roomSize.value = newFx.reverbSize;
            
            // Delay
            updated.delay.wet.value = newFx.delayOn ? newFx.delayMix : 0;
          }
          
          return updated;
        }
        return t;
      })
    };
  }),

  splitTrack: (id, splitTime) => set((state) => {
    const trackIndex = state.tracks.findIndex(t => t.id === id);
    if (trackIndex === -1) return state;
    
    const track = state.tracks[trackIndex];
    // Check if splitTime is within the track's timeline region boundaries
    if (splitTime <= track.startTime || splitTime >= track.startTime + track.duration) {
      return state; // Nothing to cut
    }
    
    const timeIntoTrack = splitTime - track.startTime;
    
    // Create new player for the sliced portion (sharing same audio url)
    const newPlayer = new Tone.Player({ url: track.url || undefined });
    const newReverb = new Tone.Freeverb({ roomSize: track.fx.reverbSize, wet: track.fx.reverbOn ? track.fx.reverbMix : 0 });
    const newDelay = new Tone.PingPongDelay({ delayTime: "8n", feedback: 0.4, wet: track.fx.delayOn ? track.fx.delayMix : 0 });
    const newChannel = new Tone.Channel(track.pan, Tone.gainToDb(track.volume)).connect(masterBus);
    newChannel.mute = track.muted;
    newChannel.solo = track.solo;
    
    newPlayer.chain(newReverb, newDelay, newChannel);
    
    const newSourceOffset = track.sourceOffset + timeIntoTrack;
    const newDuration = track.duration - timeIntoTrack;
    const newStartTime = splitTime;
    
    newPlayer.sync().start(newStartTime, newSourceOffset, newDuration);
    
    // Update original track duration
    const origUpdatedDuration = timeIntoTrack;
    track.player?.unsync();
    track.player?.sync().start(track.startTime, track.sourceOffset, origUpdatedDuration);
    
    const newTrack: Track = {
      ...track,
      id: Math.random().toString(36).substr(2, 9),
      name: `${track.name} (Cut)`,
      startTime: newStartTime,
      sourceOffset: newSourceOffset,
      duration: newDuration,
      player: newPlayer,
      channel: newChannel,
      reverb: newReverb,
      delay: newDelay,
    };
    
    const newTracks = [...state.tracks];
    newTracks[trackIndex] = { ...track, duration: origUpdatedDuration };
    newTracks.splice(trackIndex + 1, 0, newTrack);
    
    return { tracks: newTracks };
  }),

  togglePlay: async () => {
    await Tone.start();
    set((state) => {
      if (state.isPlaying) {
        Tone.Transport.pause();
      } else {
        Tone.Transport.start();
      }
      return { isPlaying: !state.isPlaying };
    });
  },
  
  setTime: (time) => {
    Tone.Transport.seconds = time;
    set({ currentTime: time });
  },
  
  setMasterVolume: (vol) => {
    masterBus.volume.value = Tone.gainToDb(vol);
    set({ masterVolume: vol });
  },
  
  setBpm: (bpm) => {
    Tone.Transport.bpm.value = bpm;
    set({ bpm });
  },

  setZoom: (z) => set({ zoom: z }),

  updateMasterFx: (updates) => set((state) => {
    const newFx = { ...state.masterFx, ...updates };
    
    if (updates.eqLow !== undefined) masterEQ.low.value = updates.eqLow;
    if (updates.eqMid !== undefined) masterEQ.mid.value = updates.eqMid;
    if (updates.eqHigh !== undefined) masterEQ.high.value = updates.eqHigh;
    if (updates.compThreshold !== undefined) masterCompressor.threshold.value = updates.compThreshold;
    if (updates.compRatio !== undefined) masterCompressor.ratio.value = updates.compRatio;
    
    return { masterFx: newFx };
  }),
  
  isExporting: false,
  exportAudio: async () => {
    const { tracks } = get();
    if (tracks.length === 0) return;
    
    set({ isExporting: true });
    
    try {
      let maxDuration = 0;
      tracks.forEach(t => {
        const end = t.startTime + t.duration;
        if (end > maxDuration) maxDuration = end;
      });
      maxDuration += 2; // reverb/delay tail
      
      const recorder = new Tone.Recorder();
      masterBus.connect(recorder);
      
      await Tone.start();
      recorder.start();
      
      const prevPosition = Tone.Transport.seconds;
      const wasPlaying = get().isPlaying;
      
      if (wasPlaying) Tone.Transport.pause();
      Tone.Transport.seconds = 0;
      Tone.Transport.start();
      
      await new Promise(resolve => setTimeout(resolve, maxDuration * 1000));
      
      Tone.Transport.stop();
      Tone.Transport.seconds = prevPosition;
      if (wasPlaying) Tone.Transport.start();
      
      const recording = await recorder.stop();
      const url = URL.createObjectURL(recording);
      
      const anchor = document.createElement("a");
      anchor.download = "SonicSupreme_Bounce.webm";
      anchor.href = url;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      masterBus.disconnect(recorder);
    } catch (e) {
      console.error('Export failed:', e);
    } finally {
      set({ isExporting: false });
    }
  }
}));
