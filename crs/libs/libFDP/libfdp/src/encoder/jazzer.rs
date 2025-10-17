use std::{cmp::Ordering, ops::RangeInclusive};

use bytes::{Buf, BufMut, Bytes, BytesMut};
use memchr::memmem::find_iter;
use simd_cesu8::mutf8;

#[cfg(feature = "debug")]
use crate::encoder::debug::jazzer::test_consume;

use super::{adjust_with_zero, EncoderError, EncoderResult, FdpStagedCall, LengthVariance};

#[derive(Clone, Debug)]
pub enum JazzerFdpCall {
    JByte {
        value: i8,
        range: Option<RangeInclusive<i8>>,
    },
    JChar {
        value: u16,
        range: Option<RangeInclusive<u16>>,
        no_surrogates: bool,
    },
    JShort {
        value: i16,
        range: Option<RangeInclusive<i16>>,
    },
    JInt {
        value: i32,
        range: Option<RangeInclusive<i32>>,
    },
    JLong {
        value: i64,
        range: Option<RangeInclusive<i64>>,
    },
    JBool {
        value: bool,
    },
    JFloat {
        value: f32,
        range: Option<RangeInclusive<f32>>,
    },
    ProbJFloat {
        value: f32,
    },
    JDouble {
        value: f64,
        range: Option<RangeInclusive<f64>>,
    },
    ProbJDouble {
        value: f64,
    },
    JBytes {
        values: Vec<i8>,
    },
    JChars {
        values: Vec<u16>,
    },
    JShorts {
        values: Vec<i16>,
    },
    JInts {
        values: Vec<i32>,
    },
    JLongs {
        values: Vec<i64>,
    },
    JBools {
        values: Vec<bool>,
    },
    ValuePick {
        value_index: usize,
        array_length: usize,
    },
    ValuePicks {
        value_indexes: Vec<usize>,
        array_length: usize,
    },
    AsciiString {
        value: String,
        max_length: usize,
    },
    RemainingAsciiString {
        value: String,
    },
    JString {
        value: String,
        max_length: usize,
    },
    RemainingJString {
        value: String,
    },
    RemainingJBytes {
        values: Vec<i8>,
    },
    RemainingBytesMark {
        value: usize,
    },
}

enum Utf8State {
    LeadingByteGeneric,
    ContinuationByteGeneric,
    ContinuationByteLowLeadingByte,
    FirstContinuationByteLowLeadingByte,
    FirstContinuationByteSurrogateLeadingByte,
    FirstContinuationByteGeneric,
    SecondContinuationByteGeneric,
    LeadingByteLowSurrogate,
    FirstContinuationByteLowSurrogate,
    SecondContinuationByteHighSurrogate,
    SecondContinuationByteLowSurrogate,
}

#[derive(Default)]
pub struct JazzerFdpEncoder {
    inner: crate::FdpEncoder,
    #[cfg(feature = "debug")]
    call_log: Vec<JazzerFdpCall>,
}

fn get_jfloat_type_val(value: f32) -> u16 {
    const MAX_NEGATIVE: f32 = -f32::MIN_POSITIVE;
    const F32_MIN_POSITIVE_SUBNORMAL: f32 = 1e-45;
    const F32_MAX_NEGATIVE_SUBNORMAL: f32 = -1e-45;

    match value {
        // 0.0 is semantically equal to -0.0, therefore these two are the same match pattern by itself
        | 0.0 if value.is_sign_positive() => 0,
        | -0.0 => 1,
        | f32::INFINITY => 2,
        | f32::NEG_INFINITY => 3,
        | _ if value.is_nan() => 4,
        | F32_MIN_POSITIVE_SUBNORMAL => 5,
        | F32_MAX_NEGATIVE_SUBNORMAL => 6,
        | f32::MIN_POSITIVE => 7,
        | MAX_NEGATIVE => 8,
        | f32::MAX => 9,
        | f32::MIN => 10,
        | _ => 11,
    }
}

