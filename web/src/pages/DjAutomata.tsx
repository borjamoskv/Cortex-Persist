import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import './djAutomata.css';

/* ═══════════════════════════════════════════════════════
   DJ AUTOMATA — Autonomous DJ Visualizer
   Web Audio API synth + real-time visualizer + auto-mix
   ═══════════════════════════════════════════════════════ */

// ── Track database (synthesized patterns) ──
const TRACKS = [
  { name: 'SOVEREIGN PULSE', artist: 'AUTOMATA', bpm: 128, key: 'Am' },
  { name: 'BYZANTINE DRIFT', artist: 'AUTOMATA', bpm: 130, key: 'Cm' },
  { name: 'ENTROPY GATE', artist: 'AUTOMATA', bpm: 126, key: 'Dm' },
  { name: 'LEDGER HYMN', artist: 'AUTOMATA', bpm: 132, key: 'Em' },
  { name: 'ZERO TRUST', artist: 'AUTOMATA', bpm: 128, key: 'Fm' },
  { name: 'HASH CHAIN', artist: 'AUTOMATA', bpm: 134, key: 'Gm' },
  { name: 'CORTEX NOIR', artist: 'AUTOMATA', bpm: 125, key: 'Bbm' },
  { name: 'SWARM SIGNAL', artist: 'AUTOMATA', bpm: 130, key: 'Ebm' },
];

// ── Console log entry ──
interface ConsoleEntry {
  time: string;
  tag: string;
  tagClass: string;
  message: string;
}

// ── Deck state ──
interface DeckState {
  track: typeof TRACKS[0];
  status: 'playing' | 'idle' | 'syncing';
  progress: number;
}

// ── Audio Synth Engine ──
class DjSynthEngine {
  private ctx: AudioContext;
  private analyser: AnalyserNode;
  private masterGain: GainNode;
  private deckAGain: GainNode;
  private deckBGain: GainNode;
  private intervalIds: number[] = [];
  private oscillators: OscillatorNode[] = [];

  constructor() {
    this.ctx = new AudioContext();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.smoothingTimeConstant = 0.7;

    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 0.35;
    this.masterGain.connect(this.analyser);
    this.analyser.connect(this.ctx.destination);

    this.deckAGain = this.ctx.createGain();
    this.deckAGain.gain.value = 1;
    this.deckAGain.connect(this.masterGain);

    this.deckBGain = this.ctx.createGain();
    this.deckBGain.gain.value = 0;
    this.deckBGain.connect(this.masterGain);
  }

  get analyserNode() { return this.analyser; }
  get context() { return this.ctx; }

  // Crossfade A↔B (0 = full A, 1 = full B)
  setCrossfade(value: number) {
    this.deckAGain.gain.setTargetAtTime(1 - value, this.ctx.currentTime, 0.1);
    this.deckBGain.gain.setTargetAtTime(value, this.ctx.currentTime, 0.1);
  }

  // Start synth pattern for a deck
  startPattern(deck: 'A' | 'B', bpm: number) {
    const gain = deck === 'A' ? this.deckAGain : this.deckBGain;
    const beatInterval = 60000 / bpm;

    // ── Kick drum (sine wave with pitch envelope) ──
    const kickId = window.setInterval(() => {
      const osc = this.ctx.createOscillator();
      const kickGain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(150, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(30, this.ctx.currentTime + 0.12);
      kickGain.gain.setValueAtTime(0.8, this.ctx.currentTime);
      kickGain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.15);
      osc.connect(kickGain);
      kickGain.connect(gain);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.15);
    }, beatInterval);

    // ── Hi-hat (noise burst) ──
    const hatId = window.setInterval(() => {
      const bufferSize = this.ctx.sampleRate * 0.03;
      const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * 0.3;
      }
      const noise = this.ctx.createBufferSource();
      noise.buffer = buffer;
      const hatGain = this.ctx.createGain();
      hatGain.gain.setValueAtTime(0.15, this.ctx.currentTime);
      hatGain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.04);

      const hipass = this.ctx.createBiquadFilter();
      hipass.type = 'highpass';
      hipass.frequency.value = 8000;

