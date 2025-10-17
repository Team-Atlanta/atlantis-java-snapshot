use std::ops::RangeInclusive;

#[cfg(feature = "debug")]
use crate::encoder::debug::llvm::test_consume;

use super::{EncoderError, EncoderResult};

#[derive(Clone, Debug)]
pub enum LlvmFdpCall {
    Byte {
        value: u8,
        range: Option<RangeInclusive<u8>>,
    },
    Char {
        value: i8,
        range: Option<RangeInclusive<i8>>,
    },
    Short {
        value: i16,
        range: Option<RangeInclusive<i16>>,
    },
    UShort {
        value: u16,
        range: Option<RangeInclusive<u16>>,
    },
    Int {
        value: i32,
        range: Option<RangeInclusive<i32>>,
    },
    UInt {
        value: u32,
        range: Option<RangeInclusive<u32>>,
    },
    LongLong {
        value: i64,
        range: Option<RangeInclusive<i64>>,
    },
    ULongLong {
        value: u64,
        range: Option<RangeInclusive<u64>>,
    },
    Bool {
        value: bool,
    },
    Float {
        value: f32,
        range: Option<RangeInclusive<f32>>,
    },
    ProbFloat {
        value: f32,
    },
    Double {
        value: f64,
        range: Option<RangeInclusive<f64>>,
    },
    ProbDouble {
        value: f64,
    },
    Enum {
        value: u32,
        max_k: u32,
    },
    Bytes {
        value: Vec<u8>,
        terminator: Option<u8>,
    },
    RemainingBytes {
        value: Vec<u8>,
    },
    RemainingBytesMark {
        value: usize,
    },
    String {
        value: Vec<u8>,
        requested_length: Option<usize>,
    },
    RandomString {
        value: Vec<u8>,
        max_length: Option<usize>,
    },
    RemainingString {
        value: Vec<u8>,
    },
    ValuePick {
        value_index: usize,
        array_length: usize,
    },
}

#[derive(Default)]
pub struct LlvmFdpEncoder {
    inner: crate::FdpEncoder,
    #[cfg(feature = "debug")]
    call_log: Vec<LlvmFdpCall>,
}

