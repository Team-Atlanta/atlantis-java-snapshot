//! Sanitizer Coverage comparison functions

use core::{
    cmp,
    ffi::{c_char, c_int, c_void},
    ptr,
};

use crate::CMPLOG_MAP_W;

unsafe extern "C" {

    /// Trace an 8 bit `cmp`
    pub fn __sanitizer_cov_trace_cmp1(v0: u8, v1: u8);
    /// Trace a 16 bit `cmp`
    pub fn __sanitizer_cov_trace_cmp2(v0: u16, v1: u16);
    /// Trace a 32 bit `cmp`
    pub fn __sanitizer_cov_trace_cmp4(v0: u32, v1: u32);
    /// Trace a 64 bit `cmp`
    pub fn __sanitizer_cov_trace_cmp8(v0: u64, v1: u64);

    /// Trace an 8 bit constant `cmp`
    pub fn __sanitizer_cov_trace_const_cmp1(v0: u8, v1: u8);
    /// Trace a 16 bit constant `cmp`
    pub fn __sanitizer_cov_trace_const_cmp2(v0: u16, v1: u16);
    /// Trace a 32 bit constant `cmp`
    pub fn __sanitizer_cov_trace_const_cmp4(v0: u32, v1: u32);
    /// Trace a 64 bit constant `cmp`
    pub fn __sanitizer_cov_trace_const_cmp8(v0: u64, v1: u64);

    /// Trace a switch statement
    pub fn __sanitizer_cov_trace_switch(val: u64, cases: *const u64);

    /// trace byte comparison internal api
    pub fn __libafl_targets_trace_memcmp_style_functions(
        called_pc: usize,
        s1: *const u8, s2: *const u8,
        len: usize,
        stop_at_zero: u8);
    /// cmplog internal api
    pub fn __libafl_targets_cmplog_routines_len(called_pc: usize, s1: *const u8, s2: *const u8, len: usize);
    /// cmplog internal api
    pub fn __libafl_targets_cmplog_routines_len1_len2(called_pc: usize, s1: *const u8, s2: *const u8, len1: usize, len2: usize);
}

/// overriding `__sanitizer_weak_hook_memcmp`
/// # Safety
/// this function has raw pointer access
#[unsafe(no_mangle)]
pub unsafe extern "C" fn __sanitizer_weak_hook_memcmp(
    called_pc: *const c_void,
    s1: *const c_void,
    s2: *const c_void,
    n: usize,
    result: c_int,
) {
    unsafe {
        if result != 0 {
            let k: usize = called_pc as usize;
            let k = (k >> 4) ^ (k << 8);
            let k = k & (CMPLOG_MAP_W - 1);
            __libafl_targets_cmplog_routines_len(
                k,
                s1 as *const u8,
                s2 as *const u8,
                cmp::min(n, 32),
            );

            #[cfg(feature = "sancov_value_profile")]
            __libafl_targets_trace_memcmp_style_functions(
                called_pc as usize,
                s1 as *const u8, s2 as *const u8,
                n,
                false as u8);
        }
    }
}

#[unsafe(no_mangle)]
/// overriding `__sanitizer_weak_hook_strncmp`
///
/// # Safety
/// this function has raw pointer access
pub unsafe extern "C" fn __sanitizer_weak_hook_strncmp(
    called_pc: *const c_void,
    s1: *const c_char,
    s2: *const c_char,
    n: usize,
    result: c_int,
) {
    unsafe {
        if result != 0 {
            let n = cmp::min(n, 32);
            let k: usize = called_pc as usize;
            let k = (k >> 4) ^ (k << 8);
            let k = k & (CMPLOG_MAP_W - 1);
            let mut actual_len = 0;
            while actual_len < n {
                let c1 = ptr::read(s1.add(actual_len));
                let c2 = ptr::read(s2.add(actual_len));

                if c1 == 0 || c2 == 0 {
                    break;
                }
                actual_len += 1;
            }
            __libafl_targets_cmplog_routines_len(k, s1 as *const u8, s2 as *const u8, actual_len);

            #[cfg(feature = "sancov_value_profile")]
            __libafl_targets_trace_memcmp_style_functions(
                called_pc as usize,
                s1 as *const u8, s2 as *const u8,
                actual_len,
                true as u8);
        }
    }
}

#[unsafe(no_mangle)]
/// overriding `__sanitizer_weak_hook_strncasecmps`
/// # Safety
/// this function has raw pointer access
pub unsafe extern "C" fn __sanitizer_weak_hook_strncasecmp(
    called_pc: *const c_void,
    s1: *const c_char,
    s2: *const c_char,
    n: usize,
    result: c_int,
) {
    unsafe {
        __sanitizer_weak_hook_strncmp(called_pc, s1, s2, n, result);
    }
}

