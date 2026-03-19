import { gsap } from 'gsap';

export function initScrollMachine({ camera, objectGroup, materials, uniforms }) {
    // La máquina de scroll: GSAP Master Timeline
    const hero = gsap.timeline({
        scrollTrigger: {
            trigger: '.hero-section',
            start: 'top top',
            end: '+=800%',      // 8 viewports (ultra precision)
            scrub: 1.5,         // Inercia cinematográfica F1/Norris
            pin: true,
            fastScrollEnd: true,
            onUpdate: (self) => {
                // Capturamos la velocidad cruda del scroll (píxeles por segundo)
                const velocity = Math.abs(self.getVelocity());
                // Mapeamos la velocidad a intensidad de aberración (max 4.0)
                // Usamos un clamp sutil para que scrolls normales den un 0.5-1.0
                // y un flick brutal del trackpad dispare hasta 4.0
                const targetDistortion = Math.min(velocity / 800, 4.0);
                
                // Tweeneamos al valor objetivo rápido para suavizar el input rudo del sensor
                gsap.to(uniforms.chroma.uDistortion, {
                    value: targetDistortion,
                    duration: 0.2, // smoothing kinetic
                    ease: 'power3.out',
                    overwrite: 'auto'
                });
            }
        }
    });

    // --- CAPA 0: CSS BACKGROUND AMBIENCE --- //
    hero.to('.bg-gradient', {
        background: 'radial-gradient(ellipse at 50% 30%, #151d00 0%, #000000 70%)', // Verde oscuro cyber lime bleeding
        ease: 'none'
    }, 0);
    
    hero.fromTo('.noise-layer', { opacity: 0.03 }, { opacity: 0.12 }, 0);
    hero.fromTo('.scanlines', { opacity: 0.05 }, { opacity: 0.3 }, 0.5);

    // --- CAPA 1: TIPOGRAFÍA KINETICA --- //
    const chars = gsap.utils.toArray('.hero-title .char');
    
    // Title Reveal (1.0) - MOT 10 Bezier Flight
    hero.to(chars, {
        motionPath: {
            path: [
                { xPercent: 0, yPercent: 40 },
                { xPercent: -30, yPercent: -50 },
                { xPercent: 0, yPercent: -150 }
            ],
            curviness: 1.2
        },
        opacity: 1,
        color: '#ffffff',
        stagger: 0.02, // delay microscópico letra a letra
        ease: 'expo.out', // Razor sharp
        textShadow: '0 0 30px rgba(204,255,0, 0.8)' // Cyber lime blast
    }, 0.05);

    // "2026" Watermark Parallax
    hero.fromTo('.stat-number', 
        { scale: 0.9, opacity: 0.02, yPercent: 10 },
        { scale: 1.3, opacity: 0.06, yPercent: -40, ease: 'power2.inOut' }, 0);

    // Subtitle Cyber Lime Glitch Fade in
    hero.to('.subtitle', { opacity: 1, y: -30, letterSpacing: '0.8em', ease: 'power3.out' }, 0.2);

    // Letterbox Cinematic Close
    hero.to('.letterbox-top', { scaleY: 1, ease: 'expo.inOut' }, 0.6);
    hero.to('.letterbox-bottom', { scaleY: 1, ease: 'expo.inOut' }, 0.6);

    // --- CAPA 2: WEBGL & 3D KINETICS --- //
    
    // Core Object Matrix Motion - MOT 10 Helmet Orbit
    hero.to(objectGroup.rotation, {
        motionPath: {
            path: [
                { x: 0, y: 0, z: 0 },
                { x: Math.PI / 2, y: -Math.PI, z: 0.5 },
                { x: -Math.PI / 4, y: Math.PI * 2, z: -0.2 },
                { x: 0, y: Math.PI * 3, z: 0 }
            ],
            curviness: 1.0
        },
        ease: 'power4.inOut'
    }, 0);

    hero.to(objectGroup.position, {
        motionPath: {
            path: [
                { x: 0, y: 0, z: 0 },
                { x: 2.5, y: 1.0, z: -1.0 },
                { x: -2.0, y: -1.0, z: 1.5 },
                { x: 0, y: 0, z: 0.5 }
            ],
            curviness: 1.0
        },
        ease: 'power4.inOut'
    }, 0);

    // Modificamos el Mesh Deformation (uSpike)
    hero.to(uniforms.core.uSpike, {
        value: 1.5,
        ease: 'power2.inOut'
    }, 0);

    // Fresnel Edge Glow Intensity (uIntensity)
    hero.to(uniforms.core.uIntensity, {
        value: 4.5, // Pasa de 0.5 a un glow masivo
        ease: 'power3.in'
    }, 0.2);

    // Procedural Wireframe Overlay Fade In
    hero.to(uniforms.core.uWireframeOpacity, {
        value: 0.8,
        ease: 'power2.inOut'
    }, 0.3);

    // --- CAPA 3: POST PROCESSING COMPOSER --- //

    // Bloom Strength Overshoot (Neon Burst)
    hero.to(uniforms.bloom, {
        strength: 3.5,
        radius: 1.2,
        ease: 'power3.out'
    }, 0.2);

    hero.to(uniforms.bloom, {
        strength: 1.0, 
        ease: 'power2.in'
    }, 0.6);

    // [ELIMINADO] Chromatic Aberration Glitch Spikes
    // La aberración cromática ahora se calcula procedimentalmente en `onUpdate` guiada
    // por la velocidad pura del ratón/scroll, no por posiciones estáticas en el timeline.
    
    // --- CAPA 4: CÁMARA & SALIDA --- //
    
    // Orbital MotionPath for Camera - MOT 10 Cinematic Sweep
    hero.to(camera.position, {
        motionPath: {
            path: [
                { x: 0, y: 0, z: camera.position.z },
                { x: -2.0, y: 1.5, z: 3.0 },
                { x: 1.5, y: -0.8, z: 0.2 },
                { x: 0, y: 0, z: 0.5 }
            ],
            curviness: 1.2
        },
        ease: 'expo.inOut'
    }, 0.4);

    hero.to(camera.rotation, {
        motionPath: {
            path: [
                { x: 0, y: 0, z: 0 },
                { x: 0.3, y: -0.4, z: 0.15 },
                { x: -0.2, y: 0.3, z: -0.1 },
                { x: 0, y: 0, z: 0 }
            ],
            curviness: 1.2
        },
        ease: 'expo.inOut'
    }, 0.4);

    // Title Shatter Out
    hero.to(chars, {
        yPercent: -250,
        opacity: 0,
        rotationZ: () => Math.random() * 30 - 15,
        rotationX: 90,
        stagger: 0.02,
        ease: 'power3.in'
    }, 0.7);
    
    hero.to('.subtitle', { opacity: 0, letterSpacing: '2em' }, 0.7);
    
    // Fade to Black absoluto final
    hero.to(uniforms.core.uColorGlow.value, { 
        r: 0, g: 0, b: 0, ease: 'power2.in' 
    }, 0.8);
}