fn get_jdouble_type_val(value: f64) -> u16 {
    const MAX_NEGATIVE: f64 = -f64::MIN_POSITIVE;
    const F64_MIN_POSITIVE_SUBNORMAL: f64 = 5e-324;
    const F64_MAX_NEGATIVE_SUBNORMAL: f64 = -5e-324;

    match value {
        // 0.0 is semantically equal to -0.0, therefore these two are the same match pattern by itself
        | 0.0 if value.is_sign_positive() => 0,
        | -0.0 => 1,
        | f64::INFINITY => 2,
        | f64::NEG_INFINITY => 3,
        | _ if value.is_nan() => 4,
        | F64_MIN_POSITIVE_SUBNORMAL => 5,
        | F64_MAX_NEGATIVE_SUBNORMAL => 6,
        | f64::MIN_POSITIVE => 7,
        | MAX_NEGATIVE => 8,
        | f64::MAX => 9,
        | f64::MIN => 10,
        | _ => 11,
    }
}

fn escape_mutf8_string(value: &[u8]) -> BytesMut {
    let mut converted = BytesMut::with_capacity(value.len());
    // This must be safe because char area < 0x80 should always be a component of one byte char unit.
    for byte in value {
        if *byte == 0x5C {
            converted.put_u16(0x5C5C);
        } else {
            converted.put_u8(*byte);
        }
    }
    converted
}

fn check_jstring_length(value: &[u8]) -> Result<(usize, Vec<usize>), EncoderError> {
    const K_TWO_BYTE_ZERO_LEADING_BYTE: u8 = 0b11000000;
    const K_TWO_BYTE_ZERO_CONTINUATION_BYTE: u8 = 0b10000000;
    const K_THREE_BYTE_LOW_LEADING_BYTE: u8 = 0b11100000;
    const K_SURROGATE_LEADING_BYTE: u8 = 0b11101101;

    fn check_continuation_byte(byte: u8) -> Result<(), EncoderError> {
        if !((byte & (1 << 7) != 0) && (byte & (1 << 6) == 0)) {
            Err(EncoderError::InvalidInput(
                "Invalid modified UTF-8 byte".to_owned(),
            ))
        } else {
            Ok(())
        }
    }

    let mut length = 0;
    let mut state = Utf8State::LeadingByteGeneric;
    let mut prev_byte = 0;
    let mut shrinkable_zero_byte_pos = Vec::new();
    for (idx, byte) in value.iter().enumerate() {
        match state {
            | Utf8State::LeadingByteGeneric => match byte.leading_ones() {
                | 0 if *byte == 0 => {
                    return Err(EncoderError::InvalidInput(
                        "Invalid modified UTF-8 byte".to_owned(),
                    ));
                },
                | 0 => length += 1,
                | 1 => {
                    return Err(EncoderError::InvalidInput(
                        "Invalid modified UTF-8 byte".to_owned(),
                    ))
                },
                | 2 => {
                    if byte & 0b00011110 == 0 {
                        state = Utf8State::ContinuationByteLowLeadingByte;
                    } else {
                        state = Utf8State::ContinuationByteGeneric;
                    }
                },
                | 3 => match *byte {
                    | K_THREE_BYTE_LOW_LEADING_BYTE => {
                        state = Utf8State::FirstContinuationByteLowLeadingByte;
                    },
                    | K_SURROGATE_LEADING_BYTE => {
                        state = Utf8State::FirstContinuationByteSurrogateLeadingByte;
                    },
                    | _ => {
                        state = Utf8State::FirstContinuationByteGeneric;
                    },
                },
                | _ => {
                    return Err(EncoderError::InvalidInput(
                        "Invalid modified UTF-8 byte".to_owned(),
                    ))
                },
            },
            | Utf8State::ContinuationByteLowLeadingByte => {
                check_continuation_byte(*byte)?;
                if prev_byte != K_TWO_BYTE_ZERO_LEADING_BYTE
                    || *byte != K_TWO_BYTE_ZERO_CONTINUATION_BYTE
                {
                    if prev_byte & (1 << 1) == 0 {
                        return Err(EncoderError::InvalidInput(
                            "Invalid modified UTF-8 byte".to_owned(),
                        ));
                    }
                } else {
                    shrinkable_zero_byte_pos.push(idx - 1);
                }
                state = Utf8State::LeadingByteGeneric;
                length += 1;
            },
            | Utf8State::ContinuationByteGeneric => {
                check_continuation_byte(*byte)?;
                state = Utf8State::LeadingByteGeneric;
                length += 1;
            },
            | Utf8State::FirstContinuationByteLowLeadingByte => {
                check_continuation_byte(*byte)?;
                if byte & (1 << 5) == 0 {
                    return Err(EncoderError::InvalidInput(
                        "Invalid modified UTF-8 byte".to_owned(),
                    ));
                }
                state = Utf8State::SecondContinuationByteGeneric;
            },
            | Utf8State::FirstContinuationByteSurrogateLeadingByte => {
                check_continuation_byte(*byte)?;
                if byte & (1 << 5) != 0 {
                    if byte & (1 << 4) != 0 {
                        return Err(EncoderError::InvalidInput(
                            "Invalid modified UTF-8 byte".to_owned(),
                        ));
                    }
                    state = Utf8State::SecondContinuationByteHighSurrogate
                } else {
                    state = Utf8State::SecondContinuationByteGeneric
                }
            },
            | Utf8State::FirstContinuationByteGeneric => {
                check_continuation_byte(*byte)?;
                state = Utf8State::SecondContinuationByteGeneric;
            },
            | Utf8State::SecondContinuationByteHighSurrogate => {
                check_continuation_byte(*byte)?;
                state = Utf8State::LeadingByteLowSurrogate;
                length += 1;
            },
            | Utf8State::SecondContinuationByteLowSurrogate
            | Utf8State::SecondContinuationByteGeneric => {
                check_continuation_byte(*byte)?;
                state = Utf8State::LeadingByteGeneric;
                length += 1;
            },
            | Utf8State::LeadingByteLowSurrogate => {
                if *byte != K_SURROGATE_LEADING_BYTE {
                    return Err(EncoderError::InvalidInput(
                        "Invalid modified UTF-8 byte".to_owned(),
                    ));
                }
                state = Utf8State::FirstContinuationByteLowSurrogate
            },
            | Utf8State::FirstContinuationByteLowSurrogate => {
                check_continuation_byte(*byte)?;
                if (byte & (1 << 5) == 0) || (byte & (1 << 4) == 0) {
                    return Err(EncoderError::InvalidInput(
                        "Invalid modified UTF-8 byte".to_owned(),
                    ));
                }
                state = Utf8State::SecondContinuationByteLowSurrogate;
            },
        }
        prev_byte = *byte;
    }
    match state {
        | Utf8State::LeadingByteGeneric => Ok((length, shrinkable_zero_byte_pos)),
        | _ => Err(EncoderError::InvalidInput(
            "Invalid modified UTF-8 byte".to_owned(),
        )),
    }
}

