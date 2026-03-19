import * as THREE from 'three';
import * as CANNON from 'cannon-es';
import InputManager from './Input/InputManager.js';
import Vehicle from './Physics/Vehicle.js';
import ChaseCamera from './Camera/ChaseCamera.js';
import DJZone from './DJZone.js';

export default class Game {
    constructor(canvas) {
        this.canvas = canvas;
        
        // Setup Three.js
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color('#1a1a1a'); // Industrial Noir aesthetic

        this.sizes = {
            width: window.innerWidth,
            height: window.innerHeight
        };

        this.camera = new THREE.PerspectiveCamera(75, this.sizes.width / this.sizes.height, 0.1, 1000);
        this.camera.position.set(0, 5, 10);
        this.scene.add(this.camera);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true
        });
        this.renderer.setSize(this.sizes.width, this.sizes.height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        // Setup Cannon-es
        this.world = new CANNON.World();
        this.world.broadphase = new CANNON.SAPBroadphase(this.world);
        this.world.gravity.set(0, -9.82, 0); // Earth gravity
        this.world.defaultContactMaterial.friction = 0.1;

        // Input
        this.input = new InputManager();

        // Time
        this.clock = new THREE.Clock();
        this.previousTime = 0;

        // Resize handler
        window.addEventListener('resize', () => this.resize());

        // Basic Lighting
        this.setupLighting();

        // Placeholder items for testing physics
        this.createPlaceholderEnvironment();

        // Start Loop
        this.tick();
    }

    setupLighting() {
        const ambientLight = new THREE.AmbientLight('#ffffff', 0.5);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight('#ffffff', 2);
        directionalLight.position.set(5, 10, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 1024;
        directionalLight.shadow.mapSize.height = 1024;
        this.scene.add(directionalLight);
    }

    createPlaceholderEnvironment() {
        // Simple Floor (Visual + Physics)
        const floorShape = new CANNON.Plane();
        const floorBody = new CANNON.Body({
            mass: 0, // static
            shape: floorShape
        });
        floorBody.quaternion.setFromAxisAngle(new CANNON.Vec3(-1, 0, 0), Math.PI * 0.5);
        this.world.addBody(floorBody);

        const floorMesh = new THREE.Mesh(
            new THREE.PlaneGeometry(200, 200),
            new THREE.MeshStandardMaterial({ 
                color: '#222222',
                roughness: 0.8,
            })
        );
        floorMesh.rotation.x = -Math.PI * 0.5;
        floorMesh.receiveShadow = true;
        this.scene.add(floorMesh);

        // Grid Helper
        const gridHelper = new THREE.GridHelper(200, 200, '#444444', '#1a1a1a');
        this.scene.add(gridHelper);

        // Instantiate Player Vehicle
        this.vehicle = new Vehicle(this.scene, this.world, this.input);

        // Instantiate Chase Camera
        this.chaseCamera = new ChaseCamera(this.camera, this.vehicle.chassisBody);

        // Instantiate DJ Zone
        this.djZone = new DJZone(this.scene, this.world, { x: -20, y: 0, z: -20 });
    }

    resize() {
        this.sizes.width = window.innerWidth;
        this.sizes.height = window.innerHeight;

        this.camera.aspect = this.sizes.width / this.sizes.height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(this.sizes.width, this.sizes.height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    }

    tick() {
        const elapsedTime = this.clock.getElapsedTime();
        const deltaTime = elapsedTime - this.previousTime;
        this.previousTime = elapsedTime;

        // Step physics world
        this.world.step(1 / 60, deltaTime, 3);

        // Update Vehicle Physics & Visuals
        if (this.vehicle) {
            this.vehicle.update();
        }

        // Update Chase Camera
        if (this.chaseCamera) {
            this.chaseCamera.update();
        }

        // Update DJ Zone
        if (this.djZone && this.vehicle) {
            this.djZone.update(this.vehicle.chassisBody.position);
        }

        // Render
        this.renderer.render(this.scene, this.camera);

        window.requestAnimationFrame(() => this.tick());
    }
}
