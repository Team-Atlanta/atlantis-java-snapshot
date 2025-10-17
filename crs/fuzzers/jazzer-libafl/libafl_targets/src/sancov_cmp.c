#include "common.h"
#include <stddef.h>

#ifdef SANCOV_VALUE_PROFILE
  #include "value_profile.h"
#endif

#ifdef SANCOV_CMPLOG
  #include "cmplog.h"
#endif

// Note: for RETADDR to give us the fuzz target caller address we need 
//       to guarantee that this code is inlined. `inline` keyword provides
//       no such guarantees, but a macro does.
#ifdef SANCOV_VALUE_PROFILE
  #define SANCOV_VALUE_PROFILE_CALL(k, arg_size, arg1, arg2, arg1_is_const) \
    uintptr_t k2 = k & (CMP_MAP_SIZE - 1); \
    __libafl_targets_value_profile##arg_size(k2, arg1, arg2);
#else
  #define SANCOV_VALUE_PROFILE_CALL(k, arg_size, arg1, arg2, arg1_is_const)
#endif

#ifdef SANCOV_CMPLOG
  #define SANCOV_CMPLOG_CALL(k, arg_size, arg1, arg2, arg1_is_const) \
    k &= CMPLOG_MAP_W - 1; \
    cmplog_instructions_checked(k, arg_size, (uint64_t)arg1, (uint64_t)arg2, arg1_is_const);
#else
  #define SANCOV_CMPLOG_CALL(k, arg_size, arg1, arg2, arg1_is_const)
#endif

#define HANDLE_SANCOV_TRACE_CMP(arg_size, arg1, arg2, arg1_is_const) { \
  uintptr_t k = RETADDR; \
  k = (k >> 4) ^ (k << 8); \
  SANCOV_VALUE_PROFILE_CALL(k, arg_size, arg1, arg2, arg1_is_const) \
  SANCOV_CMPLOG_CALL(k, arg_size, arg1, arg2, arg1_is_const) \
}

#define HANDLE_SANCOV_TRACE_CMP_WITH_PC(arg_size, arg1, arg2, arg1_is_const) { \
  uintptr_t k = (uintptr_t) caller_pc; \
  k = (k >> 4) ^ (k << 8); \
  SANCOV_VALUE_PROFILE_CALL(k, arg_size, arg1, arg2, arg1_is_const) \
  SANCOV_CMPLOG_CALL(k, arg_size, arg1, arg2, arg1_is_const) \
}

void __sanitizer_cov_trace_cmp1(uint8_t arg1, uint8_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(1, arg1, arg2, 0);
}

void __sanitizer_cov_trace_cmp2(uint16_t arg1, uint16_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(2, arg1, arg2, 0);
}

void __sanitizer_cov_trace_cmp4(uint32_t arg1, uint32_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(4, arg1, arg2, 0);
}

void __sanitizer_cov_trace_cmp8(uint64_t arg1, uint64_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(8, arg1, arg2, 0);
}

void __sanitizer_cov_trace_switch(uint64_t val, uint64_t *cases) {
  uintptr_t rt = RETADDR;

  // if (!cases[1]) {return;}

  for (uint64_t i = 0; i < cases[0]; i++) {
    uintptr_t k = rt + i;
    k = (k >> 4) ^ (k << 8);
    // val , cases[i + 2]
#ifdef SANCOV_VALUE_PROFILE
    k &= CMP_MAP_SIZE - 1;
    switch (cases[1]) {
      case 8:
        __libafl_targets_value_profile1(k, (uint8_t)val, (uint8_t)cases[i + 2]);
        break;
      case 16:
        __libafl_targets_value_profile2(k, (uint16_t)val,
                                        (uint16_t)cases[i + 2]);
        break;
      case 32:
        __libafl_targets_value_profile4(k, (uint32_t)val,
                                        (uint32_t)cases[i + 2]);
        break;
      default:
        __libafl_targets_value_profile8(k, val, cases[i + 2]);
        break;
    }
#endif
#ifdef SANCOV_CMPLOG
    k &= CMPLOG_MAP_W - 1;
    // Note: cases[i + 2] are the constant values, so keep them in arg1 and indicate that it's const
    cmplog_instructions_checked(k, cases[1] / 8, cases[i + 2], val, 1);
#endif
  }
}

// Ammar: For jazzer, copies of above functions with PC passed in.
void __sanitizer_cov_trace_cmp4_with_pc(void *caller_pc, uint32_t arg1, uint32_t arg2) {
  HANDLE_SANCOV_TRACE_CMP_WITH_PC(4, arg1, arg2, 0);
}