fn adjust_jstring_safe(value: Bytes, adjust_target: usize) -> Bytes {
    // This shouldn't fail as we already did it
    let (_, shrink_pos) = check_jstring_length(&value).unwrap();

    match adjust_target.cmp(&value.len()) {
        | Ordering::Less => {
            let target_shrink = value.len() - adjust_target;
            let mut bytes = BytesMut::with_capacity(adjust_target);
            let mut cursor = 0;
            // This shouldn't fail as variance min should be equal to shrink_pos.len().
            for pos in &shrink_pos[..target_shrink] {
                bytes.extend_from_slice(&value[cursor..*pos]);
                bytes.put_u8(0);
                cursor = pos + 2;
            }
            bytes.extend_from_slice(&value[cursor..]);
            bytes.freeze()
        },
        | Ordering::Equal => value,
        | Ordering::Greater => unreachable!(),
    }
}

fn adjust_jstring(mut value: Bytes, adjust_target: usize) -> Bytes {
    const EXTENSION_SEQUENCE: [u8; 5] =
        [0b11101101, 0b10100000, 0b10000000, 0b11101101, 0b10110000];

    match adjust_target.cmp(&value.len()) {
        | Ordering::Less => {
            value.truncate(adjust_target);
            value
        },
        | Ordering::Equal => value,
        | Ordering::Greater => {
            let extension_length = 2 + adjust_target - value.len();
            let mut bytes = BytesMut::from(value);
            bytes.truncate(bytes.len() - 2);
            // This shouldn't fail as actual max extension should be 3
            let to_extend = &EXTENSION_SEQUENCE[..extension_length];
            bytes.extend_from_slice(to_extend);
            bytes.freeze()
        },
    }
}

