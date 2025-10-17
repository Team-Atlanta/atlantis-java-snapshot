use std::ffi::c_void;

use fdp_reference::*;

use crate::{
    encoder::{llvm::*, EncoderResult},
    EncoderError,
};

unsafe fn consume_one(fdp: *mut c_void, call: &LlvmFdpCall) -> bool {
    match call {
        | LlvmFdpCall::Byte { value, range: None } => consumeByte(fdp) == *value,
        | LlvmFdpCall::Byte {
            value,
            range: Some(range),
        } => consumeByteInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::Char { value, range: None } => consumeChar(fdp) == *value,
        | LlvmFdpCall::Char {
            value,
            range: Some(range),
        } => consumeCharInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::Short { value, range: None } => consumeShort(fdp) == *value,
        | LlvmFdpCall::Short {
            value,
            range: Some(range),
        } => consumeShortInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::UShort { value, range: None } => consumeUnsignedShort(fdp) == *value,
        | LlvmFdpCall::UShort {
            value,
            range: Some(range),
        } => consumeUnsignedShortInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::Int { value, range: None } => consumeInt(fdp) == *value,
        | LlvmFdpCall::Int {
            value,
            range: Some(range),
        } => consumeIntInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::UInt { value, range: None } => consumeUnsignedInt(fdp) == *value,
        | LlvmFdpCall::UInt {
            value,
            range: Some(range),
        } => consumeUnsignedIntInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::LongLong { value, range: None } => consumeLongLong(fdp) == *value,
        | LlvmFdpCall::LongLong {
            value,
            range: Some(range),
        } => consumeLongLongInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::ULongLong { value, range: None } => consumeUnsignedLongLong(fdp) == *value,
        | LlvmFdpCall::ULongLong {
            value,
            range: Some(range),
        } => consumeUnsignedLongLongInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::Bool { value } => consumeBool(fdp) == *value,
        | LlvmFdpCall::Float { value, range: None } => consumeFloat(fdp) == *value,
        | LlvmFdpCall::Float {
            value,
            range: Some(range),
        } => consumeFloatInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::ProbFloat { value } => consumeProbabilityFloat(fdp) == *value,
        | LlvmFdpCall::Double { value, range: None } => consumeDouble(fdp) == *value,
        | LlvmFdpCall::Double {
            value,
            range: Some(range),
        } => consumeDoubleInRange(fdp, *range.start(), *range.end()) == *value,
        | LlvmFdpCall::ProbDouble { value } => consumeProbabilityDouble(fdp) == *value,
        | LlvmFdpCall::Enum { value, max_k } => consumeEnum(fdp, *max_k) == *value,
        | LlvmFdpCall::Bytes {
            value,
            terminator: None,
        } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeBytes(fdp, buf.as_mut_ptr(), value.len());
            buf == *value
        },
        | LlvmFdpCall::Bytes {
            value,
            terminator: Some(terminator),
        } => {
            let mut buf = vec![0; value.len()];
            let _read =
                consumeBytesWithTerminator(fdp, buf.as_mut_ptr(), value.len() - 1, *terminator);
            buf == *value
        },
        | LlvmFdpCall::String {
            value,
            requested_length: None,
        } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeBytesAsString(fdp, buf.as_mut_ptr(), value.len());
            buf == *value
        },
        | LlvmFdpCall::String {
            value,
            requested_length: Some(requested_length),
        } => {
            let mut buf = vec![0; *requested_length];
            let _read = consumeBytesAsString(fdp, buf.as_mut_ptr(), *requested_length);
            buf[..value.len()] == *value
        },
        | LlvmFdpCall::RandomString {
            value,
            max_length: None,
        } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeRandomLengthString(fdp, buf.as_mut_ptr());
            buf == *value
        },
        | LlvmFdpCall::RandomString {
            value,
            max_length: Some(max_length),
        } => {
            let mut buf = vec![0; *max_length];
            let read = consumeRandomLengthStringWithMaxLength(fdp, buf.as_mut_ptr(), *max_length);
            buf[..read] == *value
        },
        | LlvmFdpCall::ValuePick {
            value_index,
            array_length,
        } => pickValueIndexInArray(fdp, *array_length) == *value_index,
        | LlvmFdpCall::RemainingBytes { value } => {
            let mut buf = vec![0; value.len()];
            let read = consumeRemainingBytes(fdp, buf.as_mut_ptr());
            buf[..read] == *value
        },
        | LlvmFdpCall::RemainingBytesMark { value } => remainingBytes(fdp) == *value,
        | LlvmFdpCall::RemainingString { value } => {
            let mut buf = vec![0; value.len()];
            let read = consumeRemainingBytesAsString(fdp, buf.as_mut_ptr());
            buf[..read] == *value
        },
    }
}

pub fn test_consume(data: &[u8], call_list: &[LlvmFdpCall]) -> EncoderResult {
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
