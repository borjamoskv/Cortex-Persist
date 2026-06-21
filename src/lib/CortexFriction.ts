// @C5-REAL
import * as fs from 'fs';
import * as path from 'path';

// CORTEX-Persist: Telemetry Ledger
// Purpose: Record C5-REAL friction to prevent the Ouroboros Daemon from purging stable components.

const LEDGER_PATH = path.join(process.cwd(), '.cortex_ledger.json');

interface FrictionEvent {
    componentId: string;
    timestamp: number;
    type: 'RENDER' | 'API_HIT' | 'INTERACTION';
}

export class CortexFriction {
    /**
     * Records a friction event for a component.
     * @param componentId Unique component identifier (e.g. "Layout.astro", "Engine.ts").
     * @param type Friction type (default: RENDER).
     */
    static ping(componentId: string, type: FrictionEvent['type'] = 'RENDER'): void {
        try {
            let ledger: Record<string, FrictionEvent> = {};
            
            if (fs.existsSync(LEDGER_PATH)) {
                const data = fs.readFileSync(LEDGER_PATH, 'utf-8');
                ledger = JSON.parse(data);
            }

            ledger[componentId] = {
                componentId,
                timestamp: Date.now(),
                type
            };

            fs.writeFileSync(LEDGER_PATH, JSON.stringify(ledger, null, 2), 'utf-8');
        } catch (error) {
            // Fails silently to avoid interrupting the runtime in case of I/O errors.
            // In a strict C5-REAL environment, this should trigger a telemetry loss alert.
            console.error(`[CORTEX-TELEMETRY-ERROR] Could not register friction for ${componentId}.`, error);
        }
    }
    
    /**
     * Returns the complete ledger for the Ouroboros Daemon to read.
     */
    static getLedger(): Record<string, FrictionEvent> {
        if (!fs.existsSync(LEDGER_PATH)) return {};
        try {
            return JSON.parse(fs.readFileSync(LEDGER_PATH, 'utf-8'));
        } catch {
            return {};
        }
    }
}
