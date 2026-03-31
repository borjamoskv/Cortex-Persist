#include <arm_neon.h>
#include <stdint.h>
#include <stddef.h>

/**
 * CORTEX — VOID-MAX Batch SIMD Accelerator (ARM64 Neon).
 * 
 * Processes a batch of vectors against a single query vector.
 * Axiom Ω0: Saturate the silicon bandwidth.
 */

// Calculates Hamming Distance between a query and a batch of vectors.
// 'query': pointer to query vector (len bytes)
// 'batch': pointer to flat array of vectors (count * len bytes)
// 'distances': pointer to output array (count * uint64_t)
void void_batch_hamming_dist_neon(
    const uint8_t* query, 
    const uint8_t* batch, 
    uint64_t* distances, 
    size_t count, 
    size_t len
) {
    for (size_t i = 0; i < count; i++) {
        const uint8_t* target = batch + (i * len);
        uint64_t total_dist = 0;
        size_t j = 0;
        
        // SIMD loop (128-bit blocks)
        for (; j <= len - 16; j += 16) {
            uint8x16_t vq = vld1q_u8(query + j);
            uint8x16_t vt = vld1q_u8(target + j);
            uint8x16_t vxor = veorq_u8(vq, vt);
            uint8x16_t vcnt = vcntq_u8(vxor);
            total_dist += vaddlvq_u8(vcnt);
        }
        
        // Tail
        for (; j < len; j++) {
            total_dist += __builtin_popcount(query[j] ^ target[j]);
        }
        
        distances[i] = total_dist;
    }
}