fn adjust_remaining_jstring(mut value: Bytes, adjust_target: usize) -> Bytes {
    const EXTENSION_SEQUENCE: [u8; 5] =
        [0b11101101, 0b10100000, 0b10000000, 0b11101101, 0b10110000];

    match adjust_target.cmp(&value.len()) {
        | Ordering::Less => {
            value.truncate(adjust_target);
            value
        },
        | Ordering::Equal => value,
        | Ordering::Greater => {
            let extension_length = adjust_target - value.len();
            let mut bytes = BytesMut::from(value);
            // This shouldn't fail as actual max extension should be 5
            let to_extend = &EXTENSION_SEQUENCE[..extension_length];
            bytes.extend_from_slice(to_extend);
            bytes.freeze()
        },
    }
}

fn preprocess_ascii_string(value: &[u8], escape: bool) -> Result<Bytes, EncoderError> {
    let to_process = if escape {
        &escape_mutf8_string(value)
    } else {
        value
    };
    let mut buffer = BytesMut::with_capacity(to_process.len());

    let mut cursor = 0;
    for pos in find_iter(to_process, &[192, 128]) {
        buffer.extend_from_slice(&to_process[cursor..pos]);
        buffer.put_u8(0);
        cursor = pos + 2;
    }
    buffer.extend_from_slice(&to_process[cursor..]);
    let buffer = buffer.freeze();
    if buffer.iter().any(|x| *x >= 0x80) {
        return Err(EncoderError::InvalidInput(
            "ASCII string containing out of range char".to_owned(),
        ));
    }
    Ok(buffer)
}

impl JazzerFdpEncoder {
    pub fn new() -> Self {
        Default::default()
    }

