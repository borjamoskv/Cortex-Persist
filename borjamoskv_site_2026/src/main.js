import './style.css';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { MotionPathPlugin } from 'gsap/MotionPathPlugin';
import { initWebGL } from './webgl.js';
import { initScrollMachine } from './scroll-machine.js';

gsap.registerPlugin(ScrollTrigger, MotionPathPlugin);

document.addEventListener('DOMContentLoaded', () => {
    // 1. Iniciar pipeline WebGL (Retorna objetos para controlar desde GSAP)
    const { camera, objectGroup, materials, uniforms } = initWebGL();
    
    // 2. Iniciar coreografía de scroll
    initScrollMachine({
        camera, objectGroup, materials, uniforms
    });
});
