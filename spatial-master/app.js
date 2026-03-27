// CORTEX SPATIAL ENGINE v1.0
// Strict Architecture: Zero rhetoric, deterministic nodes.

let audioCtx = null;
let sourceNode = null;
let inputGainNode = null;
let compNode = null;
let eqLowNode = null;
let eqMidNode = null;
let eqHighNode = null;
let pannerNode = null;
let masterGainNode = null;
let analyserNode = null;

let isPlaying = false;
let animationId = null;

// DOM Elements
const audioUpload = document.getElementById('audio-upload');
const fileName = document.getElementById('file-name');
const audioElement = document.getElementById('audio-element');
const btnPlay = document.getElementById('btn-play');
const btnPause = document.getElementById('btn-pause');
const canvas = document.getElementById('visualizer');
const canvasCtx = canvas.getContext('2d');

// Transport state
audioUpload.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        fileName.textContent = file.name;
        const objectUrl = URL.createObjectURL(file);
        audioElement.src = objectUrl;
        btnPlay.disabled = false;
        btnPause.disabled = false;
    }
});

btnPlay.addEventListener('click', () => {
    if (!audioCtx) initAudioGraph();
    
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    
    audioElement.play();
    isPlaying = true;
    drawVisualizer();
});

btnPause.addEventListener('click', () => {
    audioElement.pause();
    isPlaying = false;
    if (animationId) cancelAnimationFrame(animationId);
});

function initAudioGraph() {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    // Nodes
    sourceNode = audioCtx.createMediaElementSource(audioElement);
    
    inputGainNode = audioCtx.createGain();
    
    compNode = audioCtx.createDynamicsCompressor();
    
    eqLowNode = audioCtx.createBiquadFilter();
    eqLowNode.type = 'lowshelf';
    eqLowNode.frequency.value = 100;
    
    eqMidNode = audioCtx.createBiquadFilter();
    eqMidNode.type = 'peaking';
    eqMidNode.frequency.value = 1000;
    eqMidNode.Q.value = 1;

    eqHighNode = audioCtx.createBiquadFilter();
    eqHighNode.type = 'highshelf';
    eqHighNode.frequency.value = 5000;
    
    pannerNode = audioCtx.createPanner();
    pannerNode.panningModel = 'HRTF';
    pannerNode.distanceModel = 'inverse';
    pannerNode.refDistance = 1;
    pannerNode.maxDistance = 10000;
    pannerNode.rolloffFactor = 1;
    pannerNode.coneInnerAngle = 360;
    pannerNode.coneOuterAngle = 0;
    pannerNode.coneOuterGain = 0;
    
    // Set listener fixed position
    const listener = audioCtx.listener;
    if(listener.positionX) {
        listener.positionX.value = 0;
        listener.positionY.value = 0;
        listener.positionZ.value = 0;
        listener.forwardX.value = 0;
        listener.forwardY.value = 0;
        listener.forwardZ.value = -1;
        listener.upX.value = 0;
        listener.upY.value = 1;
        listener.upZ.value = 0;
    } else {
        listener.setPosition(0,0,0);
        listener.setOrientation(0,0,-1,0,1,0); // deprecated form fallback
    }

    masterGainNode = audioCtx.createGain();
    
    analyserNode = audioCtx.createAnalyser();
    analyserNode.fftSize = 2048;
    
    // Chain: Source -> InputGain -> EQ -> Compressor -> Spatial -> Master Gain -> Analyser -> Destination
    sourceNode.connect(inputGainNode);
    inputGainNode.connect(eqLowNode);
    eqLowNode.connect(eqMidNode);
    eqMidNode.connect(eqHighNode);
    eqHighNode.connect(compNode);
    compNode.connect(pannerNode);
    pannerNode.connect(masterGainNode);
    masterGainNode.connect(analyserNode);
    analyserNode.connect(audioCtx.destination);

    // Initial sync
    syncControls();
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
}

function syncControls() {
    // Input Gain
    bindSlider('input-gain', val => { inputGainNode.gain.value = val; }, val => `${(20 * Math.log10(val || 0.001)).toFixed(1)} dB`);
    // Master Gain
    bindSlider('master-gain', val => { masterGainNode.gain.value = val; }, val => `${(20 * Math.log10(val || 0.001)).toFixed(1)} dB`);
    
    // Compressor
    bindSlider('comp-thresh', val => { compNode.threshold.value = val; }, val => `${val} dB`);
    bindSlider('comp-ratio', val => { compNode.ratio.value = val; }, val => `${val}:1`);
    
    // EQ
    bindSlider('eq-low', val => { eqLowNode.gain.value = val; }, val => `${val} dB`);
    bindSlider('eq-mid', val => { eqMidNode.gain.value = val; }, val => `${val} dB`);
    bindSlider('eq-high', val => { eqHighNode.gain.value = val; }, val => `${val} dB`);
    
    // Panner
    bindSlider('pan-x', val => { 
        if(pannerNode.positionX){ pannerNode.positionX.value = val; } else { updatePannerLegacy(); }
    }, val => parseFloat(val).toFixed(1));
    
    bindSlider('pan-y', val => { 
        if(pannerNode.positionY){ pannerNode.positionY.value = val; } else { updatePannerLegacy(); }
    }, val => parseFloat(val).toFixed(1));
    
    bindSlider('pan-z', val => { 
        if(pannerNode.positionZ){ pannerNode.positionZ.value = val; } else { updatePannerLegacy(); }
    }, val => parseFloat(val).toFixed(1));
}

function updatePannerLegacy() {
    const x = document.getElementById('pan-x').value;
    const y = document.getElementById('pan-y').value;
    const z = document.getElementById('pan-z').value;
    pannerNode.setPosition(x, y, z);
}

function bindSlider(id, targetParamCb, formatterCb) {
    const input = document.getElementById(id);
    const display = document.getElementById(`${id}-val`);
    
    // Init values
    targetParamCb(parseFloat(input.value));
    display.textContent = formatterCb(input.value);
    
    input.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        targetParamCb(val);
        display.textContent = formatterCb(val);
    });
}

function resizeCanvas() {
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
}

function drawVisualizer() {
    if (!isPlaying) return;
    animationId = requestAnimationFrame(drawVisualizer);
    
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyserNode.getByteFrequencyData(dataArray);
    
    canvasCtx.fillStyle = '#0A0A0A';
    canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
    
    const barWidth = (canvas.width / bufferLength) * 2.5;
    let barHeight;
    let x = 0;
    
    for (let i = 0; i < bufferLength; i++) {
        barHeight = dataArray[i];
        
        // Gradient coloring Exergy blue
        const r = 43;
        const g = 59;
        const b = 229 + (barHeight / 2);
        
        canvasCtx.fillStyle = `rgb(${r},${g},${b})`;
        canvasCtx.fillRect(x, canvas.height - barHeight / 2, barWidth, barHeight / 2);
        
        x += barWidth + 1;
    }
}
