import * as THREE from 'three';
import * as CANNON from 'cannon-es';

export default class DJZone {
    constructor(scene, world, position = { x: -20, y: 0, z: -20 }) {
        this.scene = scene;
        this.world = world;
        this.position = position;

        this.isActive = false;

        this.createVisuals();
        this.createPhysics();
        this.createText();
        this.createLight();
    }

    createVisuals() {
        this.group = new THREE.Group();
        this.group.position.set(this.position.x, this.position.y, this.position.z);

        // DJ Table
        const tableGeo = new THREE.BoxGeometry(4, 1.2, 1.5);
        const tableMat = new THREE.MeshStandardMaterial({ color: '#111111', roughness: 0.2 });
        this.tableMesh = new THREE.Mesh(tableGeo, tableMat);
        this.tableMesh.position.y = 0.6;
        this.tableMesh.castShadow = true;
        this.tableMesh.receiveShadow = true;
        this.group.add(this.tableMesh);

        // Decks
        const deckGeo = new THREE.BoxGeometry(1.2, 0.1, 1);
        const deckMat = new THREE.MeshStandardMaterial({ color: '#222222', roughness: 0.5 });
        const deck1 = new THREE.Mesh(deckGeo, deckMat);
        deck1.position.set(-1, 1.25, 0);
        const deck2 = new THREE.Mesh(deckGeo, deckMat);
        deck2.position.set(1, 1.25, 0);
        this.group.add(deck1, deck2);

        // Mixer
        const mixerGeo = new THREE.BoxGeometry(0.8, 0.15, 1);
        const mixerMat = new THREE.MeshStandardMaterial({ color: '#333333', roughness: 0.4 });
        const mixer = new THREE.Mesh(mixerGeo, mixerMat);
        mixer.position.set(0, 1.25, 0);
        this.group.add(mixer);

        // Speakers
        const speakerGeo = new THREE.BoxGeometry(1.5, 3, 1.5);
        this.speakerMat = new THREE.MeshStandardMaterial({ 
            color: '#050505', 
            emissive: '#1a1a1a', 
            emissiveIntensity: 0.1,
            roughness: 0.8 
        });
        
        this.speakerLeft = new THREE.Mesh(speakerGeo, this.speakerMat);
        this.speakerLeft.position.set(-4, 1.5, -1);
        this.speakerLeft.castShadow = true;
        
        this.speakerRight = new THREE.Mesh(speakerGeo, this.speakerMat);
        this.speakerRight.position.set(4, 1.5, -1);
        this.speakerRight.castShadow = true;

        this.group.add(this.speakerLeft, this.speakerRight);

        // Platform
        const platformGeo = new THREE.CylinderGeometry(6, 6, 0.2, 32);
        const platformMat = new THREE.MeshStandardMaterial({ color: '#0a0a0a' });
        const platform = new THREE.Mesh(platformGeo, platformMat);
        platform.position.y = 0.1;
        platform.receiveShadow = true;
        this.group.add(platform);

        this.scene.add(this.group);
    }

    createPhysics() {
        // Table physics
        const tableShape = new CANNON.Box(new CANNON.Vec3(2, 0.6, 0.75));
        this.tableBody = new CANNON.Body({ mass: 0 }); // static
        this.tableBody.addShape(tableShape);
        this.tableBody.position.set(this.position.x, 0.6, this.position.z);
        this.world.addBody(this.tableBody);

        // Speakers physics
        const speakerShape = new CANNON.Box(new CANNON.Vec3(0.75, 1.5, 0.75));
        
        const speakerLeftBody = new CANNON.Body({ mass: 0 });
        speakerLeftBody.addShape(speakerShape);
        speakerLeftBody.position.set(this.position.x - 4, 1.5, this.position.z - 1);
        this.world.addBody(speakerLeftBody);
        
        const speakerRightBody = new CANNON.Body({ mass: 0 });
        speakerRightBody.addShape(speakerShape);
        speakerRightBody.position.set(this.position.x + 4, 1.5, this.position.z - 1);
        this.world.addBody(speakerRightBody);
    }

    createText() {
        // Simple DOM text overlay instead of 3D Text geometry to save performance and logic
        this.textElement = document.createElement('div');
        this.textElement.innerText = "DJ SKILLS\nIDM & DARK DISCO";
        this.textElement.style.position = 'absolute';
        this.textElement.style.top = '20%';
        this.textElement.style.left = '50%';
        this.textElement.style.transform = 'translate(-50%, -50%)';
        this.textElement.style.color = '#CCFF00';
        this.textElement.style.fontFamily = '"Courier New", monospace';
        this.textElement.style.fontSize = '3rem';
        this.textElement.style.fontWeight = 'bold';
        this.textElement.style.textAlign = 'center';
        this.textElement.style.textShadow = '0 0 10px #CCFF00';
        this.textElement.style.pointerEvents = 'none';
        this.textElement.style.opacity = '0';
        this.textElement.style.transition = 'opacity 0.5s ease-in-out';
        this.textElement.style.zIndex = '1000';
        document.body.appendChild(this.textElement);
    }

    createLight() {
        this.boothLight = new THREE.PointLight('#CCFF00', 0, 15);
        this.boothLight.position.set(0, 3, 0);
        this.group.add(this.boothLight);
    }

    update(vehiclePosition) {
        // Measure distance to vehicle
        const dx = vehiclePosition.x - this.position.x;
        const dz = vehiclePosition.z - this.position.z;
        const distance = Math.sqrt(dx * dx + dz * dz);

        // Interaction radius
        const threshold = 12;

        if (distance < threshold) {
            if (!this.isActive) {
                this.isActive = true;
                this.textElement.style.opacity = '1';
            }
            // Pulse effect
            const time = performance.now() * 0.005;
            const intensity = (Math.sin(time) * 0.5 + 0.5);
            this.boothLight.intensity = intensity * 10;
            this.speakerMat.emissiveIntensity = intensity * 0.8;
            
            // Subwoofer vibration
            const scale = 1 + (intensity * 0.05);
            this.speakerLeft.scale.set(scale, scale, scale);
            this.speakerRight.scale.set(scale, scale, scale);
        } else {
            if (this.isActive) {
                this.isActive = false;
                this.textElement.style.opacity = '0';
                this.boothLight.intensity = 0;
                this.speakerMat.emissiveIntensity = 0.1;
                this.speakerLeft.scale.set(1, 1, 1);
                this.speakerRight.scale.set(1, 1, 1);
            }
        }
    }
}
