/**
 * Lyria 3 WebGL Visualizer
 * Shadow-Aesthetic Raymarching-inspired engine
 */

class LyriaVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.renderer = null;
        this.scene = null;
        this.camera = null;
        this.material = null;
        this.mesh = null;
        this.uniforms = {
            uTime: { value: 0 },
            uResolution: { value: new THREE.Vector2() },
            uAudioData: { value: new Float32Array(128) },
            uIntensity: { value: 0.0 }
        };
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;

        // Load Three.js if not present
        if (typeof THREE === 'undefined') {
            await this.loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.min.js');
        }

        this.scene = new THREE.Scene();
        this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
        
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true
        });

        this.resize();

        const vertexShader = `
            varying vec2 vUv;
            void main() {
                vUv = uv;
                gl_Position = vec4(position, 1.0);
            }
        `;

        const fragmentShader = `
            uniform float uTime;
            uniform vec2 uResolution;
            uniform float uAudioData[128];
            uniform float uIntensity;
            varying vec2 vUv;

            // Industrial Noir Palette
            const vec3 background = vec3(0.039, 0.039, 0.039); // #0A0A0A
            const vec3 cyberLime = vec3(0.8, 1.0, 0.0);      // #CCFF00

            float sdSphere(vec3 p, float s) {
                return length(p) - s;
            }

            void main() {
                vec2 uv = (gl_FragCoord.xy * 2.0 - uResolution.xy) / min(uResolution.y, uResolution.x);
                
                // Audio reactivity setup
                float lowFreq = uAudioData[5] * 0.5;
                float midFreq = uAudioData[40] * 0.3;
                
                vec3 finalColor = background;
                
                // Shadow-Aesthetic Raymarching Core (Simplified)
                vec3 ro = vec3(0.0, 0.0, 2.0);
                vec3 rd = normalize(vec3(uv, -1.0));
                float t = 0.0;
                
                for(int i = 0; i < 32; i++) {
                    vec3 p = ro + rd * t;
                    
                    // Distort shape with audio
                    float displacement = sin(5.0 * p.x + uTime + lowFreq) * sin(5.0 * p.y + uTime) * sin(5.0 * p.z + uTime) * 0.1;
                    float d = sdSphere(p, 0.6 + displacement + midFreq);
                    
                    if(d < 0.001 || t > 10.0) break;
                    t += d;
                }
                
                if(t < 10.0) {
                    vec3 p = ro + rd * t;
                    float edge = 1.0 - smoothstep(0.0, 0.8, t * 0.2);
                    vec3 glow = cyberLime * edge * uIntensity;
                    finalColor = mix(background, glow, edge);
                }
                
                // Add noise grain
                float noise = fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453);
                finalColor += noise * 0.05;

                gl_FragColor = vec4(finalColor, 1.0);
            }
        `;

        this.material = new THREE.ShaderMaterial({
            uniforms: this.uniforms,
            vertexShader,
            fragmentShader,
            transparent: true
        });

        this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.material);
        this.scene.add(this.mesh);

        this.initialized = true;
        window.addEventListener('resize', () => this.resize());
    }

    loadScript(url) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = url;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    resize() {
        if (!this.renderer) return;
        const width = this.canvas.parentElement.clientWidth;
        const height = this.canvas.parentElement.clientHeight;
        this.renderer.setSize(width, height, false);
        this.uniforms.uResolution.value.set(width, height);
    }

    update(audioData) {
        if (!this.initialized) return;

        // Map 0-255 audio data to normalized uniforms
        const normalizedData = new Float32Array(128);
        let sum = 0;
        for (let i = 0; i < 128; i++) {
            normalizedData[i] = audioData[i] / 255.0;
            sum += normalizedData[i];
        }
        
        this.uniforms.uAudioData.value = normalizedData;
        this.uniforms.uIntensity.value = Math.min(1.0, sum / 20.0); // Dynamic intensity
        this.uniforms.uTime.value += 0.01;

        this.renderer.render(this.scene, this.camera);
    }
}

window.Visualizer = new LyriaVisualizer('visualizer');
