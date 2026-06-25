/**
 * C5-REAL GAME LOGIC
 */

const canvas = document.getElementById('c5-canvas');
const ctx = canvas.getContext('2d');
const fpsCounter = document.getElementById('fps-counter');
const entityCounter = document.getElementById('entity-counter');

let width, height;
function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
}
window.addEventListener('resize', resize);
resize();

// Player state
const player = { x: width/2, y: height/2, vx: 0, vy: 0, speed: 200 };
const keys = { w: false, a: false, s: false, d: false };

window.addEventListener('keydown', (e) => {
    if (keys.hasOwnProperty(e.key.toLowerCase())) keys[e.key.toLowerCase()] = true;
});
window.addEventListener('keyup', (e) => {
    if (keys.hasOwnProperty(e.key.toLowerCase())) keys[e.key.toLowerCase()] = false;
});

// Shockwave (FGD-055 Repulsion Field concept)
window.addEventListener('mousedown', (e) => {
    const mx = e.clientX;
    const my = e.clientY;
    const SHOCK_RADIUS = 250;
    const SHOCK_FORCE = 15;
    
    for (let i = 0; i < ECS.MAX_ENTITIES; i++) {
        if (!ECS.active[i]) continue;
        const dx = ECS.positionsX[i] - mx;
        const dy = ECS.positionsY[i] - my;
        const distSq = dx*dx + dy*dy;
        
        if (distSq < SHOCK_RADIUS*SHOCK_RADIUS && distSq > 0) {
            const dist = Math.sqrt(distSq);
            const force = (1 - (dist / SHOCK_RADIUS)) * SHOCK_FORCE;
            ECS.velocitiesX[i] += (dx / dist) * force;
            ECS.velocitiesY[i] += (dy / dist) * force;
        }
    }
});

// Fixed Timestep Loop (FGD-005)
const FIXED_DT = 1 / 60;
let accumulator = 0;
let lastTime = performance.now();

// FPS tracking
let frames = 0;
let lastFpsTime = performance.now();

function gameLoop(time) {
    const dt = (time - lastTime) / 1000;
    lastTime = time;
    
    // Prevent death spiral if tab is inactive
    if (dt > 0.1) {
        accumulator = 0;
    } else {
        accumulator += dt;
    }

    // Player input
    player.vx = (keys.d - keys.a) * player.speed;
    player.vy = (keys.s - keys.w) * player.speed;

    while (accumulator >= FIXED_DT) {
        // Spawn missing entities
        let activeCount = 0;
        for (let i = 0; i < ECS.MAX_ENTITIES; i++) {
            if (ECS.active[i]) activeCount++;
        }
        
        if (activeCount < ECS.MAX_ENTITIES) {
            // Spawn at random edges
            let ex = Math.random() < 0.5 ? 0 : width;
            let ey = Math.random() * height;
            if (Math.random() < 0.5) {
                ex = Math.random() * width;
                ey = Math.random() < 0.5 ? 0 : height;
            }
            ECS.spawnEntity(ex, ey, 0, 0);
        }

        // Swarm logic (Seek player)
        for (let i = 0; i < ECS.MAX_ENTITIES; i++) {
            if (!ECS.active[i]) continue;
            const dx = player.x - ECS.positionsX[i];
            const dy = player.y - ECS.positionsY[i];
            const distSq = dx*dx + dy*dy;
            
            if (distSq > 0) {
                const dist = Math.sqrt(distSq);
                ECS.velocitiesX[i] += (dx / dist) * 0.1;
                ECS.velocitiesY[i] += (dy / dist) * 0.1;
            }
        }

        player.x += player.vx * FIXED_DT;
        player.y += player.vy * FIXED_DT;
        
        // Bounds
        player.x = Math.max(10, Math.min(width - 10, player.x));
        player.y = Math.max(10, Math.min(height - 10, player.y));

        ECS.updateSpatialGrid();
        ECS.applyPhysics(FIXED_DT);
        accumulator -= FIXED_DT;
    }

    render();
    
    // Telemetry
    frames++;
    if (time - lastFpsTime >= 1000) {
        fpsCounter.innerText = `FPS: ${frames}`;
        let activeCount = 0;
        for (let i = 0; i < ECS.MAX_ENTITIES; i++) activeCount += ECS.active[i];
        entityCounter.innerText = `ENTIDADES: ${activeCount}`;
        frames = 0;
        lastFpsTime = time;
    }

    requestAnimationFrame(gameLoop);
}

function render() {
    // FGD-044 Linear Frame Wipe equivalent
    ctx.fillStyle = '#0A0A0A';
    ctx.fillRect(0, 0, width, height);

    // Render Swarm
    ctx.fillStyle = '#FF3333'; // "Guiris" o Zombies
    ctx.beginPath();
    for (let i = 0; i < ECS.MAX_ENTITIES; i++) {
        if (!ECS.active[i]) continue;
        ctx.moveTo(ECS.positionsX[i] + ECS.ENTITY_RADIUS, ECS.positionsY[i]);
        ctx.arc(ECS.positionsX[i], ECS.positionsY[i], ECS.ENTITY_RADIUS, 0, Math.PI * 2);
    }
    ctx.fill();

    // Render Player
    ctx.fillStyle = '#2B3BE5';
    ctx.beginPath();
    ctx.arc(player.x, player.y, 8, 0, Math.PI * 2);
    ctx.fill();
}

requestAnimationFrame(gameLoop);
