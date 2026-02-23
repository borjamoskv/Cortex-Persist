import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Float, Text, ContactShadows, Environment } from '@react-three/drei';
import { EffectComposer, Bloom, Noise, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';
import { oracleStream } from '../api/oracleStream';

interface NodeData {
  id: string;
  name: string;
  type: 'axiom' | 'fact' | 'ghost' | 'fiat_stream';
  position: [number, number, number];
}

const NODES: NodeData[] = [
  { id: '1', name: 'Prime Directive', type: 'axiom', position: [0, 0, 0] },
  { id: '2', name: 'Auth Module', type: 'fact', position: [10, 5, -5] },
  { id: '3', name: 'Vector Store', type: 'fact', position: [-8, -4, 6] },
  { id: '4', name: 'Fiat Stream (Bunq)', type: 'fiat_stream', position: [5, -10, 2] },
  { id: '5', name: 'Consensus Engine', type: 'fact', position: [-12, 8, -8] },
  { id: '6', name: 'Secure Vault', type: 'axiom', position: [15, -2, 10] },
];

function Connection({ start, end }: { start: [number, number, number], end: [number, number, number] }) {
  const lineRef = useRef<THREE.Line>(null);
  const points = useMemo(() => [new THREE.Vector3(...start), new THREE.Vector3(...end)], [start, end]);
  const lineGeometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);

  useFrame((state) => {
    if (lineRef.current) {
      const material = lineRef.current.material as THREE.LineBasicMaterial;
      material.opacity = 0.1 + Math.abs(Math.sin(state.clock.elapsedTime * 2)) * 0.2;
    }
  });

  return (
    <line geometry={lineGeometry} ref={lineRef}>
      <lineBasicMaterial color="#CCFF00" transparent opacity={0.1} />
    </line>
  );
}

function Node({ data }: { data: NodeData }) {
  const meshRef = useRef<THREE.Group>(null);
  const color = data.type === 'axiom' ? '#CCFF00' : 
                data.type === 'ghost' ? '#6600FF' : 
                data.type === 'fiat_stream' ? '#06d6a0' : '#2E5090';
  const initialPos = new THREE.Vector3(...data.position);

  useFrame((state, delta) => {
    // Latency-Negative reaction to AST Oracle pulses
    if (meshRef.current) {
      // Scale pulse
      const isFiat = data.type === 'fiat_stream';
      const astPulse = oracleStream.state.mutationPulse;
      const fiatPulse = oracleStream.state.fiatPulse;
      
      const pulseSize = 1 + (astPulse * 0.8) + (isFiat ? fiatPulse * 1.5 : 0);
      meshRef.current.scale.lerp(new THREE.Vector3(pulseSize, pulseSize, pulseSize), delta * 15);
      
      // Spatial distortion on pulse
      if (astPulse > 0 || (isFiat && fiatPulse > 0)) {
        const totalPulse = astPulse + (isFiat ? fiatPulse : 0);
        meshRef.current.position.y = initialPos.y + Math.sin(state.clock.elapsedTime * 10) * totalPulse;
      } else {
        meshRef.current.position.lerp(initialPos, delta * 3);
      }
    }
  });

  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={1}>
      <group position={data.position} ref={meshRef}>
        <mesh>
          <dodecahedronGeometry args={[1.2, 0]} />
          <meshStandardMaterial 
            color={color} 
            emissive={color}
            emissiveIntensity={2}
            wireframe 
          />
        </mesh>
        <Text
          position={[0, -2, 0]}
          fontSize={0.5}
          color="white"
          font="https://fonts.gstatic.com/s/jetbrainsmono/v18/tMe62o-9oZ_U6uL-v8_T_XfFOPhV.woff"
          anchorX="center"
          anchorY="middle"
          fillOpacity={0.4}
        >
          {data.name}
        </Text>
      </group>
    </Float>
  );
}

// Scene lifecycle and Oracle decay
function OracleController() {
  React.useEffect(() => {
    oracleStream.connect();
  }, []);

  useFrame((state, delta) => {
    if (oracleStream.state.mutationPulse > 0) {
      oracleStream.state.mutationPulse -= delta * 1.5; // Decay rate
      if (oracleStream.state.mutationPulse < 0) oracleStream.state.mutationPulse = 0;
    }
    if (oracleStream.state.fiatPulse > 0) {
      oracleStream.state.fiatPulse -= delta * 1.0; // Slower decay for financial events
      if (oracleStream.state.fiatPulse < 0) oracleStream.state.fiatPulse = 0;
    }
  });
  return null;
}