      noise.connect(hipass);
      hipass.connect(hatGain);
      hatGain.connect(gain);
      noise.start();
    }, beatInterval / 2);

    // ── Bass line (sawtooth) ──
    const bassNotes = [55, 55, 73.42, 65.41]; // A1, A1, D2, C2
    let bassIndex = 0;
    const bassId = window.setInterval(() => {
      const osc = this.ctx.createOscillator();
      const bassGain = this.ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.value = bassNotes[bassIndex % bassNotes.length];
      bassIndex++;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = 400;
      filter.Q.value = 8;

      bassGain.gain.setValueAtTime(0.2, this.ctx.currentTime);
      bassGain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.2);

      osc.connect(filter);
      filter.connect(bassGain);
      bassGain.connect(gain);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.25);
    }, beatInterval);

    // ── Ambient pad (detuned saws) ──
    const padOsc1 = this.ctx.createOscillator();
    const padOsc2 = this.ctx.createOscillator();
    const padGain = this.ctx.createGain();
    const padFilter = this.ctx.createBiquadFilter();

    padOsc1.type = 'sawtooth';
    padOsc1.frequency.value = 220;
    padOsc2.type = 'sawtooth';
    padOsc2.frequency.value = 220.5; // Slight detune

    padFilter.type = 'lowpass';
    padFilter.frequency.value = 800;
    padGain.gain.value = 0.04;

    padOsc1.connect(padFilter);
    padOsc2.connect(padFilter);
    padFilter.connect(padGain);
    padGain.connect(gain);
    padOsc1.start();
    padOsc2.start();

    this.oscillators.push(padOsc1, padOsc2);
    this.intervalIds.push(kickId, hatId, bassId);
  }

  // Get frequency data
  getFrequencyData(): Uint8Array {
    const data = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(data);
    return data;
  }

  // Get waveform data
  getWaveformData(): Uint8Array {
    const data = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteTimeDomainData(data);
    return data;
  }

  async resume() {
    if (this.ctx.state === 'suspended') {
      await this.ctx.resume();
    }
  }

  destroy() {
    this.intervalIds.forEach(id => clearInterval(id));
    this.oscillators.forEach(osc => {
      try { osc.stop(); } catch { /* already stopped */ }
    });
    this.ctx.close();
  }
}

/* ═══════════════════════════════════════
   Main Component
   ═══════════════════════════════════════ */
