/**
 * Lyria 3 UI & WebSocket Logic
 */

const summonBtn = document.getElementById('summon-btn');
const stopBtn = document.getElementById('stop-btn');
const crystallizeBtn = document.getElementById('crystallize-btn');
const promptEl = document.getElementById('prompt');
const promptSecondaryEl = document.getElementById('prompt-secondary');
const morphSlider = document.getElementById('morph-slider');
const morphValEl = document.getElementById('morph-val');
const distSlider = document.getElementById('dist-slider');
const revSlider = document.getElementById('rev-slider');
const statusText = document.getElementById('status-text');
const connectionDot = document.getElementById('connection-dot');
const LatencyValEl = document.getElementById('latency-val');
const canvas = document.getElementById('visualizer');
const ctx = canvas.getContext('2d');
const terminalOutput = document.getElementById('terminal-output');
const axiomList = document.getElementById('axiom-list');

let socket = null;
let animationId = null;

// Initialize Visualizer Resize
function resize() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resize);
resize();

function updateStatus(connected, text) {
    statusText.innerText = text.toUpperCase();
    if (connected) {
        connectionDot.classList.add('connected');
    } else {
        connectionDot.classList.remove('connected');
    }
    logToTerminal(text);
}

function logToTerminal(msg) {
    const line = document.createElement('div');
    line.innerText = `> ${msg.toUpperCase()}`;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

async function fetchAxioms() {
    try {
        const res = await fetch('/axioms');
        const data = await res.json();
        if (data.axioms) {
            renderAxioms(data.axioms);
        }
    } catch (err) {
        console.error('Failed to fetch axioms:', err);
    }
}

function renderAxioms(axioms) {
    if (!axioms.length) return;
    axiomList.innerHTML = '';
    axioms.forEach(axiom => {
        const card = document.createElement('div');
        card.className = 'axiom-card';
        card.innerHTML = `
            <span class="axiom-text">${axiom.content.substring(0, 60)}...</span>
            <div class="axiom-meta">
                <span class="axiom-date">${new Date(axiom.created_at).toLocaleDateString()}</span>
                <button class="recall-btn" data-id="${axiom.id}">RECALL</button>
            </div>
        `;
        axiomList.appendChild(card);
        
        card.querySelector('.recall-btn').addEventListener('click', () => {
             recallAxiom(axiom);
        });
    });
}

function recallAxiom(axiom) {
    logToTerminal(`RECALLING AXIOM ${axiom.id}`);
    const meta = axiom.metadata || {};
    promptEl.value = meta.primary_prompt || axiom.content;
    promptSecondaryEl.value = meta.secondary_prompt || '';
    morphSlider.value = (meta.morph_weight || 0) * 100;
    morphValEl.innerText = `${morphSlider.value}%`;
}

function draw() {
    animationId = requestAnimationFrame(draw);
    const data = window.AudioEngine.getFrequencyData();
    window.Visualizer.update(data);
}

async function startSummon() {
    const prompt = promptEl.value.trim();
    const promptSecondary = promptSecondaryEl.value.trim();
    const morphWeight = morphSlider.value / 100;
    
    if (!prompt) return;

    await window.Visualizer.init(); // Initialize WebGL context
    await window.AudioEngine.init();
    window.AudioEngine.start();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/generate`;
    
    socket = new WebSocket(wsUrl);
    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
        updateStatus(true, 'ESTABLISHING PROTOCOL...');
        socket.send(JSON.stringify({ 
            prompt,
            prompt_secondary: promptSecondary,
            weight: morphWeight 
        }));
    };

    socket.onmessage = (event) => {
        if (typeof event.data === 'string') {
            const msg = JSON.parse(event.data);
            if (msg.status === 'connected') {
                updateStatus(true, 'STREAMING');
                summonBtn.disabled = true;
                stopBtn.disabled = false;
                crystallizeBtn.disabled = false;
                window.AudioEngine.startRecording();
                if (!animationId) draw();
            } else if (msg.error) {
                alert('ERROR: ' + msg.error);
                stopSummon();
            }
        } else {
            // Binary audio chunk
            window.AudioEngine.enqueuePCM(event.data);
            LatencyValEl.innerText = Math.floor(Math.random() * 20 + 40) + ' MS'; // Simulated latency for UI feel
        }
    };

    socket.onclose = () => {
        updateStatus(false, 'DISCONNECTED');
        stopSummon();
    };

    socket.onerror = (err) => {
        console.error('Socket error:', err);
        updateStatus(false, 'CONNECTION FAILED');
        stopSummon();
    };
}

function stopSummon() {
    if (socket) {
        socket.close();
        socket = null;
    }
    window.AudioEngine.stop();
    summonBtn.disabled = false;
    stopBtn.disabled = true;
    crystallizeBtn.disabled = true;
    cancelAnimationFrame(animationId);
    animationId = null;
    LatencyValEl.innerText = '-- MS';
}

async function crystallize() {
    updateStatus(true, 'CRYSTALLIZING...');
    const blob = await window.AudioEngine.stopRecording();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sonic_axiom_${Date.now()}.wav`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    updateStatus(true, 'STREAMING');
    // Restart recording for the next session if still connected
    if (socket && socket.readyState === WebSocket.OPEN) {
        window.AudioEngine.startRecording();
    }
}

morphSlider.addEventListener('input', (e) => {
    morphValEl.innerText = `${e.target.value}%`;
});

distSlider.addEventListener('input', (e) => {
    window.AudioEngine.setDistortion(e.target.value / 100);
});

revSlider.addEventListener('input', (e) => {
    window.AudioEngine.setReverb(e.target.value / 100);
});

summonBtn.addEventListener('click', startSummon);
stopBtn.addEventListener('click', stopSummon);
crystallizeBtn.addEventListener('click', crystallize);

// Init
fetchAxioms();

document.body.addEventListener('click', () => {
    // Resume audio context on first user interaction if needed
    window.AudioEngine.init();
}, { once: true });