impl LlvmFdpEncoder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn produce_byte_in_range_unchecked(
        &mut self,
        value: u8,
        min: u8,
        max: u8,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Byte {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_char_in_range_unchecked(
        &mut self,
        value: i8,
        min: i8,
        max: i8,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Char {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_short_in_range_unchecked(
        &mut self,
        value: i16,
        min: i16,
        max: i16,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Short {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_unsigned_short_in_range_unchecked(
        &mut self,
        value: u16,
        min: u16,
        max: u16,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::UShort {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_int_in_range_unchecked(
        &mut self,
        value: i32,
        min: i32,
        max: i32,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Int {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_unsigned_int_in_range_unchecked(
        &mut self,
        value: u32,
        min: u32,
        max: u32,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::UInt {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_long_long_in_range_unchecked(
        &mut self,
        value: i64,
        min: i64,
        max: i64,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::LongLong {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_unsigned_long_long_in_range_unchecked(
        &mut self,
        value: u64,
        min: u64,
        max: u64,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ULongLong {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_byte_unchecked(&mut self, value: u8) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Byte { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u8::MIN as i128..=u8::MAX as i128)
    }

    pub fn produce_char_unchecked(&mut self, value: i8) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Char { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, i8::MIN as i128..=i8::MAX as i128)
    }

    pub fn produce_short_unchecked(&mut self, value: i16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::Short { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, i16::MIN as i128..=i16::MAX as i128)
    }

    pub fn produce_unsigned_short_unchecked(&mut self, value: u16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::UShort { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u16::MIN as i128..=u16::MAX as i128)
    }

    pub fn produce_int_unchecked(&mut self, value: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Int { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, i32::MIN as i128..=i32::MAX as i128)
    }

    pub fn produce_unsigned_int_unchecked(&mut self, value: u32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::UInt { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u32::MIN as i128..=u32::MAX as i128)
    }

    pub fn produce_long_long_unchecked(&mut self, value: i64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::LongLong { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, i64::MIN as i128..=i64::MAX as i128)
    }

    pub fn produce_unsigned_long_long_unchecked(&mut self, value: u64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::ULongLong { value, range: None });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u64::MIN as i128..=u64::MAX as i128)
    }

    pub fn produce_bool_unchecked(&mut self, value: bool) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Bool { value });
        self.inner.produce_bool_unchecked(value)
    }

    pub fn produce_float_in_range_unchecked(
        &mut self,
        value: f32,
        min: f32,
        max: f32,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Float {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_float_in_range_unchecked(value, min..=max)
    }

    pub fn produce_double_in_range_unchecked(
        &mut self,
        value: f64,
        min: f64,
        max: f64,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Double {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_double_in_range_unchecked(value, min..=max)
    }

    pub fn produce_float_unchecked(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::Float { value, range: None });
        self.inner
            .produce_float_in_range_unchecked(value, f32::MIN..=f32::MAX)
    }

    pub fn produce_double_unchecked(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::Double { value, range: None });
        self.inner
            .produce_double_in_range_unchecked(value, f64::MIN..=f64::MAX)
    }

    pub fn produce_probability_float_unchecked(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ProbFloat { value });
        self.inner.produce_probability_float_unchecked(value)
    }

    pub fn produce_probability_double_unchecked(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ProbDouble { value });
        self.inner.produce_probability_double_unchecked(value)
    }

    pub fn produce_enum_unchecked(&mut self, value: u32, max_value: u32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Enum {
            value,
            max_k: max_value,
        });
        self.inner.produce_enum_unchecked(value, max_value)
    }

    pub fn produce_bytes_unchecked(&mut self, value: &[u8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Bytes {
            value: value.to_vec(),
            terminator: None,
        });
        self.inner.produce_bytes_unchecked(value);
        Ok(())
    }

    pub fn produce_bytes_with_terminator_unchecked(
        &mut self,
        value: &[u8],
        terminator: u8,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Bytes {
            value: value.to_vec(),
            terminator: Some(terminator),
        });
        self.inner
            .produce_bytes_with_terminator_unchecked(value, terminator)
    }

    pub fn produce_remaining_bytes_unchecked(&mut self, value: &[u8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RemainingBytes {
            value: value.to_vec(),
        });
        self.inner.produce_remaining_bytes_unchecked(value);
        Ok(())
    }

    pub fn produce_remaining_bytes_as_string_unchecked(&mut self, value: &[u8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RemainingString {
            value: value.to_vec(),
        });
        self.inner.produce_remaining_bytes_unchecked(value);
        Ok(())
    }

    pub fn produce_bytes_as_string_unchecked(
        &mut self,
        value: &[u8],
        num_bytes: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::String {
            value: value.to_vec(),
            requested_length: Some(num_bytes),
        });
        self.inner.produce_string_unchecked(value, num_bytes)
    }

    pub fn produce_random_length_string_with_max_length_unchecked(
        &mut self,
        value: &[u8],
        max_length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RandomString {
            value: value.to_vec(),
            max_length: Some(max_length),
        });
        self.inner
            .produce_random_string_unchecked(value, Some(max_length))
    }

    pub fn produce_random_length_string_unchecked(&mut self, value: &[u8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RandomString {
            value: value.to_vec(),
            max_length: None,
        });
        self.inner.produce_random_string_unchecked(value, None)
    }

    pub fn produce_picked_value_index_in_array_unchecked(
        &mut self,
        value: usize,
        length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ValuePick {
            value_index: value,
            array_length: length,
        });
        self.inner
            .produce_array_value_picker_unchecked(value, length)
    }

    pub fn produce_byte_in_range(&mut self, value: u8, min: u8, max: u8) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Byte {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_char_in_range(&mut self, value: i8, min: i8, max: i8) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Char {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_short_in_range(&mut self, value: i16, min: i16, max: i16) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Short {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_unsigned_short_in_range(
        &mut self,
        value: u16,
        min: u16,
        max: u16,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::UShort {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_int_in_range(&mut self, value: i32, min: i32, max: i32) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Int {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_unsigned_int_in_range(
        &mut self,
        value: u32,
        min: u32,
        max: u32,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::UInt {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_long_long_in_range(&mut self, value: i64, min: i64, max: i64) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::LongLong {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_unsigned_long_long_in_range(
        &mut self,
        value: u64,
        min: u64,
        max: u64,
    ) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ULongLong {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_byte(&mut self, value: u8) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Byte { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, u8::MIN as i128..=u8::MAX as i128)
    }

    pub fn produce_char(&mut self, value: i8) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Char { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, i8::MIN as i128..=i8::MAX as i128)
    }

    pub fn produce_short(&mut self, value: i16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::Short { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, i16::MIN as i128..=i16::MAX as i128)
    }

    pub fn produce_unsigned_short(&mut self, value: u16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::UShort { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, u16::MIN as i128..=u16::MAX as i128)
    }

    pub fn produce_int(&mut self, value: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Int { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, i32::MIN as i128..=i32::MAX as i128)
    }

    pub fn produce_unsigned_int(&mut self, value: u32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::UInt { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, u32::MIN as i128..=u32::MAX as i128)
    }

    pub fn produce_long_long(&mut self, value: i64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::LongLong { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, i64::MIN as i128..=i64::MAX as i128)
    }

    pub fn produce_unsigned_long_long(&mut self, value: u64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::ULongLong { value, range: None });
        self.inner
            .produce_integral_in_range(value as i128, u64::MIN as i128..=u64::MAX as i128)
    }

    pub fn produce_bool(&mut self, value: bool) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Bool { value });
        self.inner.produce_bool(value)
    }

    pub fn produce_float_in_range(&mut self, value: f32, min: f32, max: f32) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Float {
            value,
            range: Some(min..=max),
        });
        self.inner.produce_float_in_range(value, min..=max)
    }

    pub fn produce_double_in_range(&mut self, value: f64, min: f64, max: f64) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Double {
            value,
            range: Some(min..=max),
        });
        self.inner.produce_double_in_range(value, min..=max)
    }

    pub fn produce_float(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::Float { value, range: None });
        self.inner
            .produce_float_in_range(value, f32::MIN..=f32::MAX)
    }

    pub fn produce_double(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::Double { value, range: None });
        self.inner
            .produce_double_in_range(value, f64::MIN..=f64::MAX)
    }

    pub fn produce_probability_float(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ProbFloat { value });
        self.inner.produce_probability_float(value)
    }

    pub fn produce_probability_double(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ProbDouble { value });
        self.inner.produce_probability_double(value)
    }

    pub fn produce_enum(&mut self, value: u32, max_value: u32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Enum {
            value,
            max_k: max_value,
        });
        self.inner.produce_enum(value, max_value)
    }

    pub fn produce_bytes(&mut self, value: &[u8], num_bytes: usize) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Bytes {
            value: value.to_vec(),
            terminator: None,
        });
        self.inner.produce_bytes(value, num_bytes)
    }

    pub fn produce_bytes_with_terminator(
        &mut self,
        value: &[u8],
        num_bytes: usize,
        terminator: u8,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::Bytes {
            value: value.to_vec(),
            terminator: Some(terminator),
        });
        self.inner
            .produce_bytes_with_terminator(value, num_bytes, terminator)
    }

    pub fn produce_remaining_bytes(&mut self, value: &[u8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RemainingBytes {
            value: value.to_vec(),
        });
        self.inner.produce_remaining_bytes(value)
    }

    pub fn produce_remaining_bytes_as_string(&mut self, value: &[u8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RemainingString {
            value: value.to_vec(),
        });
        self.inner.produce_remaining_bytes(value)
    }

    pub fn produce_bytes_as_string(&mut self, value: &[u8], num_bytes: usize) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::String {
            value: value.to_vec(),
            requested_length: Some(num_bytes),
        });
        self.inner.produce_string(value, num_bytes)
    }

    pub fn produce_random_length_string_with_max_length(
        &mut self,
        value: &[u8],
        max_length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RandomString {
            value: value.to_vec(),
            max_length: Some(max_length),
        });
        self.inner.produce_random_string(value, Some(max_length))
    }

    pub fn produce_random_length_string(&mut self, value: &[u8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::RandomString {
            value: value.to_vec(),
            max_length: None,
        });
        self.inner.produce_random_string(value, None)
    }

    pub fn produce_picked_value_index_in_array(
        &mut self,
        value: usize,
        length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(LlvmFdpCall::ValuePick {
            value_index: value,
            array_length: length,
        });
        self.inner.produce_array_value_picker(value, length)
    }

    pub fn mark_remaining_bytes(&mut self, value: usize) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(LlvmFdpCall::RemainingBytesMark { value });
        self.inner.mark_remaining_bytes(value)
    }

    pub fn finalize(self) -> Result<Vec<u8>, EncoderError> {
        let result = self.inner.finalize()?;
        #[cfg(feature = "debug")]
        {
            test_consume(&result, &self.call_log)?;
        }
        Ok(result)
    }
}
