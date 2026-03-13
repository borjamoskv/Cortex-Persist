import * as THREE from 'three';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';

gsap.registerPlugin(ScrollTrigger);

export class SovereignRenderEngine {
  constructor(canvasElement) {
    this.canvas = canvasElement;
    this.time = 0;
    this.dimensions = { width: window.innerWidth, height: window.innerHeight };
    
    // Mouse coords normalized (-1 to 1)
    this.mouse = new THREE.Vector2(0, 0);
    this.targetMouse = new THREE.Vector2(0, 0);

    this.initScene();
    this.initScroll();
    this.injectInteractiveGeometry();
    this.bindEvents();
    this.start();
  }

  initScene() {
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance"
    });
    this.renderer.setSize(this.dimensions.width, this.dimensions.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    this.scene = new THREE.Scene();
    
    // Add subtle ambient light and a directional light for specular hits
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
    this.scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.5);
    directionalLight.position.set(5, 5, 2);
    this.scene.add(directionalLight);

    this.camera = new THREE.PerspectiveCamera(
      45, this.dimensions.width / this.dimensions.height, 0.1, 1000
    );
    this.camera.position.z = 10;
  }

  initScroll() {
    this.lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    });

    this.lenis.on('scroll', ScrollTrigger.update);

    gsap.ticker.add((time) => {
      this.lenis.raf(time * 1000);
    });
    gsap.ticker.lagSmoothing(0);
  }

  injectInteractiveGeometry() {
    // 1. Core Object: A wireframe icosahedron complex
    const geometry = new THREE.IcosahedronGeometry(2, 2);
    
    // Sovereign Material
    this.solidMaterial = new THREE.MeshStandardMaterial({
      color: 0x0A0A0A,
      roughness: 0.1,
      metalness: 0.8,
    });
    
    this.wireframeMaterial = new THREE.MeshBasicMaterial({
      color: 0xCCFF00, // Cyber Lime
      wireframe: true,
      transparent: true,
      opacity: 0.15
    });

    this.coreMesh = new THREE.Mesh(geometry, this.solidMaterial);
    const wireframeMesh = new THREE.Mesh(geometry, this.wireframeMaterial);
    
    // Slightly scale up wireframe to avoide z-fighting
    wireframeMesh.scale.set(1.01, 1.01, 1.01);
    this.coreMesh.add(wireframeMesh);
    
    this.scene.add(this.coreMesh);

    // 2. Particle Field (Sovereign Dust)
    const particleGeometry = new THREE.BufferGeometry();
    const particleCount = 2000;
    const posArray = new Float32Array(particleCount * 3);
    
    for(let i = 0; i < particleCount * 3; i++) {
      // Spread across a 20x20x20 cube
      posArray[i] = (Math.random() - 0.5) * 20;
    }
    
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    
    const particleMaterial = new THREE.PointsMaterial({
      size: 0.02,
      color: 0x999999,
      transparent: true,
      opacity: 0.5,
      blending: THREE.AdditiveBlending
    });
    
    this.particles = new THREE.Points(particleGeometry, particleMaterial);
    this.scene.add(this.particles);

    // 3. Setup ScrollTriggers for GSAP linking
    // As the user scrolls, the object rotates and scales down
    ScrollTrigger.create({
      trigger: ".app-container",
      start: "top top",
      end: "bottom bottom",
      scrub: 1, // Smooth scrubbing
      onUpdate: (self) => {
        // self.progress goes from 0 to 1
        const progress = self.progress;
        
        // Rotate geometry based on scroll
        gsap.to(this.coreMesh.rotation, {
          x: progress * Math.PI * 2,
          y: progress * Math.PI * 4,
          duration: 0.5,
          ease: "power2.out"
        });
        
        // Push object back in Z space
        gsap.to(this.coreMesh.position, {
          y: progress * 5, // Moves up out of frame
          z: -progress * 10,
          duration: 0.5,
          ease: "power2.out"
        });
      }
    });
  }

  onMouseMove(e) {
    // Normalize coordinates
    this.targetMouse.x = (e.clientX / this.dimensions.width) * 2 - 1;
    this.targetMouse.y = -(e.clientY / this.dimensions.height) * 2 + 1;
  }

  resize() {
    this.dimensions.width = window.innerWidth;
    this.dimensions.height = window.innerHeight;
    this.renderer.setSize(this.dimensions.width, this.dimensions.height);
    this.camera.aspect = this.dimensions.width / this.dimensions.height;
    this.camera.updateProjectionMatrix();
  }

  bindEvents() {
    window.addEventListener('resize', () => this.resize());
    window.addEventListener('mousemove', (e) => this.onMouseMove(e));
  }

  render() {
    this.time += 0.01;
    
    // Smooth damp mouse position (lerp)
    this.mouse.x += (this.targetMouse.x - this.mouse.x) * 0.05;
    this.mouse.y += (this.targetMouse.y - this.mouse.y) * 0.05;

    // Continuous idle rotation
    if (this.coreMesh) {
      this.coreMesh.rotation.y += 0.002;
      this.coreMesh.rotation.x += 0.001;
      
      // Mouse interaction: geometry tilts towards mouse
      this.coreMesh.rotation.x += this.mouse.y * 0.05;
      this.coreMesh.rotation.y += this.mouse.x * 0.05;
    }

    // Parallax effect on particles driven by mouse
    if (this.particles) {
      this.particles.rotation.y = this.mouse.x * 0.2 + this.time * 0.05;
      this.particles.rotation.x = -this.mouse.y * 0.2;
    }

    this.renderer.render(this.scene, this.camera);
    this.rafId = requestAnimationFrame(() => this.render());
  }

  start() {
    this.render();
  }

  destroy() {
    cancelAnimationFrame(this.rafId);
    this.lenis.destroy();
    this.renderer.dispose();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('webgl-canvas');
  window.engine = new SovereignRenderEngine(canvas);

  gsap.fromTo('.hero-text', 
    { y: 50, opacity: 0 }, 
    { y: 0, opacity: 1, duration: 1.5, ease: 'power3.out', delay: 0.2 }
  );
  gsap.fromTo('.subtitle', 
    { y: 20, opacity: 0 }, 
    { y: 0, opacity: 1, duration: 1, ease: 'power3.out', delay: 0.8 }
  );

  const cursor = document.querySelector('.cursor');
  let cursorX = window.innerWidth / 2;
  let cursorY = window.innerHeight / 2;
  let targetX = cursorX;
  let targetY = cursorY;

  window.addEventListener('mousemove', (e) => {
    targetX = e.clientX;
    targetY = e.clientY;
  });

  function updateCursor() {
    cursorX += (targetX - cursorX) * 0.15;
    cursorY += (targetY - cursorY) * 0.15;
    gsap.set(cursor, { x: cursorX, y: cursorY });
    requestAnimationFrame(updateCursor);
  }
  updateCursor();
});
