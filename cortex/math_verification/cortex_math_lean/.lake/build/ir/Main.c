// Lean compiler output
// Module: Main
// Imports: public import Init public meta import Init public import CortexMathLean
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
lean_object* lean_string_push(lean_object*, uint32_t);
lean_object* lean_get_stdout();
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_print___at___00IO_println___at___00main_spec__0_spec__0(lean_object*);
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_print___at___00IO_println___at___00main_spec__0_spec__0___boxed(lean_object*, lean_object*);
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_println___at___00main_spec__0(lean_object*);
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_println___at___00main_spec__0___boxed(lean_object*, lean_object*);
static const lean_string_object lp_cortex__math__lean_main___closed__0_value = {.m_header = {.m_rc = 0, .m_cs_sz = 0, .m_other = 0, .m_tag = 249}, .m_size = 54, .m_capacity = 54, .m_length = 53, .m_data = "CortexMathLean - SAT Formal Verification Initialized."};
static const lean_object* lp_cortex__math__lean_main___closed__0 = (const lean_object*)&lp_cortex__math__lean_main___closed__0_value;
LEAN_EXPORT lean_object* _lean_main();
LEAN_EXPORT lean_object* lp_cortex__math__lean_main___boxed(lean_object*);
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_print___at___00IO_println___at___00main_spec__0_spec__0(lean_object* v_s_1_){
_start:
{
lean_object* v___x_3_; lean_object* v_putStr_4_; lean_object* v___x_5_; 
v___x_3_ = lean_get_stdout();
v_putStr_4_ = lean_ctor_get(v___x_3_, 4);
lean_inc_ref(v_putStr_4_);
lean_dec_ref(v___x_3_);
v___x_5_ = lean_apply_2(v_putStr_4_, v_s_1_, lean_box(0));
return v___x_5_;
}
}
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_print___at___00IO_println___at___00main_spec__0_spec__0___boxed(lean_object* v_s_6_, lean_object* v_a_7_){
_start:
{
lean_object* v_res_8_; 
v_res_8_ = lp_cortex__math__lean_IO_print___at___00IO_println___at___00main_spec__0_spec__0(v_s_6_);
return v_res_8_;
}
}
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_println___at___00main_spec__0(lean_object* v_s_9_){
_start:
{
uint32_t v___x_11_; lean_object* v___x_12_; lean_object* v___x_13_; 
v___x_11_ = 10;
v___x_12_ = lean_string_push(v_s_9_, v___x_11_);
v___x_13_ = lp_cortex__math__lean_IO_print___at___00IO_println___at___00main_spec__0_spec__0(v___x_12_);
return v___x_13_;
}
}
LEAN_EXPORT lean_object* lp_cortex__math__lean_IO_println___at___00main_spec__0___boxed(lean_object* v_s_14_, lean_object* v_a_15_){
_start:
{
lean_object* v_res_16_; 
v_res_16_ = lp_cortex__math__lean_IO_println___at___00main_spec__0(v_s_14_);
return v_res_16_;
}
}
LEAN_EXPORT lean_object* _lean_main(){
_start:
{
lean_object* v___x_19_; lean_object* v___x_20_; 
v___x_19_ = ((lean_object*)(lp_cortex__math__lean_main___closed__0));
v___x_20_ = lp_cortex__math__lean_IO_println___at___00main_spec__0(v___x_19_);
return v___x_20_;
}
}
LEAN_EXPORT lean_object* lp_cortex__math__lean_main___boxed(lean_object* v_a_21_){
_start:
{
lean_object* v_res_22_; 
v_res_22_ = _lean_main();
return v_res_22_;
}
}
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_cortex__math__lean_CortexMathLean(uint8_t builtin);
static bool _G_initialized = false;
LEAN_EXPORT lean_object* initialize_cortex__math__lean_Main(uint8_t builtin) {
lean_object * res;
if (_G_initialized) return lean_io_result_mk_ok(lean_box(0));
_G_initialized = true;
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_cortex__math__lean_CortexMathLean(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
return lean_io_result_mk_ok(lean_box(0));
}
char ** lean_setup_args(int argc, char ** argv);
void lean_initialize_runtime_module();
#if defined(WIN32) || defined(_WIN32)
#include <windows.h>
#endif
lean_object* run_main(int argc, char ** argv) {
    return _lean_main();
}
int main(int argc, char ** argv) {
#if defined(WIN32) || defined(_WIN32)
  SetErrorMode(SEM_FAILCRITICALERRORS);
  SetConsoleOutputCP(CP_UTF8);
#endif
  lean_object* res;
  argv = lean_setup_args(argc, argv);
  lean_initialize_runtime_module();
  res = initialize_cortex__math__lean_Main(1 /* builtin */);
  lean_io_mark_end_initialization();
  if (lean_io_result_is_ok(res)) {
    lean_dec_ref(res);
    lean_init_task_manager();
    res = lean_run_main(&run_main, argc, argv);
  }
  lean_finalize_task_manager();
  if (lean_io_result_is_ok(res)) {
    int ret = 0;
    lean_dec_ref(res);
    return ret;
  } else {
    lean_io_result_show_error(res);
    lean_dec_ref(res);
    return 1;
  }
}
#ifdef __cplusplus
}
#endif
