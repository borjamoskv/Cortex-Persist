import { create } from 'zustand';
import * as Tone from 'tone';

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
  
  // Actions
  addTrack: (file?: File) => Promise<void>;
  removeTrack: (id: string) => void;
  updateTrack: (id: string, updates: Partial<Track>) => void;
  selectTrack: (id: string | null) => void;
  splitTrack: (id: string, splitTime: number) => void;
  togglePlay: () => Promise<void>;
  setTime: (time: number) => void;
  setMasterVolume: (vol: number) => void;
  setBpm: (bpm: number) => void;
  setZoom: (z: number) => void;
}

export const useStore = create<WebAudioStore>((set, get) => ({
  tracks: [],
  selectedTrackId: null,
  isPlaying: false,
  currentTime: 0,
  masterVolume: 1,
  bpm: 120,
  zoom: 50,

  addTrack: async (file) => {
    await Tone.start(); // Ensure audio context is ready
    
    let url = null;
    let duration = 0;
    let player = null;
    
    const reverb = new Tone.Freeverb({ roomSize: 0.8, wet: 0 });
    const delay = new Tone.PingPongDelay({ delayTime: "8n", feedback: 0.4, wet: 0 });
    const channel = new Tone.Channel(0, 0).toDestination();

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
      // We don't start here, we wait for onload if it's a file
    }

    set((state) => ({
      tracks: [...state.tracks, {
        id: Math.random().toString(36).substr(2, 9),
        name: file ? file.name : `Track ${state.tracks.length + 1}`,
        url,
        volume: 0.8,
        pan: 0,
        muted: false,
        solo: false,
        color: state.tracks.length % 2 === 0 ? '#CCFF00' : '#6600FF',
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
    
    // Create new player for the sliced portion (sharing same audiourl)
    const newPlayer = new Tone.Player({ url: track.url || undefined });
    const newReverb = new Tone.Freeverb({ roomSize: track.fx.reverbSize, wet: track.fx.reverbOn ? track.fx.reverbMix : 0 });
    const newDelay = new Tone.PingPongDelay({ delayTime: "8n", feedback: 0.4, wet: track.fx.delayOn ? track.fx.delayMix : 0 });
    const newChannel = new Tone.Channel(track.pan, Tone.gainToDb(track.volume)).toDestination();
    newChannel.mute = track.muted;
    newChannel.solo = track.solo;
    
    newPlayer.chain(newReverb, newDelay, newChannel);
    
    const newSourceOffset = track.sourceOffset + timeIntoTrack;
    const newDuration = track.duration - timeIntoTrack;
    const newStartTime = splitTime;
    
    // Schedule the new player
    // Note: To avoid errors, we do this asynchronously or immediately if buffer is already loaded from Cache.
    // Tone.js auto-caches URL buffers.
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
    // Shrink original track
    newTracks[trackIndex] = { ...track, duration: origUpdatedDuration };
    // Insert new track right after
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
    Tone.Destination.volume.value = Tone.gainToDb(vol);
    set({ masterVolume: vol });
  },
  
  setBpm: (bpm) => {
    Tone.Transport.bpm.value = bpm;
    set({ bpm });
  },

  setZoom: (z) => set({ zoom: z })
}));
