// Lean compiler output
// Module: CortexMathLean
// Imports: public import Init public meta import Init public import CortexMathLean.GraphTheory public import CortexMathLean.HardGraphChecker
#include <lean/lean.h>
#if defined(__clang__)
#pragma clang diagnostic ignored "-Wunused-parameter"
#pragma clang diagnostic ignored "-Wunused-label"
#elif defined(__GNUC__) && !defined(__CLANG__)
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wunused-label"
#pragma GCC diagnostic ignored "-Wunused-but-set-variable"
#endif
#ifdef __cplusplus
extern "C" {
#endif
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_cortex__math__lean_CortexMathLean_GraphTheory(uint8_t builtin);
lean_object* initialize_cortex__math__lean_CortexMathLean_HardGraphChecker(uint8_t builtin);
static bool _G_initialized = false;
LEAN_EXPORT lean_object* initialize_cortex__math__lean_CortexMathLean(uint8_t builtin) {
lean_object * res;
if (_G_initialized) return lean_io_result_mk_ok(lean_box(0));
_G_initialized = true;
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_cortex__math__lean_CortexMathLean_GraphTheory(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_cortex__math__lean_CortexMathLean_HardGraphChecker(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
return lean_io_result_mk_ok(lean_box(0));
}
#ifdef __cplusplus
}
#endif
