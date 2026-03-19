import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

// Custom Fragment Shader para Post-Processing (Glitch/Chromatic Aberration)
const chromaShader = {
    uniforms: {
        tDiffuse: { value: null },
        uDistortion: { value: 0.0 },
        uTime: { value: 0.0 }
    },
    vertexShader: `
        varying vec2 vUv;
        void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `,
    fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float uDistortion;
        uniform float uTime;
        varying vec2 vUv;
        void main() {
            vec2 uv = vUv;
            // Chromatic aberration offset based on distortion
            float offset = uDistortion * 0.05 * sin(uTime * 10.0 + uv.y * 20.0);
            
            float r = texture2D(tDiffuse, uv + vec2(offset, 0.0)).r;
            float g = texture2D(tDiffuse, uv).g;
            float b = texture2D(tDiffuse, uv - vec2(offset, 0.0)).b;
            
            vec4 texColor = texture2D(tDiffuse, uv);
            gl_FragColor = vec4(r, g, b, texColor.a);
        }
    `
};

// Shaders para el Objeto Abstracto (Vertex Displacement + Fresnel Noise)
const objectVertexShader = `
    uniform float uTime;
    uniform float uSpike;
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    // Simplex Noise 3D
    vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
    vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}

    float snoise(vec3 v){ 
      const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
      const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
      vec3 i  = floor(v + dot(v, C.yyy) );
      vec3 x0 = v - i + dot(i, C.xxx) ;
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min( g.xyz, l.zxy );
      vec3 i2 = max( g.xyz, l.zxy );
      vec3 x1 = x0 - i1 + 1.0 * C.xxx;
      vec3 x2 = x0 - i2 + 2.0 * C.xxx;
      vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
      i = mod(i, 289.0 ); 
      vec4 p = permute( permute( permute( 
                 i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
               + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
               + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
      float n_ = 1.0/7.0;
      vec3  ns = n_ * D.wyz - D.xzx;
      vec4 j = p - 49.0 * floor(p * ns.z *ns.z);
      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_ );
      vec4 x = x_ *ns.x + ns.yyyy;
      vec4 y = y_ *ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);
      vec4 b0 = vec4( x.xy, y.xy );
      vec4 b1 = vec4( x.zw, y.zw );
      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
      vec3 p0 = vec3(a0.xy,h.x);
      vec3 p1 = vec3(a0.zw,h.y);
      vec3 p2 = vec3(a1.xy,h.z);
      vec3 p3 = vec3(a1.zw,h.w);
      vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
      p0 *= norm.x;
      p1 *= norm.y;
      p2 *= norm.z;
      p3 *= norm.w;
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
    }

    void main() {
        vUv = uv;
        vNormal = normal;
        
        // Procedural vertex displacement
        float noise = snoise(position * 1.5 + uTime * 0.4);
        vec3 displacedPosition = position + normal * noise * uSpike;
        
        vec4 mvPosition = modelViewMatrix * vec4(displacedPosition, 1.0);
        vViewPosition = -mvPosition.xyz;
        
        gl_Position = projectionMatrix * mvPosition;
    }
`;

const objectFragmentShader = `
    uniform float uTime;
    uniform vec3 uColorGlow;
    uniform float uIntensity;
    uniform float uWireframeOpacity;

    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    void main() {
        vec3 normal = normalize(vNormal);
        vec3 viewDir = normalize(vViewPosition);
        
        // Fresnel Edge Glow
        float fresnel = dot(viewDir, normal);
        fresnel = clamp(1.0 - fresnel, 0.0, 1.0);
        fresnel = pow(fresnel, 3.0); // sharp edge
        
        // Base color is dark industrial metal
        vec3 baseColor = vec3(0.04, 0.04, 0.05);
        
        // Add Cyber Lime glow on the edges based on intensity uniform
        vec3 finalColor = baseColor + (uColorGlow * fresnel * uIntensity);
        
        // Pseudo wireframe (UV based grid)
        vec2 grid = abs(fract(vUv * 20.0) - 0.5);
        float line = smoothstep(0.45, 0.5, max(grid.x, grid.y));
        finalColor += line * uColorGlow * uWireframeOpacity;
        
        gl_FragColor = vec4(finalColor, 1.0);
    }
`;

export function initWebGL() {
    const canvas = document.querySelector('#webgl-canvas');
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "high-performance" });
    renderer.setPixelRatio(window.devicePixelRatio); // Full res for Bloom
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    
    // Cámara
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0, 8);

    const objectGroup = new THREE.Group();
    scene.add(objectGroup);

    // Icosaedro alto poligonaje para deforms
    const geometry = new THREE.IcosahedronGeometry(2, 32);
    
    // Shader custom Noir
    const coreUniforms = {
        uTime: { value: 0 },
        uSpike: { value: 0.1 },             // ScrollTriggered
        uIntensity: { value: 0.5 },         // ScrollTriggered
        uWireframeOpacity: { value: 0.0 },  // ScrollTriggered
        uColorGlow: { value: new THREE.Color(0xccff00) }
    };

    const material = new THREE.ShaderMaterial({
        vertexShader: objectVertexShader,
        fragmentShader: objectFragmentShader,
        uniforms: coreUniforms,
        wireframe: false,
        transparent: true
    });

    const mesh = new THREE.Mesh(geometry, material);
    objectGroup.add(mesh);

    // --- EFFECT COMPOSER (Bloom + Chroma Glitch) --- //
    const composer = new EffectComposer(renderer);
    
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);

    const bloomPass = new UnrealBloomPass(
        new THREE.Vector2(window.innerWidth, window.innerHeight),
        1.5, // strength
        0.4, // radius
        0.85 // threshold
    );
    composer.addPass(bloomPass);

    const chromaPass = new ShaderPass(chromaShader);
    composer.addPass(chromaPass);

    const outputPass = new OutputPass();
    composer.addPass(outputPass);

    // Mouse Parallax System
    const mouse = new THREE.Vector2(0, 0);
    const targetMouse = new THREE.Vector2(0, 0);
    
    window.addEventListener('mousemove', (e) => {
        targetMouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        targetMouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    });

    // Resize handler
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
        composer.setSize(window.innerWidth, window.innerHeight);
    });

    // Render loop
    const clock = new THREE.Clock();
    
    function animate() {
        requestAnimationFrame(animate);
        const elapsedTime = clock.getElapsedTime();
        const delta = clock.getDelta();
        
        // Procedural uniforms
        coreUniforms.uTime.value = elapsedTime;
        chromaPass.uniforms.uTime.value = elapsedTime;
        
        // Lerp mouse for smooth parallax
        mouse.x += (targetMouse.x - mouse.x) * 0.05;
        mouse.y += (targetMouse.y - mouse.y) * 0.05;
        
        // Parallax rotations
        objectGroup.rotation.y = elapsedTime * 0.1 + mouse.x * 0.5;
        objectGroup.rotation.x = mouse.y * 0.5;
        
        camera.position.x += (mouse.x * 1.5 - camera.position.x) * 0.05;
        camera.position.y += (mouse.y * 1.5 - camera.position.y) * 0.05;
        camera.lookAt(0, 0, 0);
        
        // Render via composer
        composer.render();
    }
    animate();

    return {
        scene, 
        camera, 
        renderer,
        composer, 
        objectGroup, 
        materials: { core: material },
        uniforms: { 
            core: coreUniforms, 
            chroma: chromaPass.uniforms,
            bloom: bloomPass
        }
    };
}
