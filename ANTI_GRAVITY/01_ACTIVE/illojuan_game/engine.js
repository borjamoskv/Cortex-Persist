/**
 * C5-REAL ENGINE
 * Primitive FGD-076: ARCHETYPE_CHUNK_MEMORY_BLOCK (ECS via TypedArrays)
 * Primitive FGD-005: FIXED_TIMESTEP_INTEGRATOR
 * Primitive FGD-009: MORTON_CODE_HASHING (Spatial Grid)
 */

const MAX_ENTITIES = 5000;
const ENTITY_RADIUS = 3;

// ECS: SOA (Structure of Arrays) Topology
const positionsX = new Float32Array(MAX_ENTITIES);
const positionsY = new Float32Array(MAX_ENTITIES);
const velocitiesX = new Float32Array(MAX_ENTITIES);
const velocitiesY = new Float32Array(MAX_ENTITIES);
const active = new Uint8Array(MAX_ENTITIES);

// --- Spatial Hash Grid ---
const CELL_SIZE = 50;
let grid = new Map();

function getCellKey(x, y) {
    const cx = Math.floor(x / CELL_SIZE);
    const cy = Math.floor(y / CELL_SIZE);
    // Base-60 inspired spatial hash using bitshifts
    return (cx << 16) | (cy & 0xFFFF);
}

function updateSpatialGrid() {
    grid.clear();
    for (let i = 0; i < MAX_ENTITIES; i++) {
        if (!active[i]) continue;
        const key = getCellKey(positionsX[i], positionsY[i]);
        if (!grid.has(key)) {
            grid.set(key, []);
        }
        grid.get(key).push(i);
    }
}

// --- Systems ---
function spawnEntity(x, y, vx, vy) {
    for (let i = 0; i < MAX_ENTITIES; i++) {
        if (!active[i]) {
            positionsX[i] = x;
            positionsY[i] = y;
            velocitiesX[i] = vx;
            velocitiesY[i] = vy;
            active[i] = 1;
            return i;
        }
    }
    return -1;
}

function applyPhysics(dt) {
    // Avoidance (FGD-037 RVO Approximation)
    for (let i = 0; i < MAX_ENTITIES; i++) {
        if (!active[i]) continue;
        
        let px = positionsX[i];
        let py = positionsY[i];
        let vx = velocitiesX[i];
        let vy = velocitiesY[i];
        
        const key = getCellKey(px, py);
        const neighbors = grid.get(key) || [];
        
        let sepX = 0;
        let sepY = 0;
        let count = 0;
        
        for (let j = 0; j < neighbors.length; j++) {
            const nId = neighbors[j];
            if (nId === i) continue;
            
            const dx = px - positionsX[nId];
            const dy = py - positionsY[nId];
            const distSq = dx*dx + dy*dy;
            
            if (distSq < (ENTITY_RADIUS * 2.5) ** 2 && distSq > 0) {
                const dist = Math.sqrt(distSq);
                sepX += (dx / dist) * 0.5;
                sepY += (dy / dist) * 0.5;
                count++;
            }
        }
        
        if (count > 0) {
            vx += sepX;
            vy += sepY;
        }
        
        // Basic drag
        vx *= 0.98;
        vy *= 0.98;

        positionsX[i] += vx * dt * 60;
        positionsY[i] += vy * dt * 60;
        velocitiesX[i] = vx;
        velocitiesY[i] = vy;
    }
}

window.ECS = {
    MAX_ENTITIES,
    ENTITY_RADIUS,
    positionsX,
    positionsY,
    velocitiesX,
    velocitiesY,
    active,
    spawnEntity,
    updateSpatialGrid,
    applyPhysics
};
