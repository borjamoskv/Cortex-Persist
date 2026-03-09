import { useState, useCallback } from 'react';

/**
 * Hook O(1) para validación criptográfica en local.
 * Axioma Ω₃: I verify, then trust.
 */
export function useSovereignVerifier() {
  const [verificationState, setVerificationState] = useState({
    status: 'IDLE', // IDLE | VERIFYING | CONFIRMED | CORRUPTED
    lastVerifiedHash: null,
    latencyMs: 0
  });

  const verifyPayload = useCallback(async (payload, signature, pubKeyBase64) => {
    const t0 = performance.now();
    setVerificationState(s => ({ ...s, status: 'VERIFYING' }));

    try {
      // 1. Decodificar llave pública
      const binaryDerString = window.atob(pubKeyBase64);
      const binaryDer = new Uint8Array(binaryDerString.length);
      for (let i = 0; i < binaryDerString.length; i++) {
        binaryDer[i] = binaryDerString.charCodeAt(i);
      }

      // 2. Importar llave al WebCrypto Subsystem
      const key = await window.crypto.subtle.importKey(
        'spki',
        binaryDer,
        { name: 'ECDSA', namedCurve: 'P-256' },
        true,
        ['verify']
      );

      // 3. Preparar firma y datos
      const signatureBuffer = Uint8Array.from(atob(signature), c => c.charCodeAt(0));
      const dataBuffer = new TextEncoder().encode(JSON.stringify(payload));

      // 4. Verificación Criptográfica Nativa
      const isValid = await window.crypto.subtle.verify(
        { name: 'ECDSA', hash: { name: 'SHA-256' } },
        key,
        signatureBuffer,
        dataBuffer
      );

      const t1 = performance.now();
      
      if (!isValid) throw new Error("CORTEX_MEMBRANE_BREACH: Signature mismatch.");

      setVerificationState({
        status: 'CONFIRMED',
        lastVerifiedHash: signature.substring(0, 8),
        latencyMs: Math.round(t1 - t0)
      });

      return true;
    } catch (error) {
      console.error("[Ω₃-ALERT]", error);
      setVerificationState({
        status: 'CORRUPTED',
        lastVerifiedHash: null,
        latencyMs: Math.round(performance.now() - t0)
      });
      return false;
    }
  }, []);

  return { ...verificationState, verifyPayload };
}