export default function DjAutomata() {
  const [started, setStarted] = useState(false);
  const [deckA, setDeckA] = useState<DeckState>({
    track: TRACKS[0],
    status: 'idle',
    progress: 0,
  });
  const [deckB, setDeckB] = useState<DeckState>({
    track: TRACKS[1],
    status: 'idle',
    progress: 0,
  });
  const [crossfade, setCrossfade] = useState(0); // 0=A, 1=B
  const [activeDeck, setActiveDeck] = useState<'A' | 'B'>('A');
  const [consoleLogs, setConsoleLogs] = useState<ConsoleEntry[]>([]);
  const [glitching, setGlitching] = useState(false);
  const [bpm, setBpm] = useState(128);

  const engineRef = useRef<DjSynthEngine | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const eqBarsRef = useRef<HTMLDivElement>(null);
  const eqBarsBRef = useRef<HTMLDivElement>(null);
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number>(0);
  const crossfadeTimerRef = useRef<number>(0);
  const progressTimerRef = useRef<number>(0);

  // ── Add console log ──
  const addLog = useCallback((tag: string, message: string, tagClass = '') => {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    setConsoleLogs(prev => [...prev.slice(-30), { time, tag, tagClass, message }]);
  }, []);

  // ── Start the engine ──
  const handleStart = useCallback(async () => {
    const engine = new DjSynthEngine();
    engineRef.current = engine;
    await engine.resume();

    engine.startPattern('A', TRACKS[0].bpm);
    engine.startPattern('B', TRACKS[1].bpm);
    engine.setCrossfade(0);

    setStarted(true);
    setDeckA(prev => ({ ...prev, status: 'playing' }));
    setBpm(TRACKS[0].bpm);

    addLog('AUTOMATA', 'Engine initialized. Audio context active.', '');
    addLog('AUTOMATA', `DECK A loaded: ${TRACKS[0].name} [${TRACKS[0].bpm} BPM]`, '');
    addLog('AUTOMATA', `DECK B loaded: ${TRACKS[1].name} [${TRACKS[1].bpm} BPM]`, '');
    addLog('AUTOMATA', 'Autonomous mixing engaged.', '');
  }, [addLog]);

  // ── Visualization loop ──
  useEffect(() => {
    if (!started || !engineRef.current) return;

    const engine = engineRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');

    const draw = () => {
      // ── EQ bars ──
      const freqData = engine.getFrequencyData();

      [eqBarsRef, eqBarsBRef].forEach(ref => {
        const container = ref.current;
        if (!container) return;
        const bars = container.children;
        const step = Math.floor(freqData.length / bars.length);
        for (let i = 0; i < bars.length; i++) {
          const value = freqData[i * step] || 0;
          const height = (value / 255) * 100;
          (bars[i] as HTMLElement).style.height = `${Math.max(2, height)}%`;
          if (value > 220) {
            (bars[i] as HTMLElement).classList.add('hot');
          } else {
            (bars[i] as HTMLElement).classList.remove('hot');
          }
        }
      });

      // ── Waveform oscilloscope ──
      if (canvas && ctx) {
        const waveData = engine.getWaveformData();
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        // Grid lines
        ctx.strokeStyle = 'rgba(255,255,255,0.03)';
        ctx.lineWidth = 1;
        for (let y = 0; y < h; y += 20) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }

        // Center line
        ctx.strokeStyle = 'rgba(204,255,0,0.1)';
        ctx.beginPath();
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
        ctx.stroke();

        // Waveform
        ctx.strokeStyle = '#CCFF00';
        ctx.lineWidth = 1.5;
        ctx.shadowColor = 'rgba(204,255,0,0.5)';
        ctx.shadowBlur = 8;
        ctx.beginPath();

        const sliceWidth = w / waveData.length;
        let x = 0;
        for (let i = 0; i < waveData.length; i++) {
          const v = waveData[i] / 128.0;
          const y = (v * h) / 2;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
          x += sliceWidth;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      animFrameRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [started]);

  // ── Auto-crossfade timer ──
  useEffect(() => {
    if (!started || !engineRef.current) return;

    let trackIndexA = 0;
    let trackIndexB = 1;

    const doCrossfade = () => {
      const engine = engineRef.current;
      if (!engine) return;

      const nextActive = activeDeck === 'A' ? 'B' : 'A';

      // Glitch effect
      setGlitching(true);
      setTimeout(() => setGlitching(false), 600);

      addLog('AUTOMATA', `Crossfade initiated: DECK ${activeDeck} → DECK ${nextActive}`, 'violet');

      // Syncing phase
      if (nextActive === 'B') {
        setDeckB(prev => ({ ...prev, status: 'syncing' }));
        addLog('AUTOMATA', `Syncing BPM: ${deckA.track.bpm} → ${deckB.track.bpm}`, '');
      } else {
        setDeckA(prev => ({ ...prev, status: 'syncing' }));
        addLog('AUTOMATA', `Syncing BPM: ${deckB.track.bpm} → ${deckA.track.bpm}`, '');
      }

      // Crossfade animation over 3 seconds
      const steps = 30;
      const startVal = nextActive === 'B' ? 0 : 1;
      const endVal = nextActive === 'B' ? 1 : 0;
      let step = 0;

      const fadeInterval = window.setInterval(() => {
        step++;
        const t = step / steps;
        const val = startVal + (endVal - startVal) * t;
        engine.setCrossfade(val);
        setCrossfade(val);

        if (step >= steps) {
          clearInterval(fadeInterval);
          setActiveDeck(nextActive);

          if (nextActive === 'B') {
            setDeckA(prev => ({ ...prev, status: 'idle', progress: 0 }));
            setDeckB(prev => ({ ...prev, status: 'playing' }));
            setBpm(deckB.track.bpm);
            // Load next track on A
            trackIndexA = (trackIndexA + 2) % TRACKS.length;
            setDeckA(prev => ({
              ...prev,
              track: TRACKS[trackIndexA],
            }));
            addLog('AUTOMATA', `DECK A reloaded: ${TRACKS[trackIndexA].name}`, '');
          } else {
            setDeckB(prev => ({ ...prev, status: 'idle', progress: 0 }));
            setDeckA(prev => ({ ...prev, status: 'playing' }));
            setBpm(deckA.track.bpm);
            trackIndexB = (trackIndexB + 2) % TRACKS.length;
            setDeckB(prev => ({
              ...prev,
              track: TRACKS[trackIndexB],
            }));
            addLog('AUTOMATA', `DECK B reloaded: ${TRACKS[trackIndexB].name}`, '');
          }

          addLog('AUTOMATA', `Crossfade complete. DECK ${nextActive} active.`, '');
          addLog('AUTOMATA', 'Glitch transition engaged.', 'warn');
        }
      }, 100);
    };

    crossfadeTimerRef.current = window.setInterval(doCrossfade, 25000);
    return () => clearInterval(crossfadeTimerRef.current);
  }, [started, activeDeck, addLog, deckA.track.bpm, deckB.track.bpm]);

  // ── Progress simulation ──
  useEffect(() => {
    if (!started) return;

    progressTimerRef.current = window.setInterval(() => {
      setDeckA(prev => {
        if (prev.status === 'playing') {
          return { ...prev, progress: (prev.progress + 0.4) % 100 };
        }
        return prev;
      });
      setDeckB(prev => {
        if (prev.status === 'playing') {
          return { ...prev, progress: (prev.progress + 0.4) % 100 };
        }
        return prev;
      });
    }, 100);

    return () => clearInterval(progressTimerRef.current);
  }, [started]);

  // ── Auto-scroll console ──
  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [consoleLogs]);

  // ── Resize canvas ──
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  // ── Cleanup ──
  useEffect(() => {
    return () => {
      engineRef.current?.destroy();
    };
  }, []);

  // ── Render EQ bars ──
  const renderEqBars = (ref: React.RefObject<HTMLDivElement | null>) => (
    <div className="dj-eq-container" ref={ref}>
      {Array.from({ length: 32 }, (_, i) => (
        <div key={i} className="dj-eq-bar" style={{ height: '2%' }} />
      ))}
    </div>
  );

  const crossfadeTop = `${crossfade * 180}px`;

  return (
    <div className="dj-automata">
      {/* Background glows */}
      <div className={`dj-bg-glow a ${started ? 'beat' : ''}`} />
      <div className={`dj-bg-glow b ${started ? 'beat' : ''}`} />

      {/* Glitch overlay */}
      <div className={`dj-glitch-overlay ${glitching ? 'active' : ''}`} />

      {/* Start overlay */}
      <div
        className={`dj-start-overlay ${started ? 'hidden' : ''}`}
        onClick={handleStart}
      >
        <div className="dj-start-title">
          DJ<br /><span className="lime">AUTOMATA</span>
        </div>
        <div className="dj-start-subtitle">click to ignite</div>
      </div>

      {/* Main grid */}
      <div className="dj-grid">
        {/* Header */}
        <div className="dj-header">
          <div className="dj-header-brand">
            <Link to="/" style={{ color: 'rgba(250,250,250,0.35)', marginRight: '0.5rem' }}>
              <ArrowLeft size={14} />
            </Link>
            <div className="dot" />
            <span>DJ AUTOMATA</span>
          </div>
          <div className="dj-header-meta">
            <span>BPM <span className="bpm-value">{bpm}</span></span>
            <span>MODE: <span style={{ color: '#CCFF00' }}>AUTONOMOUS</span></span>
            <span>ACTIVE: DECK {activeDeck}</span>
          </div>
        </div>

        {/* Dual Decks */}
        <div className="dj-decks">
          {/* Deck A */}
          <div className={`dj-deck ${activeDeck === 'A' ? 'active' : ''}`}>
            <div className="dj-deck-header">
              <span className="dj-deck-label">DECK A</span>
              <span className={`dj-deck-status ${deckA.status}`}>
                {deckA.status.toUpperCase()}
              </span>
            </div>
            <div className="dj-track-name">{deckA.track.name}</div>
            <div className="dj-track-artist">
              {deckA.track.artist} · {deckA.track.bpm} BPM · {deckA.track.key}
            </div>
            <div className="dj-progress-container">
              <div className="dj-progress-bar" style={{ width: `${deckA.progress}%` }} />
            </div>
            {renderEqBars(eqBarsRef)}
          </div>

          {/* Crossfader */}
          <div className="dj-crossfader">
            <span className="dj-crossfader-label">XFADE</span>
            <div className="dj-crossfader-track">
              <div
                className="dj-crossfader-thumb"
                style={{ top: crossfadeTop }}
              />
            </div>
          </div>

          {/* Deck B */}
          <div className={`dj-deck ${activeDeck === 'B' ? 'active' : ''}`}>
            <div className="dj-deck-header">
              <span className="dj-deck-label">DECK B</span>
              <span className={`dj-deck-status ${deckB.status}`}>
                {deckB.status.toUpperCase()}
              </span>
            </div>
            <div className="dj-track-name">{deckB.track.name}</div>
            <div className="dj-track-artist">
              {deckB.track.artist} · {deckB.track.bpm} BPM · {deckB.track.key}
            </div>
            <div className="dj-progress-container">
              <div className="dj-progress-bar" style={{ width: `${deckB.progress}%` }} />
            </div>
            {renderEqBars(eqBarsBRef)}
          </div>
        </div>

        {/* Waveform Oscilloscope */}
        <div className="dj-waveform-container">
          <canvas ref={canvasRef} />
        </div>

        {/* Status Console */}
        <div className="dj-console">
          {consoleLogs.map((log, i) => (
            <div key={i} className="dj-console-line">
              <span className="timestamp">{log.time}</span>
              <span className={`tag ${log.tagClass}`}>[{log.tag}]</span>
              {log.message}
            </div>
          ))}
          <div ref={consoleEndRef} />
        </div>
      </div>
    </div>
  );
}
