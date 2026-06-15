import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function HeroCanvas() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // Three.js setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);

    // Network Particles (Swarm Nodes)
    const particlesCount = 400; // Optimal for O(N^2) distance calculations
    const positions = new Float32Array(particlesCount * 3);
    const velocities: { x: number; y: number; z: number }[] = [];

    for (let i = 0; i < particlesCount; i++) {
      // Spread nodes in a sphere-like area
      positions[i * 3] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
      
      // Gentle drift velocities
      velocities.push({
        x: (Math.random() - 0.5) * 0.015,
        y: (Math.random() - 0.5) * 0.015,
        z: (Math.random() - 0.5) * 0.015,
      });
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    // Material matching Industrial Noir aesthetic (YInMn Blue)
    const material = new THREE.PointsMaterial({
      size: 0.04,
      color: 0x2b3be5, // YInMn Blue Accent
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending
    });

    const particlesMesh = new THREE.Points(geometry, material);
    scene.add(particlesMesh);

    // Cryptographic Hash-Chains (Connecting Lines)
    const linesGeometry = new THREE.BufferGeometry();
    // Maximum possible connections = N * (N - 1) / 2
    const maxConnections = (particlesCount * (particlesCount - 1)) / 2;
    const linePositions = new Float32Array(maxConnections * 6);
    
    // We use dynamic draw hint if possible
    const posAttribute = new THREE.BufferAttribute(linePositions, 3);
    linesGeometry.setAttribute('position', posAttribute);

    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x2b3be5,
      transparent: true,
      opacity: 0.15,
      blending: THREE.AdditiveBlending
    });

    const linesMesh = new THREE.LineSegments(linesGeometry, lineMaterial);
    scene.add(linesMesh);

    camera.position.z = 4;

    // Mouse interaction parallax
    let mouseX = 0;
    let mouseY = 0;
    const windowHalfX = window.innerWidth / 2;
    const windowHalfY = window.innerHeight / 2;

    const onDocumentMouseMove = (event: MouseEvent) => {
      mouseX = (event.clientX - windowHalfX);
      mouseY = (event.clientY - windowHalfY);
    };

    document.addEventListener('mousemove', onDocumentMouseMove);

    // Resize handler
    const onWindowResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', onWindowResize);

    // Animation loop (Swarm Consensus)
    const animate = () => {
      requestAnimationFrame(animate);
      
      let vertexpos = 0;
      let numConnected = 0;

      // Kintsugi Kinetic: Pulsing and moving
      for (let i = 0; i < particlesCount; i++) {
        const i3 = i * 3;
        // Drift
        positions[i3] += velocities[i].x;
        positions[i3 + 1] += velocities[i].y;
        positions[i3 + 2] += velocities[i].z;
        
        // Bounding box bounce
        if (Math.abs(positions[i3]) > 5) velocities[i].x *= -1;
        if (Math.abs(positions[i3 + 1]) > 5) velocities[i].y *= -1;
        if (Math.abs(positions[i3 + 2]) > 5) velocities[i].z *= -1;
        
        // Calculate hash-chain links (distances)
        for (let j = i + 1; j < particlesCount; j++) {
          const j3 = j * 3;
          const dx = positions[i3] - positions[j3];
          const dy = positions[i3 + 1] - positions[j3 + 1];
          const dz = positions[i3 + 2] - positions[j3 + 2];
          const distSq = dx*dx + dy*dy + dz*dz;
          
          // Connect nodes if they are close enough
          if (distSq < 2.5) {
            linePositions[vertexpos++] = positions[i3];
            linePositions[vertexpos++] = positions[i3 + 1];
            linePositions[vertexpos++] = positions[i3 + 2];
            
            linePositions[vertexpos++] = positions[j3];
            linePositions[vertexpos++] = positions[j3 + 1];
            linePositions[vertexpos++] = positions[j3 + 2];
            numConnected++;
          }
        }
      }
      
      // Update buffers
      linesMesh.geometry.setDrawRange(0, numConnected * 2);
      linesMesh.geometry.attributes.position.needsUpdate = true;
      particlesMesh.geometry.attributes.position.needsUpdate = true;

      // Parallax rotation
      const targetX = mouseX * 0.0005;
      const targetY = mouseY * 0.0005;

      scene.rotation.y += 0.05 * (targetX - scene.rotation.y);
      scene.rotation.x += 0.05 * (targetY - scene.rotation.x);
      
      // Slow constant spin
      scene.rotation.y += 0.001;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      document.removeEventListener('mousemove', onDocumentMouseMove);
      window.removeEventListener('resize', onWindowResize);
      if (mountRef.current) {
        mountRef.current.removeChild(renderer.domElement);
      }
      geometry.dispose();
      linesGeometry.dispose();
      material.dispose();
      lineMaterial.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div 
      ref={mountRef} 
      style={{ 
        position: 'absolute', 
        top: 0, 
        left: 0, 
        width: '100%', 
        height: '100%', 
        zIndex: 0,
        pointerEvents: 'none',
        opacity: 0.7
      }} 
      aria-hidden="true"
    />
  );
}
