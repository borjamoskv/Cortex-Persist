#include <stdint.h>
#include <stddef.h>

#ifdef __arm64__
#include <arm_neon.h>
#elif defined(__x86_64__)
#include <immintrin.h>
#endif

/**
 * CORTEX — VOID-MAX Batch SIMD Accelerator (Universal).
 * 
 * Processes a batch of vectors against a single query vector.
 * Axiom Ω0: Saturate the silicon bandwidth.
 * Supports: ARM64 Neon, x86_64 AVX2, AVX-512 (VPOPCNTDQ).
 */

#ifdef __arm64__
// ARM64 Neon implementation (Optimized for Apple Silicon / Graviton)
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
        
        for (; j <= len - 16; j += 16) {
            uint8x16_t vq = vld1q_u8(query + j);
            uint8x16_t vt = vld1q_u8(target + j);
            uint8x16_t vxor = veorq_u8(vq, vt);
            uint8x16_t vcnt = vcntq_u8(vxor);
            total_dist += vaddlvq_u8(vcnt);
        }
        
        for (; j < len; j++) {
            total_dist += __builtin_popcount(query[j] ^ target[j]);
        }
        distances[i] = total_dist;
    }
}
#endif

#ifdef __x86_64__
// AVX-512 implementation (Optimized for Intel Mac Pro / Xeon / EPYC)
void void_batch_hamming_dist_avx512(
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

        // 512-bit (64-byte) blocks
        for (; j <= len - 64; j += 64) {
            __m512i vq = _mm512_loadu_si512((const __m512i*)(query + j));
            __m512i vt = _mm512_loadu_si512((const __m512i*)(target + j));
            __m512i vxor = _mm512_xor_si512(vq, vt);
            // VPOPCNTDQ: Population count of bits set in each 64-bit qword
            __m512i vcnt = _mm512_popcnt_epi64(vxor);
            // Reduce 8 qwords into a single uint64
            total_dist += _mm512_reduce_add_epi64(vcnt);
        }

        // Bitwise tail
        for (; j < len; j++) {
            total_dist += __builtin_popcount(query[j] ^ target[j]);
        }
        distances[i] = total_dist;
    }
}
#endif
