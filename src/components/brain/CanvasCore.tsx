import React, { useRef } from 'react';
import { Canvas, useFrame, extend } from '@react-three/fiber';
import { NoirShaderMaterial } from './NoirShaderMaterial';
import * as THREE from 'three';

extend({ NoirShaderMaterial });

const AnimatedPlane = () => {
  const materialRef = useRef<any>();

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uTime = state.clock.elapsedTime;
      materialRef.current.uMouse = new THREE.Vector2(
        (state.mouse.x + 1) / 2,
        (state.mouse.y + 1) / 2
      );
      materialRef.current.uScroll = window.scrollY;
    }
  });

  return (
    <mesh>
      <planeGeometry args={[10, 10, 128, 128]} />
      {/* @ts-ignore */}
      <noirShaderMaterial ref={materialRef} />
    </mesh>
  );
};

export default function CanvasCore() {
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: -1, pointerEvents: 'none' }}>
      <Canvas camera={{ position: [0, 0, 2] }}>
        <AnimatedPlane />
      </Canvas>
    </div>
  );
}
