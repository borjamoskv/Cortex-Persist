/**
 * Lyria 3 Audio Engine
 * Handles PCM 16-bit 48kHz real-time streaming
 */

class LyriaAudioEngine {
    constructor() {
        this.ctx = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 48000
        });
        this.analyser = this.ctx.createAnalyser();
        this.analyser.fftSize = 512;
        
        // Final destination for playback
        this.analyser.connect(this.ctx.destination);

        // Recording destination
        this.dest = this.ctx.createMediaStreamDestination();
        this.analyser.connect(this.dest);
        
        this.chunks = [];
        this.recorder = new MediaRecorder(this.dest.stream);
        this.recorder.ondataavailable = (e) => {
            if (e.data.size > 0) this.chunks.push(e.data);
        };
        
        // Post-Processing Nodes
        this.distortion = this.ctx.createWaveShaper();
        this.distortion.curve = this.makeDistortionCurve(0);
        this.distortion.oversample = '4x';

        this.reverb = this.ctx.createGain(); // Reverb mix node
        this.delay = this.ctx.createDelay();
        this.feedback = this.ctx.createGain();
        
        this.delay.delayTime.value = 0.3;
        this.feedback.gain.value = 0.4;
        this.reverb.gain.value = 0.0; // Dry by default

        // Wiring: Source -> Distortion -> Reverb Loop -> Analyser
        // Delay Loop
        this.distortion.connect(this.delay);
        this.delay.connect(this.feedback);
        this.feedback.connect(this.delay);
        this.delay.connect(this.reverb);

        this.distortion.connect(this.analyser); // Clean signal to analyser
        this.reverb.connect(this.analyser);     // Wet signal to analyser
        
        this.nextStartTime = 0;
        this.isPlaying = false;
    }

    async init() {
        if (this.ctx.state === 'suspended') {
            await this.ctx.resume();
        }
    }

    /**
     * Enqueue PCM 16-bit integer data
     * @param {ArrayBuffer} buffer 
     */
    enqueuePCM(buffer) {
        if (!this.isPlaying) return;

        const int16 = new Int16Array(buffer);
        const float32 = new Float32Array(int16.length);
        
        // Convert PCM16 to Float32
        for (let i = 0; i < int16.length; i++) {
            float32[i] = int16[i] / 32768.0;
        }

        const audioBuffer = this.ctx.createBuffer(1, float32.length, 48000);
        audioBuffer.getChannelData(0).set(float32);

        const source = this.ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.distortion);

        const currentTime = this.ctx.currentTime;
        if (this.nextStartTime < currentTime) {
            this.nextStartTime = currentTime + 0.05; // Small buffer for initial chunk
        }

        source.start(this.nextStartTime);
        this.nextStartTime += audioBuffer.duration;
    }

    start() {
        this.isPlaying = true;
        this.nextStartTime = this.ctx.currentTime;
    }

    stop() {
        this.isPlaying = false;
        if (this.recorder.state === 'recording') {
            this.recorder.stop();
        }
    }

    startRecording() {
        this.chunks = [];
        this.recorder.start();
    }

    stopRecording() {
        return new Promise((resolve) => {
            this.recorder.onstop = () => {
                const blob = new Blob(this.chunks, { type: 'audio/wav' });
                resolve(blob);
            };
            this.recorder.stop();
        });
    }

    getFrequencyData() {
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);
        return dataArray;
    }

    setDistortion(amount) {
        this.distortion.curve = this.makeDistortionCurve(amount * 400);
    }

    setReverb(amount) {
        this.reverb.gain.setTargetAtTime(amount, this.ctx.currentTime, 0.1);
    }

    makeDistortionCurve(amount) {
        const k = typeof amount === 'number' ? amount : 50;
        const n_samples = 44100;
        const curve = new Float32Array(n_samples);
        const deg = Math.PI / 180;
        for (let i = 0; i < n_samples; ++i) {
            const x = (i * 2) / n_samples - 1;
            curve[i] = ((3 + k) * x * 20 * deg) / (Math.PI + k * Math.abs(x));
        }
        return curve;
    }
}

window.AudioEngine = new LyriaAudioEngine();
