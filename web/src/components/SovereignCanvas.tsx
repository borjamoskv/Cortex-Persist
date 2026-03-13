import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Environment, Float, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

function Monolith() {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Follow the mouse subtly with the monolithic block
  useFrame((state) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.x = THREE.MathUtils.lerp(meshRef.current.rotation.x, state.pointer.y * 0.4, 0.05);
    meshRef.current.rotation.y = THREE.MathUtils.lerp(meshRef.current.rotation.y, state.pointer.x * 0.4, 0.05);
  });

  return (
    <Float speed={2} rotationIntensity={0.8} floatIntensity={1.5}>
      <mesh ref={meshRef} position={[4, 0, -2]}>
        {/* Sacred Geometry: Icosahedron distorted by physical noise */}
        <icosahedronGeometry args={[3.5, 2]} />
        <MeshDistortMaterial 
          color="#050505" 
          emissive="#CCFF00" 
          emissiveIntensity={0.05}
          envMapIntensity={2} 
          clearcoat={1} 
          clearcoatRoughness={0.1}
          metalness={0.9}
          roughness={0.1}
          distort={0.4}
          speed={1.5}
        />
      </mesh>
    </Float>
  );
}

// Rig to move the camera based on pointer, giving a 3D parallax effect Nivel Igloo
function Rig() {
  useFrame((state) => {
    state.camera.position.x = THREE.MathUtils.lerp(state.camera.position.x, state.pointer.x * 1.5, 0.05);
    state.camera.position.y = THREE.MathUtils.lerp(state.camera.position.y, state.pointer.y * 1.5, 0.05);
    state.camera.lookAt(0, 0, 0);
  });
  return null;
}

export default function SovereignCanvas() {
  return (
    <div className="absolute inset-0 z-0 pointer-events-none opacity-60 mix-blend-screen overflow-hidden">
      <Canvas camera={{ position: [0, 0, 10], fov: 45 }} dpr={[1, 2]}>
        <ambientLight intensity={0.1} />
        <directionalLight position={[10, 10, 5]} intensity={2} color="#6600FF" />
        <spotLight position={[-10, 10, 10]} intensity={4} color="#CCFF00" angle={0.5} penumbra={1} />
        
        <Monolith />
        <Rig />
        
        {/* City environment reflection provides realistic metal/glass reflections */}
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