#[unsafe(no_mangle)]
/// overriding `__sanitizer_weak_hook_strcmp`
/// # Safety
/// this function has raw pointer access
pub unsafe extern "C" fn __sanitizer_weak_hook_strcmp(
    called_pc: *const c_void,
    s1: *const c_char,
    s2: *const c_char,
    result: c_int,
) {
    unsafe {
        if result != 0 {
            let k: usize = called_pc as usize;
            let k = (k >> 4) ^ (k << 8);
            let k = k & (CMPLOG_MAP_W - 1);
            let mut actual_len = 0;
            while actual_len < 32 {
                let c1 = ptr::read(s1.add(actual_len));
                let c2 = ptr::read(s2.add(actual_len));

                if c1 == 0 || c2 == 0 {
                    break;
                }
                actual_len += 1;
            }
            __libafl_targets_cmplog_routines_len(k, s1 as *const u8, s2 as *const u8, actual_len);

            #[cfg(feature = "sancov_value_profile")]
            __libafl_targets_trace_memcmp_style_functions(
                called_pc as usize,
                s1 as *const u8, s2 as *const u8,
                actual_len,
                true as u8);
        }
    }
}

#[unsafe(no_mangle)]
/// overriding `__sanitizer_weak_hook_strcmp`
/// # Safety
/// this function has raw pointer access
pub unsafe extern "C" fn __sanitizer_weak_hook_strcasecmp(
    called_pc: *const c_void,
    s1: *const c_char,
    s2: *const c_char,
    result: c_int,
) {
    unsafe {
        __sanitizer_weak_hook_strcmp(called_pc, s1, s2, result);
    }
}

#[unsafe(no_mangle)]
/// overriding `__sanitizer_weak_hook_strstr`
/// # Safety
/// this function has raw pointer access
pub unsafe extern "C" fn __sanitizer_weak_hook_strstr(
    called_pc: *const c_void,
    s1: *const c_char,
    s2: *const c_char,
    result: c_int,
) {
    let result_inverse =  if result == 0 {
        1
    } else {
        0
    };
    unsafe {
        __sanitizer_weak_hook_strcmp(called_pc, s1, s2, result_inverse);
    }
}

/// overriding `__sanitizer_weak_hook_strcasestr`
#[unsafe(no_mangle)]
pub unsafe extern "C" fn __sanitizer_weak_hook_strcasestr(
    _called_pc: *const c_void,
    _s1: *const c_char,
    _s2: *const c_char,
    _result: c_int,
) {
    // TODO
}

#[unsafe(no_mangle)]
/// overriding `__sanitizer_weak_hook_memmem`
/// # Safety
/// this function has raw pointer access
pub unsafe extern "C" fn __sanitizer_weak_hook_memmem(
    called_pc: *const c_void,
    s1: *const c_void,
    s1_len: usize,
    s2: *const c_void,
    s2_len: usize,
    result: c_int,
) {
    if result == 0 {
        let k: usize = called_pc as usize;
        let k = (k >> 4) ^ (k << 8);
        let k = k & (CMPLOG_MAP_W - 1);
        let len = cmp::min(cmp::min(s1_len, s2_len), 32);
        unsafe {
            __libafl_targets_cmplog_routines_len(k, s1 as *const u8, s2 as *const u8, len);
        }
    }
}

// ------- Jazzer Variants --------

#[unsafe(no_mangle)]
/// overriding `__sanitizer_weak_hook_compare_bytes`, a jazzer custom method
/// # Safety
/// this function has raw pointer access
pub unsafe extern "C" fn __sanitizer_weak_hook_compare_bytes(
    called_pc: *const c_void,
    s1: *const c_void,
    s2: *const c_void,
    n1: usize,
    n2: usize,
    result: c_int,
) {
    if result != 0 && n1 > 1 && n2 > 1 {
        let k: usize = called_pc as usize;
        let k = (k >> 4) ^ (k << 8);
        let k = k & (CMPLOG_MAP_W - 1);
        unsafe {
            __libafl_targets_cmplog_routines_len1_len2(
                k,
                s1 as *const u8, s2 as *const u8, 
                cmp::min(n1, 32), cmp::min(n2, 32));

            #[cfg(feature = "sancov_value_profile")]
            __libafl_targets_trace_memcmp_style_functions(
                called_pc as usize,
                s1 as *const u8, s2 as *const u8,
                cmp::min(n1, n2),
                false as u8);
        }
    }
}