void __sanitizer_cov_trace_cmp8_with_pc(void *caller_pc, uint64_t arg1, uint64_t arg2) {
  HANDLE_SANCOV_TRACE_CMP_WITH_PC(8, arg1, arg2, 0);
}

void __sanitizer_cov_trace_switch_with_pc(void *caller_pc, uint64_t val, uint64_t *cases) {
  uintptr_t rt = (uintptr_t) caller_pc;

  // if (!cases[1]) {return;}

  for (uint64_t i = 0; i < cases[0]; i++) {
    uintptr_t k = rt + i;
    k = (k >> 4) ^ (k << 8);
    // val , cases[i + 2]
#ifdef SANCOV_VALUE_PROFILE
    k &= CMP_MAP_SIZE - 1;
    switch (cases[1]) {
      case 8:
        __libafl_targets_value_profile1(k, (uint8_t)val, (uint8_t)cases[i + 2]);
        break;
      case 16:
        __libafl_targets_value_profile2(k, (uint16_t)val,
                                        (uint16_t)cases[i + 2]);
        break;
      case 32:
        __libafl_targets_value_profile4(k, (uint32_t)val,
                                        (uint32_t)cases[i + 2]);
        break;
      default:
        __libafl_targets_value_profile8(k, val, cases[i + 2]);
        break;
    }
#endif
#ifdef SANCOV_CMPLOG
    k &= CMPLOG_MAP_W - 1;
    // Note: cases[i + 2] are the constant values, so keep them in arg1 and indicate that it's const
    cmplog_instructions_checked(k, cases[1] / 8, cases[i + 2], val, 1);
#endif
  }
}

void __sanitizer_cov_trace_gep_with_pc(void *caller_pc, uintptr_t idx) {
  // From https://github.com/AFLplusplus/AFLplusplus/blob/66c2bb39946679ef0c87042b5eb29ddfa3dbb2cc/custom_mutators/libfuzzer/FuzzerTracePC.cpp#L731
  HANDLE_SANCOV_TRACE_CMP_WITH_PC(4, idx, 0, 1);
}

void __sanitizer_cov_trace_div4_with_pc(void *caller_pc, uint32_t val) {
  HANDLE_SANCOV_TRACE_CMP_WITH_PC(4, val, 0, 1);
}

void __sanitizer_cov_trace_div8_with_pc(void *caller_pc, uint64_t val) {
  HANDLE_SANCOV_TRACE_CMP_WITH_PC(8, val, 0, 1);
}
//

void __sanitizer_cov_trace_const_cmp1(uint8_t arg1, uint8_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(1, arg1, arg2, 1);
}

void __sanitizer_cov_trace_const_cmp2(uint16_t arg1, uint16_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(2, arg1, arg2, 1);
}

void __sanitizer_cov_trace_const_cmp4(uint32_t arg1, uint32_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(4, arg1, arg2, 1);
}

void __sanitizer_cov_trace_const_cmp8(uint64_t arg1, uint64_t arg2) {
  HANDLE_SANCOV_TRACE_CMP(8, arg1, arg2, 1);
}

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"

void __sanitizer_cov_trace_pc_indir(uintptr_t Callee) {
  const uintptr_t kBits = 12;
  const uintptr_t kMask = (1 << kBits) - 1;

  uintptr_t caller_pc = RETADDR;
  caller_pc = (caller_pc & kMask) | ((Callee & kMask) << kBits);

  __libafl_targets_value_profile_set_bit(caller_pc);
}

// For jazzer.
void __sanitizer_cov_trace_pc_indir_with_pc(void* caller_pc_void, uintptr_t Callee) {
  const uintptr_t kBits = 12;
  const uintptr_t kMask = (1 << kBits) - 1;

  uintptr_t caller_pc = (uintptr_t) caller_pc_void;
  caller_pc = (caller_pc & kMask) | ((Callee & kMask) << kBits);

  __libafl_targets_value_profile_set_bit(caller_pc);
}


void __libafl_targets_trace_memcmp_style_functions(uintptr_t caller_pc, const uint8_t *ptr1, const uint8_t *ptr2, size_t len, uint8_t stop_at_zero) {
#ifdef SANCOV_VALUE_PROFILE
  if (len <= 1) {
    return;
  }
  uintptr_t k = (uintptr_t) caller_pc;
  k = (k >> 4) ^ (k << 8);

  size_t i = 0;
  for (; i < len; i++) {
    if (ptr1[i] != ptr2[i] || (stop_at_zero && ptr2[i] == 0)) {
      break;
    }
  }

  k += i;
  k &= CMP_MAP_SIZE - 1;

  __libafl_targets_value_profile1(k, ptr1[i], ptr2[i]);
#endif
}
//

#pragma GCC diagnostic pop
