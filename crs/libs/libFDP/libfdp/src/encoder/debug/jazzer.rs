use std::ffi::c_void;

use fdp_reference::*;
use simd_cesu8::mutf8;

use crate::{
    encoder::{jazzer::*, EncoderResult},
    EncoderError,
};

unsafe fn consume_one(fdp: *mut c_void, call: &JazzerFdpCall) -> bool {
    match call {
        | JazzerFdpCall::JByte { value, range: None } => consumeJByte(fdp) == *value,
        | JazzerFdpCall::JByte {
            value,
            range: Some(range),
        } => consumeJByteInRange(fdp, *range.start(), *range.end()) == *value,
        | JazzerFdpCall::JChar {
            value,
            range: None,
            no_surrogates: false,
        } => consumeJChar(fdp) == *value,
        | JazzerFdpCall::JChar {
            value,
            range: None,
            no_surrogates: true,
        } => consumeJCharNoSurrogates(fdp) == *value,
        | JazzerFdpCall::JChar {
            value,
            range: Some(range),
            no_surrogates: _,
        } => consumeJCharInRange(fdp, *range.start(), *range.end()) == *value,
        | JazzerFdpCall::JInt { value, range: None } => consumeJInt(fdp) == *value,
        | JazzerFdpCall::JInt {
            value,
            range: Some(range),
        } => consumeJIntInRange(fdp, *range.start(), *range.end()) == *value,
        | JazzerFdpCall::JLong { value, range: None } => consumeJLong(fdp) == *value,
        | JazzerFdpCall::JLong {
            value,
            range: Some(range),
        } => consumeJLongInRange(fdp, *range.start(), *range.end()) == *value,
        | JazzerFdpCall::JShort { value, range: None } => consumeJShort(fdp) == *value,
        | JazzerFdpCall::JShort {
            value,
            range: Some(range),
        } => consumeJShortInRange(fdp, *range.start(), *range.end()) == *value,
        | JazzerFdpCall::JBool { value } => (consumeJBoolean(fdp) != 0) == *value,
        | JazzerFdpCall::JDouble { value, range: None } => {
            let out = consumeJDouble(fdp);
            if out.is_nan() {
                value.is_nan()
            } else {
                out == *value
            }
        },
        | JazzerFdpCall::JDouble {
            value,
            range: Some(range),
        } => consumeRegularJDoubleInRange(fdp, *range.start(), *range.end()) == *value,
        | JazzerFdpCall::ProbJDouble { value } => consumeProbabilityJDouble(fdp) == *value,
        | JazzerFdpCall::JFloat { value, range: None } => {
            let out = consumeJFloat(fdp);
            if out.is_nan() {
                value.is_nan()
            } else {
                out == *value
            }
        },
        | JazzerFdpCall::JFloat {
            value,
            range: Some(range),
        } => consumeRegularJFloatInRange(fdp, *range.start(), *range.end()) == *value,
        | JazzerFdpCall::ProbJFloat { value } => consumeProbabilityJFloat(fdp) == *value,
        | JazzerFdpCall::JBools { values } => {
            let mut buf = vec![0; values.len()];
            consumeJBooleans(fdp, buf.as_mut_ptr(), buf.len());
            *values == buf.iter().map(|x| *x != 0).collect::<Vec<_>>()
        },
        | JazzerFdpCall::JBytes { values } => {
            let mut buf = vec![0; values.len()];
            consumeJBytes(fdp, buf.as_mut_ptr(), buf.len());
            *values == buf
        },
        | JazzerFdpCall::JChars { values } => {
            let mut buf = vec![0; values.len()];
            consumeJChars(fdp, buf.as_mut_ptr(), buf.len());
            *values == buf
        },
        | JazzerFdpCall::JInts { values } => {
            let mut buf = vec![0; values.len()];
            consumeJInts(fdp, buf.as_mut_ptr(), buf.len());
            *values == buf
        },
        | JazzerFdpCall::JLongs { values } => {
            let mut buf = vec![0; values.len()];
            consumeJLongs(fdp, buf.as_mut_ptr(), buf.len());
            *values == buf
        },
        | JazzerFdpCall::JShorts { values } => {
            let mut buf = vec![0; values.len()];
            consumeJShorts(fdp, buf.as_mut_ptr(), buf.len());
            *values == buf
        },
        | JazzerFdpCall::ValuePick {
            value_index,
            array_length,
        } => pickValueIndexInJArray(fdp, *array_length) == *value_index,
        | JazzerFdpCall::ValuePicks {
            value_indexes,
            array_length,
        } => {
            let mut buf = vec![0; value_indexes.len()];
            pickValueIndexesInJArray(fdp, buf.as_mut_ptr(), buf.len(), *array_length);
            *value_indexes == buf
        },
        | JazzerFdpCall::RemainingJBytes { values } => {
            let mut buf = vec![0; values.len()];
            consumeRemainingAsJBytes(fdp, buf.as_mut_ptr());
            *values == buf
        },
        | JazzerFdpCall::RemainingBytesMark { value } => remainingBytes(fdp) == *value,
        | JazzerFdpCall::AsciiString { value, max_length } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let byte_length = consumeAsciiString(fdp, buf.as_mut_ptr(), *max_length);
            encoded.len() == byte_length && *encoded == buf[..byte_length]
        },
        | JazzerFdpCall::RemainingAsciiString { value } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let byte_length = consumeRemainingAsAsciiString(fdp, buf.as_mut_ptr());
            encoded.len() == byte_length && *encoded == buf[..byte_length]
        },
        | JazzerFdpCall::JString { value, max_length } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let byte_length = consumeJString(fdp, buf.as_mut_ptr(), *max_length);
            encoded.len() == byte_length && *encoded == buf[..byte_length]
        },
        | JazzerFdpCall::RemainingJString { value } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let byte_length = consumeRemainingAsJString(fdp, buf.as_mut_ptr());
            encoded.len() == byte_length && *encoded == buf[..byte_length]
        },
    }
}

pub fn test_consume(data: &[u8], call_list: &[JazzerFdpCall]) -> EncoderResult {
    unsafe {
        let fdp = init(data.as_ptr(), data.len());
        for call in call_list {
            if !consume_one(fdp, call) {
                return Err(EncoderError::OutputMismatch(format!("{:?}", call)));
            }
        }
        deinit(fdp);
    }
    Ok(())
}