export default function NeuralHive() {
  return (
    <div className="w-full h-full glass-panel rounded-3xl overflow-hidden border-white/5 relative">
      <div className="absolute top-8 left-8 z-10">
        <h3 className="text-2xl font-bold tracking-tighter font-outfit">NEURAL_HIVE_STATIC</h3>
        <p className="text-[10px] font-mono text-cyber-lime tracking-[0.3em] uppercase opacity-60">Memory Stream Active</p>
      </div>
      
      <Canvas camera={{ position: [0, 0, 45], fov: 50 }}>
        <OracleController />
        <color attach="background" args={['#050505']} />
        
        <group>
          {NODES.map((node) => (
            <Node key={node.id} data={node} />
          ))}
          
          {/* Connections between nodes */}
          <Connection start={NODES[0].position} end={NODES[1].position} />
          <Connection start={NODES[0].position} end={NODES[2].position} />
          <Connection start={NODES[0].position} end={NODES[4].position} />
          <Connection start={NODES[1].position} end={NODES[5].position} />
          <Connection start={NODES[2].position} end={NODES[3].position} />
        </group>

        <Environment preset="city" />
        <ContactShadows opacity={0.4} scale={100} blur={1} far={40} />
        
        <EffectComposer>
          <Bloom luminanceThreshold={1} luminanceSmoothing={0.9} height={300} intensity={1.5} />
          <Noise opacity={0.05} />
          <Vignette eskil={false} offset={0.1} darkness={1.1} />
        </EffectComposer>
        
        <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.5} />
      </Canvas>
      {/* Telemetry Overlay */}
      <OracleOverlay />
    </div>
  );
}

function OracleOverlay() {
  const [lastMut, setLastMut] = React.useState<any>(null);
  const [lastFiat, setLastFiat] = React.useState<any>(null);

  React.useEffect(() => {
    const unsubAST = oracleStream.subscribeAST((mut) => {
      setLastMut(mut);
    });
    const unsubFiat = oracleStream.subscribeFiat((tx) => {
      setLastFiat(tx);
    });
    return () => {
      unsubAST();
      unsubFiat();
    };
  }, []);

  if (!lastMut) return null;

  return (
    <div className="absolute top-8 right-8 z-20 text-right font-mono pointer-events-none flex flex-col gap-4">
      {lastMut && (
        <div className="animate-in fade-in slide-in-from-right duration-500">
           <div className="text-[10px] text-cyber-lime tracking-[0.3em] uppercase mb-1 flex items-center justify-end gap-2 animate-pulse">
             <div className="w-1.5 h-1.5 bg-cyber-lime rounded-full" /> AST ORACLE DETECTED MUTATION
           </div>
           <div className="text-white font-bold text-sm tracking-tighter mb-1 bg-black/40 px-2 py-1 border border-white/10 rounded backdrop-blur inline-block">
             {lastMut.meta.file_target.split('/').pop()}
           </div>
           <div className="text-white/40 text-xs">
             Severity: <span className={lastMut.meta.severity === 'MINOR' ? 'text-cyber-lime' : 'text-electric-violet'}>{lastMut.meta.severity}</span>
           </div>
        </div>
      )}

      {lastFiat && (
        <div className="animate-in fade-in slide-in-from-right duration-500">
           <div className="text-[10px] text-[#06d6a0] tracking-[0.3em] uppercase mb-1 flex items-center justify-end gap-2">
             <div className="w-1.5 h-1.5 bg-[#06d6a0] rounded-full" /> FIAT TELEMETRY (BUNQ)
           </div>
           <div className="text-white font-bold text-lg tracking-tighter bg-black/40 px-2 py-1 border border-white/10 rounded backdrop-blur inline-block">
             {lastFiat.meta.amount > 0 ? '+' : ''}{lastFiat.meta.amount} {lastFiat.meta.currency}
           </div>
           <div className="text-white/40 text-[10px] mt-1 uppercase">
             {lastFiat.meta.counterparty}
           </div>
        </div>
      )}
    </div>
  )
}
