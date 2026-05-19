/**
 * CORTEX-Persist Intake Pipeline (C5-REAL)
 * 
 * Determinist injection of prospects/leads into the CORTEX Backend.
 * Replaces legacy static strings with a resilient, async data bridge.
 */

export const SUPPORT_EMAIL = 'borja@cortexpersist.com';
export const CORTEX_API_URL = import.meta.env.PUBLIC_CORTEX_API_URL || 'http://localhost:8000';

export interface IntakePayload {
  name: string;
  email: string;
  source_type: string;
  confidence?: 'C5-REAL' | 'C4' | 'C3' | 'C2' | 'C1';
}

/**
 * Injects a lead/prospect into the CORTEX Memory ledger.
 * Triggered by UI interactions (The Map) to persist in the DB (The Territory).
 */
export async function injectLead(payload: IntakePayload): Promise<boolean> {
  try {
    const response = await fetch(`${CORTEX_API_URL}/api/v1/influencers/intake`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Cortex-Taint': `taint:ui-intake:${Date.now()}:lead`,
      },
      body: JSON.stringify({
        ...payload,
        confidence: payload.confidence || 'C4', // Default to C4 (Simulation) until verified by backend
      }),
    });

    if (!response.ok) {
      console.error(`[CORTEX-INTAKE] Validation failed: ${response.status}`);
      return false;
    }

    console.info(`[CORTEX-INTAKE] Lead injected successfully. Horizon secured.`);
    return true;
  } catch (error) {
    console.error(`[CORTEX-INTAKE] Connection to Oracle collapsed.`, error);
    return false;
  }
}
