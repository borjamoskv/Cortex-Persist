import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const PARTICLE_COUNT = 10000;

export function SwarmScene() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  
  // Ouroboros Noir Palette
  const colorIdle = new THREE.Color('#2B3BE5'); // Accent blue
  const colorHit = new THREE.Color('#FF2040');  // Accent red
  const colorNoir = new THREE.Color('#0A0A0A');

  const { dummy, particles } = useMemo(() => {
    const dummy = new THREE.Object3D();
    const particles = Array.from({ length: PARTICLE_COUNT }, (_, i) => {
      const phi = Math.acos(-1 + (2 * i) / PARTICLE_COUNT);
      const theta = Math.sqrt(PARTICLE_COUNT * Math.PI) * phi;
      const r = 25;
      const x = r * Math.cos(theta) * Math.sin(phi);
      const y = r * Math.sin(theta) * Math.sin(phi);
      const z = r * Math.cos(phi);

      return {
        initialPosition: new THREE.Vector3(x, y, z),
        position: new THREE.Vector3(x, y, z),
        intensity: 0,
        targetIntensity: 0,
        state: 'idle' as 'idle' | 'active' | 'hit' | 'yield',
      };
    });
    return { dummy, particles };
  }, []);

  const colors = useMemo(() => {
    const array = new Float32Array(PARTICLE_COUNT * 3);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        colorNoir.toArray(array, i * 3);
    }
    return new THREE.InstancedBufferAttribute(array, 3);
  }, []);

  // 1. Binary Hook: Zero-Latency Injection (Axiom Ω₆)
  useEffect(() => {
    const handleBinaryEvent = (e: Event) => {
      const data = (e as CustomEvent).detail as Float32Array;
      if (data.length === PARTICLE_COUNT) {
        for (let i = 0; i < PARTICLE_COUNT; i++) {
          particles[i].targetIntensity = data[i];
          if (data[i] > 0.8) particles[i].state = 'hit';
          else if (data[i] > 0.5) particles[i].state = 'active';
        }
      }
    };

    window.addEventListener('ouroboros-binary-event', handleBinaryEvent);
    return () => window.removeEventListener('ouroboros-binary-event', handleBinaryEvent);
  }, [particles]);

  useFrame((state) => {
    if (!meshRef.current) return;

    meshRef.current.rotation.y = state.clock.elapsedTime * 0.03;
    meshRef.current.rotation.z = state.clock.elapsedTime * 0.01;

    let needsColorUpdate = false;

    // Optimized Frame Loop: Focused on Intensity Decay & Buffer Updates
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const p = particles[i];

      // Ebbinghaus Tensor Decay (O(1) Memory Hygiene)
      p.intensity += (p.targetIntensity - p.intensity) * 0.15;
      p.targetIntensity *= 0.94; // Shorter decay for crisp binary updates

      const intensity = p.intensity;
      
      // Update Scale & Matrix
      dummy.position.copy(p.position);
      const scale = 1.0 + intensity * 6.0;
      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      // Color Updates (High frequency)
      if (intensity > 0.05) {
          needsColorUpdate = true;
          let r = colorNoir.r, g = colorNoir.g, b = colorNoir.b;
          if (p.state === 'hit') {
              r = THREE.MathUtils.lerp(colorNoir.r, colorHit.r, intensity);
              g = THREE.MathUtils.lerp(colorNoir.g, colorHit.g, intensity);
              b = THREE.MathUtils.lerp(colorNoir.b, colorHit.b, intensity);
          } else if (p.state === 'active') {
              r = THREE.MathUtils.lerp(colorNoir.r, colorIdle.r, intensity);
              g = THREE.MathUtils.lerp(colorNoir.g, colorIdle.g, intensity);
              b = THREE.MathUtils.lerp(colorNoir.b, colorIdle.b, intensity);
          }
          colors.setXYZ(i, r, g, b);
      } else {
          if (colors.getX(i) > colorNoir.r + 0.005) {
              colors.setXYZ(i, colorNoir.r, colorNoir.g, colorNoir.b);
              needsColorUpdate = true;
          }
      }
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (needsColorUpdate) {
      colors.needsUpdate = true;
    }
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, PARTICLE_COUNT]}>
      <icosahedronGeometry args={[0.07, 0]}>
        <instancedBufferAttribute attach="attributes-color" args={[colors.array, 3]} />
      </icosahedronGeometry>
      <meshBasicMaterial vertexColors toneMapped={false} />
    </instancedMesh>
  );
}