    pub fn produce_jbyte_in_range_unchecked(
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
        self.call_log.push(JazzerFdpCall::JByte {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jchar_in_range_unchecked(
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
        self.call_log.push(JazzerFdpCall::JChar {
            value,
            range: Some(min..=max),
            no_surrogates: false,
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jshort_in_range_unchecked(
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
        self.call_log.push(JazzerFdpCall::JShort {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jint_in_range_unchecked(
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
        self.call_log.push(JazzerFdpCall::JInt {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jlong_in_range_unchecked(
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
        self.call_log.push(JazzerFdpCall::JLong {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jbyte_unchecked(&mut self, value: i8) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JByte { value, range: None });
        let mut bytes = BytesMut::with_capacity(1);
        bytes.put_i8(value);
        let value = bytes.get_u8();

        self.inner
            .produce_integral_in_range_unchecked(value as i128, u8::MIN as i128..=u8::MAX as i128)
    }

    pub fn produce_jchar_unchecked(&mut self, value: u16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JChar {
            value,
            range: None,
            no_surrogates: false,
        });
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u16::MIN as i128..=u16::MAX as i128)
    }

    pub fn produce_jshort_unchecked(&mut self, value: i16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JShort { value, range: None });
        let mut bytes = BytesMut::with_capacity(2);
        bytes.put_i16(value);
        let value = bytes.get_u16();
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u16::MIN as i128..=u16::MAX as i128)
    }

    pub fn produce_jint_unchecked(&mut self, value: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JInt { value, range: None });
        let mut bytes = BytesMut::with_capacity(4);
        bytes.put_i32(value);
        let value = bytes.get_u32();
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u32::MIN as i128..=u32::MAX as i128)
    }

    pub fn produce_jlong_unchecked(&mut self, value: i64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JLong { value, range: None });
        let mut bytes = BytesMut::with_capacity(8);
        bytes.put_i64(value);
        let value = bytes.get_u64();
        self.inner
            .produce_integral_in_range_unchecked(value as i128, u64::MIN as i128..=u64::MAX as i128)
    }

    pub fn produce_jbool_unchecked(&mut self, value: bool) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JBool { value });
        self.inner.produce_bool_unchecked(value)
    }

    pub fn produce_regular_jfloat_in_range_unchecked(
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
        self.call_log.push(JazzerFdpCall::JFloat {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_float_in_range_unchecked(value, min..=max)
    }

    pub fn produce_regular_jdouble_in_range_unchecked(
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
        self.call_log.push(JazzerFdpCall::JDouble {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_double_in_range_unchecked(value, min..=max)
    }

    pub fn produce_regular_jfloat_unchecked(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JFloat { value, range: None });
        self.inner
            .produce_float_in_range_unchecked(value, f32::MIN..=f32::MAX)
    }

    pub fn produce_regular_jdouble_unchecked(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JDouble { value, range: None });
        self.inner
            .produce_double_in_range_unchecked(value, f64::MIN..=f64::MAX)
    }

    pub fn produce_jfloat_unchecked(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JFloat { value, range: None });
        let type_val = get_jfloat_type_val(value);
        self.inner
            .produce_integral_in_range_unchecked(type_val as i128, 0..=255)?;
        if type_val <= 10 {
            self.inner
                .produce_float_in_range_unchecked(1.0, f32::MIN..=f32::MAX)
        } else {
            self.inner
                .produce_float_in_range_unchecked(value, f32::MIN..=f32::MAX)
        }
    }

    pub fn produce_jdouble_unchecked(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JDouble { value, range: None });
        let type_val = get_jdouble_type_val(value);
        self.inner
            .produce_integral_in_range_unchecked(type_val as i128, 0..=255)?;
        if type_val <= 10 {
            self.inner
                .produce_double_in_range_unchecked(1.0, f64::MIN..=f64::MAX)
        } else {
            self.inner
                .produce_double_in_range_unchecked(value, f64::MIN..=f64::MAX)
        }
    }

    pub fn produce_probability_jfloat_unchecked(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ProbJFloat { value });
        self.inner.produce_probability_float_unchecked(value)
    }

    pub fn produce_probability_jdouble_unchecked(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ProbJDouble { value });
        self.inner.produce_probability_double_unchecked(value)
    }

    pub fn produce_jbytes_unchecked(&mut self, values: &[i8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JBytes {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i8(*value);
        }
        self.inner.produce_bytes_unchecked(&buf);
        Ok(())
    }

    pub fn produce_jchars_unchecked(&mut self, values: &[u16]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JChars {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_u16_ne(*value);
        }
        self.inner.produce_bytes_unchecked(&buf);
        Ok(())
    }

    pub fn produce_jshorts_unchecked(&mut self, values: &[i16]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JShorts {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i16_ne(*value);
        }
        self.inner.produce_bytes_unchecked(&buf);
        Ok(())
    }

    pub fn produce_jints_unchecked(&mut self, values: &[i32]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JInts {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i32_ne(*value);
        }
        self.inner.produce_bytes_unchecked(&buf);
        Ok(())
    }

    pub fn produce_jlongs_unchecked(&mut self, values: &[i64]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JLongs {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i64_ne(*value);
        }
        self.inner.produce_bytes_unchecked(&buf);
        Ok(())
    }

    pub fn produce_jbools_unchecked(&mut self, values: &[bool]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JBools {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_u8(*value as u8);
        }
        self.inner.produce_bytes_unchecked(&buf);
        Ok(())
    }

    pub fn produce_remaining_as_jbytes_unchecked(&mut self, values: &[i8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::RemainingJBytes {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i8(*value);
        }
        self.inner.produce_remaining_bytes_unchecked(&buf);
        Ok(())
    }

    fn produce_ascii_string_call(
        &mut self,
        data: &str,
        max_length: Option<usize>,
    ) -> Result<FdpStagedCall, EncoderError> {
        let encoded = mutf8::encode(data);
        let mut buffer = BytesMut::from(preprocess_ascii_string(&encoded, max_length.is_some())?);
        let (actual_length, _) = check_jstring_length(&encoded)?;
        let length_variance = match max_length {
            | Some(max_length) if actual_length < max_length => {
                buffer.put_u16(0x5C00);
                Some(LengthVariance {
                    range: -2..=0,
                    adjustment_method: adjust_with_zero,
                })
            },
            | None if data.is_empty() => Some(LengthVariance {
                range: 0..=1,
                adjustment_method: adjust_with_zero,
            }),
            | Some(max_length) if actual_length > max_length => {
                return Err(EncoderError::InputTooLong(max_length));
            },
            | _ => None,
        };

        // Remaining ascii string cannot produce string with 1 byte length
        if max_length.is_none() && actual_length == 1 {
            return Err(EncoderError::InputTooShort(1));
        }

        let extra_bytes_required = if buffer.len() == 1 { 1 } else { 0 };
        let call = FdpStagedCall {
            id: self.inner.get_call_id(),
            variance: None,
            variance_on_finalization: length_variance,
            extra_bytes_required,
            candidate: buffer.freeze(),
            user_call: self.inner.current_scope.clone(),
            finish_mark: max_length.is_none(),
            reversed: false,
        };
        Ok(call)
    }

    // NOTE: max_length doesn't necessarily mean the length of bytes even in ascii string
    pub fn produce_ascii_string_unchecked(
        &mut self,
        value: &str,
        max_length: i32,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::AsciiString {
            value: value.to_owned(),
            max_length: max_length as usize,
        });
        let call = self.produce_ascii_string_call(value, Some(max_length as usize))?;
        self.inner.stage_and_flush_unchecked(call);
        Ok(())
    }

    pub fn produce_remaining_as_ascii_string_unchecked(&mut self, value: &str) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::RemainingAsciiString {
            value: value.to_owned(),
        });
        let call = self.produce_ascii_string_call(value, None)?;
        self.inner.stage_and_flush_unchecked(call);
        Ok(())
    }

    fn produce_jstring_call(
        &mut self,
        data: &str,
        max_length: Option<usize>,
    ) -> Result<FdpStagedCall, EncoderError> {
        let encoded = mutf8::encode(data);
        let mut to_process = if max_length.is_some() {
            escape_mutf8_string(&encoded)
        } else {
            BytesMut::from(encoded.as_ref())
        };
        // WARN: this shrink_pos content cannot be used directly to escaped string.
        let (jstring_length, shrink_pos) = check_jstring_length(&encoded)?;
        let variance_finalize = match max_length {
            | Some(max_length) if jstring_length < max_length => {
                to_process.put_u16(0x5C00);
                let max_extension = if jstring_length + 1 < max_length {
                    3
                } else {
                    0
                };
                Some(LengthVariance {
                    range: -2..=max_extension,
                    adjustment_method: adjust_jstring,
                })
            },
            | Some(max_length) if jstring_length > max_length => {
                return Err(EncoderError::InputTooLong(max_length));
            },
            | None => Some(LengthVariance {
                range: 0..=5,
                adjustment_method: adjust_remaining_jstring,
            }),
            | _ => None,
        };

        let variance = if shrink_pos.is_empty() {
            None
        } else {
            let max_shrink = shrink_pos.len() as isize;
            Some(LengthVariance {
                range: -max_shrink..=0,
                adjustment_method: adjust_jstring_safe,
            })
        };

        let extra_bytes_required = if to_process.len() == 1 { 1 } else { 0 };
        let call = FdpStagedCall {
            id: self.inner.get_call_id(),
            variance,
            variance_on_finalization: variance_finalize,
            extra_bytes_required,
            candidate: to_process.freeze(),
            user_call: self.inner.current_scope.clone(),
            finish_mark: max_length.is_none(),
            reversed: false,
        };
        Ok(call)
    }

    pub fn produce_jstring_unchecked(&mut self, value: &str, max_length: i32) -> EncoderResult {
        let max_length = max_length as usize;
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JString {
            value: value.to_owned(),
            max_length,
        });
        let call = self.produce_jstring_call(value, Some(max_length))?;
        self.inner.stage_and_flush_unchecked(call);
        Ok(())
    }

