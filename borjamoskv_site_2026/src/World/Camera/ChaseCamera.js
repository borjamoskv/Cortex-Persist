import * as THREE from 'three';

export default class ChaseCamera {
    constructor(camera, target) {
        this.camera = camera;
        this.target = target; // expects a CANNON.Body or THREE.Mesh

        this.currentPosition = new THREE.Vector3();
        this.currentLookAt = new THREE.Vector3();
        
        // Settings for cinematic feel
        this.positionOffset = new THREE.Vector3(0, 5, 10);
        this.lookAtOffset = new THREE.Vector3(0, 0, -5);
        this.lerpFactor = 0.05;
    }

    update() {
        if (!this.target) return;

        // Calculate ideal position behind the target based on its rotation
        const idealPosition = new THREE.Vector3().copy(this.positionOffset);
        idealPosition.applyQuaternion(this.target.quaternion);
        idealPosition.add(this.target.position);

        // Calculate what the camera should look at
        const idealLookAt = new THREE.Vector3().copy(this.lookAtOffset);
        idealLookAt.applyQuaternion(this.target.quaternion);
        idealLookAt.add(this.target.position);

        // Lerp for smoothness
        this.currentPosition.lerp(idealPosition, this.lerpFactor);
        this.currentLookAt.lerp(idealLookAt, this.lerpFactor);

        this.camera.position.copy(this.currentPosition);
        this.camera.lookAt(this.currentLookAt);
    }
}
