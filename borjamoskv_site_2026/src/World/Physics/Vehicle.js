import * as THREE from 'three';
import * as CANNON from 'cannon-es';

export default class Vehicle {
    constructor(scene, world, inputManager) {
        this.scene = scene;
        this.world = world;
        this.inputManager = inputManager;

        this.chassisMesh = null;
        this.wheelMeshes = [];

        this.createPhysicsBody();
        this.setupVisuals();
    }

    createPhysicsBody() {
        // Chassis Body
        const chassisShape = new CANNON.Box(new CANNON.Vec3(1, 0.5, 2));
        this.chassisBody = new CANNON.Body({ mass: 150 });
        this.chassisBody.addShape(chassisShape, new CANNON.Vec3(0, 0, 0));
        this.chassisBody.position.set(0, 4, 0);

        // Vehicle Setup using RaycastVehicle
        const options = {
            radius: 0.5,
            directionLocal: new CANNON.Vec3(0, -1, 0),
            suspensionStiffness: 30,
            suspensionRestLength: 0.3,
            frictionSlip: 5,
            dampingRelaxation: 2.3,
            dampingCompression: 4.4,
            maxSuspensionForce: 100000,
            rollInfluence: 0.01,
            axleLocal: new CANNON.Vec3(-1, 0, 0),
            chassisConnectionPointLocal: new CANNON.Vec3(1, 1, 0),
            maxSuspensionTravel: 0.3,
            customSlidingRotationalSpeed: -30,
            useCustomSlidingRotationalSpeed: true
        };

        this.vehicle = new CANNON.RaycastVehicle({
            chassisBody: this.chassisBody,
            indexRightAxis: 0,
            indexUpAxis: 1,
            indexForwardAxis: 2
        });

        const wheelOptions = [
            // Front Left
            { chassisConnectionPointLocal: new CANNON.Vec3(-1, 0, -1.2), isFrontWheel: true },
            // Front Right
            { chassisConnectionPointLocal: new CANNON.Vec3(1, 0, -1.2), isFrontWheel: true },
            // Back Left
            { chassisConnectionPointLocal: new CANNON.Vec3(-1, 0, 1.2), isFrontWheel: false },
            // Back Right
            { chassisConnectionPointLocal: new CANNON.Vec3(1, 0, 1.2), isFrontWheel: false }
        ];

        wheelOptions.forEach(opt => {
            this.vehicle.addWheel({
                ...options,
                chassisConnectionPointLocal: opt.chassisConnectionPointLocal
            });
        });

        this.vehicle.addToWorld(this.world);

        // Wheel Bodies (Visual syncing needed)
        this.wheelBodies = [];
        const wheelShape = new CANNON.Cylinder(options.radius, options.radius, options.radius / 2, 20);
        
        for (let i = 0; i < this.vehicle.wheelInfos.length; i++) {
            const wheelBody = new CANNON.Body({ mass: 1, type: CANNON.Body.KINEMATIC, collisionFilterGroup: 0 }); // Kinematic to let RaycastVehicle handle it
            const q = new CANNON.Quaternion();
            q.setFromAxisAngle(new CANNON.Vec3(1, 0, 0), Math.PI / 2); // Rotate cylinder
            wheelBody.addShape(wheelShape, new CANNON.Vec3(), q);
            this.world.addBody(wheelBody);
            this.wheelBodies.push(wheelBody);
        }

        // Update wheel bodies during physical tick
        this.world.addEventListener('postStep', () => {
            for (let i = 0; i < this.vehicle.wheelInfos.length; i++) {
                this.vehicle.updateWheelTransform(i);
                const transform = this.vehicle.wheelInfos[i].worldTransform;
                this.wheelBodies[i].position.copy(transform.position);
                this.wheelBodies[i].quaternion.copy(transform.quaternion);
            }
        });
    }

    setupVisuals() {
        // Chassis Visual Placeholder
        const chassisGeometry = new THREE.BoxGeometry(2, 1, 4);
        const chassisMaterial = new THREE.MeshStandardMaterial({ color: '#CCFF00' }); // Cyber lime
        this.chassisMesh = new THREE.Mesh(chassisGeometry, chassisMaterial);
        this.chassisMesh.castShadow = true;
        this.scene.add(this.chassisMesh);

        // Wheels Visuals
        const wheelGeometry = new THREE.CylinderGeometry(0.5, 0.5, 0.25, 20);
        wheelGeometry.rotateZ(Math.PI / 2); // align with cannon body
        const wheelMaterial = new THREE.MeshStandardMaterial({ color: '#222222', wireframe: true });

        for (let i = 0; i < 4; i++) {
            const mesh = new THREE.Mesh(wheelGeometry, wheelMaterial);
            mesh.castShadow = true;
            this.scene.add(mesh);
            this.wheelMeshes.push(mesh);
        }
    }

    update() {
        // Apply Physics Controls
        const maxSteerVal = 0.5;
        const maxForce = 500;
        const brakeForce = 15;

        // Reset
        this.vehicle.setSteeringValue(0, 0);
        this.vehicle.setSteeringValue(0, 1);
        this.vehicle.applyEngineForce(0, 2);
        this.vehicle.applyEngineForce(0, 3);
        this.vehicle.setBrake(0, 0);
        this.vehicle.setBrake(0, 1);
        this.vehicle.setBrake(0, 2);
        this.vehicle.setBrake(0, 3);

        if (this.inputManager.keys.forward) {
            this.vehicle.applyEngineForce(-maxForce, 2);
            this.vehicle.applyEngineForce(-maxForce, 3);
        }
        if (this.inputManager.keys.backward) {
            this.vehicle.applyEngineForce(maxForce, 2);
            this.vehicle.applyEngineForce(maxForce, 3);
        }
        
        let steerValue = 0;
        if (this.inputManager.keys.left) steerValue = maxSteerVal;
        if (this.inputManager.keys.right) steerValue = -maxSteerVal;
        
        this.vehicle.setSteeringValue(steerValue, 0);
        this.vehicle.setSteeringValue(steerValue, 1);

        if (this.inputManager.keys.brake) {
            this.vehicle.setBrake(brakeForce, 0);
            this.vehicle.setBrake(brakeForce, 1);
            this.vehicle.setBrake(brakeForce, 2);
            this.vehicle.setBrake(brakeForce, 3);
        }

        // Sync Visuals
        if (this.chassisMesh && this.chassisBody) {
            this.chassisMesh.position.copy(this.chassisBody.position);
            this.chassisMesh.quaternion.copy(this.chassisBody.quaternion);
        }

        for (let i = 0; i < 4; i++) {
            if (this.wheelMeshes[i] && this.wheelBodies[i]) {
                this.wheelMeshes[i].position.copy(this.wheelBodies[i].position);
                this.wheelMeshes[i].quaternion.copy(this.wheelBodies[i].quaternion);
            }
        }
    }
}