    pub fn produce_remaining_as_jstring_unchecked(&mut self, value: &str) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::RemainingJString {
            value: value.to_owned(),
        });
        let call = self.produce_jstring_call(value, None)?;
        self.inner.stage_and_flush_unchecked(call);
        Ok(())
    }

    pub fn produce_picked_value_index_in_jarray_unchecked(
        &mut self,
        value: usize,
        length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ValuePick {
            value_index: value,
            array_length: length,
        });
        self.inner
            .produce_array_value_picker_unchecked(value, length)
    }

    pub fn produce_picked_value_indexes_in_jarray_unchecked(
        &mut self,
        values: &[usize],
        length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ValuePicks {
            value_indexes: values.to_vec(),
            array_length: length,
        });
        if length < values.len() {
            return Err(EncoderError::InputTooShort(length));
        }

        let mut index_array: Vec<usize> = (0..length).collect();
        for value in values {
            let chosen_index = index_array.binary_search(value).map_err(|_| {
                EncoderError::ValueNotInRange(
                    value.to_string(),
                    0.to_string(),
                    (length - 1).to_string(),
                )
            })?;
            self.inner
                .produce_array_value_picker_unchecked(chosen_index, index_array.len())?;
            index_array.remove(chosen_index);
        }
        Ok(())
    }

    pub fn produce_jbyte_in_range(&mut self, value: i8, min: i8, max: i8) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JByte {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jchar_in_range(&mut self, value: u16, min: u16, max: u16) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JChar {
            value,
            range: Some(min..=max),
            no_surrogates: false,
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jshort_in_range(&mut self, value: i16, min: i16, max: i16) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JShort {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jint_in_range(&mut self, value: i32, min: i32, max: i32) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JInt {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jlong_in_range(&mut self, value: i64, min: i64, max: i64) -> EncoderResult {
        if min > max {
            return Err(EncoderError::InvalidRangeInput(
                min.to_string(),
                max.to_string(),
            ));
        }
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JLong {
            value,
            range: Some(min..=max),
        });
        self.inner
            .produce_integral_in_range(value as i128, min as i128..=max as i128)
    }

    pub fn produce_jbyte(&mut self, value: i8) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JByte { value, range: None });
        let mut bytes = BytesMut::with_capacity(1);
        bytes.put_i8(value);
        let value = bytes.get_u8();
        self.inner
            .produce_integral_in_range(value as i128, u8::MIN as i128..=u8::MAX as i128)
    }

    pub fn produce_jchar(&mut self, value: u16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JChar {
            value,
            range: None,
            no_surrogates: false,
        });
        self.inner
            .produce_integral_in_range(value as i128, u16::MIN as i128..=u16::MAX as i128)
    }

    pub fn produce_jchar_no_surrogates(&mut self, value: u16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JChar {
            value,
            range: None,
            no_surrogates: true,
        });
        if (0xd800..0xe000).contains(&value) {
            return Err(EncoderError::InvalidInput(value.to_string()));
        }
        self.produce_jchar(value)
    }

    pub fn produce_jshort(&mut self, value: i16) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JShort { value, range: None });
        let mut bytes = BytesMut::with_capacity(2);
        bytes.put_i16(value);
        let value = bytes.get_u16();
        self.inner
            .produce_integral_in_range(value as i128, u16::MIN as i128..=u16::MAX as i128)
    }

    pub fn produce_jint(&mut self, value: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JInt { value, range: None });
        let mut bytes = BytesMut::with_capacity(4);
        bytes.put_i32(value);
        let value = bytes.get_u32();
        self.inner
            .produce_integral_in_range(value as i128, u32::MIN as i128..=u32::MAX as i128)
    }

    pub fn produce_jlong(&mut self, value: i64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JLong { value, range: None });
        let mut bytes = BytesMut::with_capacity(8);
        bytes.put_i64(value);
        let value = bytes.get_u64();
        self.inner
            .produce_integral_in_range(value as i128, u64::MIN as i128..=u64::MAX as i128)
    }

    pub fn produce_jbool(&mut self, value: bool) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JBool { value });
        self.inner.produce_bool(value)
    }

    pub fn produce_regular_jfloat_in_range(
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
        self.call_log.push(JazzerFdpCall::JFloat {
            value,
            range: Some(min..=max),
        });
        self.inner.produce_float_in_range(value, min..=max)
    }

    pub fn produce_regular_jdouble_in_range(
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
        self.call_log.push(JazzerFdpCall::JDouble {
            value,
            range: Some(min..=max),
        });
        self.inner.produce_double_in_range(value, min..=max)
    }

    pub fn produce_regular_jfloat(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JFloat { value, range: None });
        self.inner
            .produce_float_in_range(value, f32::MIN..=f32::MAX)
    }

    pub fn produce_regular_jdouble(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JDouble { value, range: None });
        self.inner
            .produce_double_in_range(value, f64::MIN..=f64::MAX)
    }

    pub fn produce_jfloat(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JFloat { value, range: None });
        let type_val = get_jfloat_type_val(value);
        self.inner
            .produce_integral_in_range(type_val as i128, 0..=255)?;
        if type_val <= 10 {
            self.inner.produce_float_in_range(1.0, f32::MIN..=f32::MAX)
        } else {
            self.inner
                .produce_float_in_range(value, f32::MIN..=f32::MAX)
        }
    }

    pub fn produce_jdouble(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::JDouble { value, range: None });
        let type_val = get_jdouble_type_val(value);
        self.inner
            .produce_integral_in_range(type_val as i128, 0..=255)?;
        if type_val <= 10 {
            self.inner.produce_double_in_range(1.0, f64::MIN..=f64::MAX)
        } else {
            self.inner
                .produce_double_in_range(value, f64::MIN..=f64::MAX)
        }
    }

    pub fn produce_probability_jfloat(&mut self, value: f32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ProbJFloat { value });
        self.inner.produce_probability_float(value)
    }

    pub fn produce_probability_jdouble(&mut self, value: f64) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ProbJDouble { value });
        self.inner.produce_probability_double(value)
    }

    // maxLength is defined as int in Jazzer API
    pub fn produce_jbytes(&mut self, values: &[i8], max_length: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JBytes {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i8(*value);
        }
        self.inner
            .produce_bytes(&buf, max_length as usize * size_of::<i8>())
    }

    pub fn produce_jchars(&mut self, values: &[u16], max_length: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JChars {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_u16_ne(*value);
        }
        self.inner
            .produce_bytes(&buf, max_length as usize * size_of::<u16>())
    }

    pub fn produce_jshorts(&mut self, values: &[i16], max_length: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JShorts {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i16_ne(*value);
        }
        self.inner
            .produce_bytes(&buf, max_length as usize * size_of::<i16>())
    }

    pub fn produce_jints(&mut self, values: &[i32], max_length: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JInts {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i32_ne(*value);
        }
        self.inner
            .produce_bytes(&buf, max_length as usize * size_of::<i32>())
    }

    pub fn produce_jlongs(&mut self, values: &[i64], max_length: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JLongs {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i64_ne(*value);
        }
        self.inner
            .produce_bytes(&buf, max_length as usize * size_of::<i64>())
    }

    pub fn produce_jbools(&mut self, values: &[bool], max_length: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JBools {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_u8(*value as u8);
        }
        self.inner
            .produce_bytes(&buf, max_length as usize * size_of::<u8>())
    }

    pub fn produce_remaining_as_jbytes(&mut self, values: &[i8]) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::RemainingJBytes {
            values: values.to_vec(),
        });
        let mut buf = BytesMut::with_capacity(size_of_val(values));
        for value in values {
            buf.put_i8(*value);
        }
        self.inner.produce_remaining_bytes(&buf)
    }

    // NOTE: max_length doesn't necessarily mean the length of bytes even in ascii string
    pub fn produce_ascii_string(&mut self, value: &str, max_length: i32) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::AsciiString {
            value: value.to_owned(),
            max_length: max_length as usize,
        });
        let call = self.produce_ascii_string_call(value, Some(max_length as usize))?;
        self.inner.stage_and_flush(call)
    }

    pub fn produce_remaining_as_ascii_string(&mut self, value: &str) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::RemainingAsciiString {
            value: value.to_owned(),
        });
        let call = self.produce_ascii_string_call(value, None)?;
        self.inner.stage_and_flush(call)
    }

    pub fn produce_jstring(&mut self, value: &str, max_length: i32) -> EncoderResult {
        let max_length = max_length as usize;
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::JString {
            value: value.to_owned(),
            max_length,
        });
        let call = self.produce_jstring_call(value, Some(max_length))?;
        self.inner.stage_and_flush(call)
    }

    pub fn produce_remaining_as_jstring(&mut self, value: &str) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::RemainingJString {
            value: value.to_owned(),
        });
        let call = self.produce_jstring_call(value, None)?;
        self.inner.stage_and_flush(call)
    }

    pub fn produce_picked_value_index_in_jarray(
        &mut self,
        value: usize,
        length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ValuePick {
            value_index: value,
            array_length: length,
        });
        self.inner.produce_array_value_picker(value, length)
    }

    pub fn produce_picked_value_indexes_in_jarray(
        &mut self,
        values: &[usize],
        length: usize,
    ) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log.push(JazzerFdpCall::ValuePicks {
            value_indexes: values.to_vec(),
            array_length: length,
        });
        if length < values.len() {
            return Err(EncoderError::InputTooShort(length));
        }

        let mut index_array: Vec<usize> = (0..length).collect();
        for value in values {
            let chosen_index = index_array.binary_search(value).map_err(|_| {
                EncoderError::ValueNotInRange(
                    value.to_string(),
                    0.to_string(),
                    (length - 1).to_string(),
                )
            })?;
            self.inner
                .produce_array_value_picker(chosen_index, index_array.len())?;
            index_array.remove(chosen_index);
        }
        Ok(())
    }

    pub fn mark_remaining_bytes(&mut self, value: usize) -> EncoderResult {
        #[cfg(feature = "debug")]
        self.call_log
            .push(JazzerFdpCall::RemainingBytesMark { value });
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
