import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

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
uniform float uScrollY;
varying vec2 vUv;

// Simplex 2D noise
vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
float snoise(vec2 v){
  const vec4 C = vec4(0.211324865405187, 0.366025403784439,
           -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy) );
  vec2 x0 = v -   i + dot(i, C.xx);
  vec2 i1;
  i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
  + i.x + vec3(0.0, i1.x, 1.0 ));
  vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
    dot(x12.zw,x12.zw)), 0.0);
  m = m*m ;
  m = m*m ;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
  vec3 g;
  g.x  = a0.x  * x0.x  + h.x  * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

void main() {
  vec2 uv = vUv;
  
  vec2 st = uv * 3.0;
  
  // Parallax based on scroll
  st.y += uScrollY * 0.0005;
  
  // Organic noise flow
  float n1 = snoise(st + uTime * 0.1);
  float n2 = snoise(st * 2.0 - uTime * 0.15);
  float flow = snoise(st + vec2(n1, n2));
  
  // Industrial Noir Palette
  vec3 baseColor = vec3(0.02, 0.02, 0.02); // #050505 approximate
  vec3 kintsugiColor = vec3(0.96, 0.62, 0.04); // #F59E0B
  vec3 cobaltColor = vec3(0.17, 0.23, 0.90); // #2B3BE5
  
  // Kintsugi fracture lines
  float fracture = smoothstep(0.48, 0.5, flow) - smoothstep(0.5, 0.52, flow);
  fracture += smoothstep(0.88, 0.9, n1) - smoothstep(0.9, 0.92, n1);
  
  // Cobalt aura
  float aura = smoothstep(0.1, 0.7, n2) * 0.15;
  
  // Combine
  vec3 color = baseColor;
  color += kintsugiColor * fracture * 1.5; 
  color += cobaltColor * aura;
  
  // Vignette
  float dist = distance(uv, vec2(0.5));
  color *= smoothstep(0.8, 0.2, dist);

  gl_FragColor = vec4(color, 1.0);
}
`;

function NoirPlane() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      uScrollY: { value: 0 }
    }),
    []
  );

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime;
      materialRef.current.uniforms.uScrollY.value = window.scrollY;
    }
  });

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        depthWrite={false}
        depthTest={false}
      />
    </mesh>
  );
}

export default function WebGLBackground() {
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: -1, pointerEvents: 'none' }}>
      <Canvas
        camera={{ position: [0, 0, 1] }}
        dpr={[1, 2]}
        gl={{ antialias: false, powerPreference: 'high-performance' }}
      >
        <NoirPlane />
      </Canvas>
    </div>
  );
}
