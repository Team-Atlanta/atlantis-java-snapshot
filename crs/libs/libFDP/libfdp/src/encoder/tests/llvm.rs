use std::{ffi::c_void, ops::RangeInclusive};

use fdp_reference::*;
use itertools::{repeat_n, Itertools};
use rand::prelude::*;

use crate::encoder::llvm::*;

fn generate_float(range: RangeInclusive<f32>) -> f32 {
    let mut rng = rand::rng();
    let zero = 0.0f32;
    let min = *range.start();
    let max = *range.end();

    let mut range = 0.0;
    let mut result = min;
    if max > zero && min < zero && max > min + f32::MAX {
        if rng.random() {
            range = (max / 2.0) - (min / 2.0);
            result += range;
        }
    } else {
        range = max - min;
    };
    result + range * generate_prob_float()
}

fn generate_prob_float() -> f32 {
    let mut rng = rand::rng();
    let chosen = rng.random::<u32>();
    chosen as f32 / u32::MAX as f32
}

fn generate_double(range: RangeInclusive<f64>) -> f64 {
    let mut rng = rand::rng();
    let zero = 0.0f64;
    let min = *range.start();
    let max = *range.end();

    let mut range = 0.0;
    let mut result = min;
    if max > zero && min < zero && max > min + f64::MAX {
        if rng.random() {
            range = (max / 2.0) - (min / 2.0);
            result += range;
        }
    } else {
        range = max - min;
    };
    result + range * generate_prob_double()
}

fn generate_prob_double() -> f64 {
    let mut rng = rand::rng();
    let chosen = rng.random::<u64>();
    chosen as f64 / u64::MAX as f64
}

fn generate_one(fixed_choice: Option<u32>) -> LlvmFdpCall {
    let mut rng = rand::rng();
    // Do not generate remaining* calls when choice is not intended to be fixed.
    let call_choice = fixed_choice.unwrap_or_else(|| rng.random_range(0..18));

    match call_choice {
        | 0 => {
            let value = rng.random();
            LlvmFdpCall::Bool { value }
        },
        | 1 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::Byte {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::Byte {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 2 => {
            let set_terminator = rng.random();
            let bytes_len = rng.random_range(0..1024);
            let mut bytes_vec = vec![0; bytes_len];
            rng.fill_bytes(&mut bytes_vec);
            if set_terminator {
                let terminator = rng.random();
                bytes_vec.push(terminator);
                LlvmFdpCall::Bytes {
                    value: bytes_vec,
                    terminator: Some(terminator),
                }
            } else {
                LlvmFdpCall::Bytes {
                    value: bytes_vec,
                    terminator: None,
                }
            }
        },
        | 3 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::Char {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::Char {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 4 => {
            if rng.random() {
                let mut randoms = [
                    generate_double(f64::MIN..=f64::MAX),
                    generate_double(f64::MIN..=f64::MAX),
                ];
                randoms.sort_by(|a, b| a.partial_cmp(b).unwrap());
                LlvmFdpCall::Double {
                    value: generate_double(randoms[0]..=randoms[1]),
                    range: Some(randoms[0]..=randoms[1]),
                }
            } else {
                LlvmFdpCall::Double {
                    value: generate_double(f64::MIN..=f64::MAX),
                    range: None,
                }
            }
        },
        | 5 => {
            let mut randoms = [rng.random(), rng.random()];
            randoms.sort();
            LlvmFdpCall::Enum {
                value: randoms[0],
                max_k: randoms[1],
            }
        },
        | 6 => {
            if rng.random() {
                let mut randoms = [
                    generate_float(f32::MIN..=f32::MAX),
                    generate_float(f32::MIN..=f32::MAX),
                ];
                randoms.sort_by(|a, b| a.partial_cmp(b).unwrap());
                LlvmFdpCall::Float {
                    value: generate_float(randoms[0]..=randoms[1]),
                    range: Some(randoms[0]..=randoms[1]),
                }
            } else {
                LlvmFdpCall::Float {
                    value: generate_float(f32::MIN..=f32::MAX),
                    range: None,
                }
            }
        },
        | 7 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::Int {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::Int {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 8 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::LongLong {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::LongLong {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 9 => {
            let random = generate_prob_double();
            LlvmFdpCall::ProbDouble { value: random }
        },
        | 10 => {
            let random = generate_prob_float();
            LlvmFdpCall::ProbFloat { value: random }
        },
        | 11 => {
            let set_max_length = rng.random();
            let mut randoms = [rng.random_range(0..1024), rng.random_range(0..1024)];
            randoms.sort();
            let mut bytes_vec = vec![0; randoms[0]];
            rng.fill_bytes(&mut bytes_vec);
            if set_max_length {
                LlvmFdpCall::RandomString {
                    value: bytes_vec,
                    max_length: Some(randoms[1]),
                }
            } else {
                LlvmFdpCall::RandomString {
                    value: bytes_vec,
                    max_length: None,
                }
            }
        },
        | 12 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::Short {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::Short {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 13 => {
            let set_max_length = rng.random();
            let mut randoms = [rng.random_range(0..1024), rng.random_range(0..1024)];
            randoms.sort();
            let mut bytes_vec = vec![0; randoms[0]];
            rng.fill_bytes(&mut bytes_vec);
            if set_max_length {
                LlvmFdpCall::String {
                    value: bytes_vec,
                    requested_length: Some(randoms[1]),
                }
            } else {
                LlvmFdpCall::String {
                    value: bytes_vec,
                    requested_length: None,
                }
            }
        },
        | 14 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::UInt {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::UInt {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 15 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::ULongLong {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::ULongLong {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 16 => {
            let set_range = rng.random();
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if set_range {
                LlvmFdpCall::UShort {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                LlvmFdpCall::UShort {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 17 => {
            let array_length = rng.random_range(1..1048576);
            let value_index = rng.random_range(0..array_length);
            LlvmFdpCall::ValuePick {
                value_index,
                array_length,
            }
        },
        | 18 => {
            let bytes_len = rng.random_range(0..1024);
            let mut bytes_vec = vec![0; bytes_len];
            rng.fill_bytes(&mut bytes_vec);
            LlvmFdpCall::RemainingBytes { value: bytes_vec }
        },
        | 19 => {
            let bytes_len = rng.random_range(0..1024);
            let mut bytes_vec = vec![0; bytes_len];
            rng.fill_bytes(&mut bytes_vec);
            LlvmFdpCall::RemainingString { value: bytes_vec }
        },
        | _ => unreachable!(),
    }
}

fn produce_one(encoder: &mut LlvmFdpEncoder, call: &LlvmFdpCall) {
    match call {
        | LlvmFdpCall::Byte { value, range: None } => encoder.produce_byte(*value).unwrap(),
        | LlvmFdpCall::Byte {
            value,
            range: Some(range),
        } => encoder
            .produce_byte_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::Char { value, range: None } => encoder.produce_char(*value).unwrap(),
        | LlvmFdpCall::Char {
            value,
            range: Some(range),
        } => encoder
            .produce_char_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::Short { value, range: None } => encoder.produce_short(*value).unwrap(),
        | LlvmFdpCall::Short {
            value,
            range: Some(range),
        } => encoder
            .produce_short_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::UShort { value, range: None } => {
            encoder.produce_unsigned_short(*value).unwrap()
        },
        | LlvmFdpCall::UShort {
            value,
            range: Some(range),
        } => encoder
            .produce_unsigned_short_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::Int { value, range: None } => encoder.produce_int(*value).unwrap(),
        | LlvmFdpCall::Int {
            value,
            range: Some(range),
        } => encoder
            .produce_int_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::UInt { value, range: None } => encoder.produce_unsigned_int(*value).unwrap(),
        | LlvmFdpCall::UInt {
            value,
            range: Some(range),
        } => encoder
            .produce_unsigned_int_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::LongLong { value, range: None } => {
            encoder.produce_long_long(*value).unwrap()
        },
        | LlvmFdpCall::LongLong {
            value,
            range: Some(range),
        } => encoder
            .produce_long_long_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::ULongLong { value, range: None } => {
            encoder.produce_unsigned_long_long(*value).unwrap()
        },
        | LlvmFdpCall::ULongLong {
            value,
            range: Some(range),
        } => encoder
            .produce_unsigned_long_long_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::Bool { value } => encoder.produce_bool(*value).unwrap(),
        | LlvmFdpCall::Float { value, range: None } => encoder.produce_float(*value).unwrap(),
        | LlvmFdpCall::Float {
            value,
            range: Some(range),
        } => encoder
            .produce_float_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::ProbFloat { value } => encoder.produce_probability_float(*value).unwrap(),
        | LlvmFdpCall::Double { value, range: None } => encoder.produce_double(*value).unwrap(),
        | LlvmFdpCall::Double {
            value,
            range: Some(range),
        } => encoder
            .produce_double_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | LlvmFdpCall::ProbDouble { value } => encoder.produce_probability_double(*value).unwrap(),
        | LlvmFdpCall::Enum { value, max_k } => encoder.produce_enum(*value, *max_k).unwrap(),
        | LlvmFdpCall::Bytes {
            value,
            terminator: None,
        } => encoder.produce_bytes(value, value.len()).unwrap(),
        | LlvmFdpCall::Bytes {
            value,
            terminator: Some(terminator),
        } => encoder
            .produce_bytes_with_terminator(value, value.len() - 1, *terminator)
            .unwrap(),
        | LlvmFdpCall::String {
            value,
            requested_length: None,
        } => encoder.produce_bytes_as_string(value, value.len()).unwrap(),
        | LlvmFdpCall::String {
            value,
            requested_length: Some(requested_length),
        } => encoder
            .produce_bytes_as_string(value, *requested_length)
            .unwrap(),
        | LlvmFdpCall::RandomString {
            value,
            max_length: None,
        } => encoder.produce_random_length_string(value).unwrap(),
        | LlvmFdpCall::RandomString {
            value,
            max_length: Some(max_length),
        } => encoder
            .produce_random_length_string_with_max_length(value, *max_length)
            .unwrap(),
        | LlvmFdpCall::ValuePick {
            value_index,
            array_length,
        } => encoder
            .produce_picked_value_index_in_array(*value_index, *array_length)
            .unwrap(),
        | LlvmFdpCall::RemainingBytes { value } => encoder.produce_remaining_bytes(value).unwrap(),
        | LlvmFdpCall::RemainingBytesMark { value } => {
            encoder.mark_remaining_bytes(*value).unwrap()
        },
        | LlvmFdpCall::RemainingString { value } => {
            encoder.produce_remaining_bytes_as_string(value).unwrap()
        },
    }
}

unsafe fn consume_one(fdp: *mut c_void, call: &LlvmFdpCall) {
    match call {
        | LlvmFdpCall::Byte { value, range: None } => assert_eq!(consumeByte(fdp), *value),
        | LlvmFdpCall::Byte {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeByteInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::Char { value, range: None } => assert_eq!(consumeChar(fdp), *value),
        | LlvmFdpCall::Char {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeCharInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::Short { value, range: None } => assert_eq!(consumeShort(fdp), *value),
        | LlvmFdpCall::Short {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeShortInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::UShort { value, range: None } => {
            assert_eq!(consumeUnsignedShort(fdp), *value)
        },
        | LlvmFdpCall::UShort {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeUnsignedShortInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::Int { value, range: None } => assert_eq!(consumeInt(fdp), *value),
        | LlvmFdpCall::Int {
            value,
            range: Some(range),
        } => assert_eq!(consumeIntInRange(fdp, *range.start(), *range.end()), *value),
        | LlvmFdpCall::UInt { value, range: None } => assert_eq!(consumeUnsignedInt(fdp), *value),
        | LlvmFdpCall::UInt {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeUnsignedIntInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::LongLong { value, range: None } => assert_eq!(consumeLongLong(fdp), *value),
        | LlvmFdpCall::LongLong {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeLongLongInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::ULongLong { value, range: None } => {
            assert_eq!(consumeUnsignedLongLong(fdp), *value)
        },
        | LlvmFdpCall::ULongLong {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeUnsignedLongLongInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::Bool { value } => assert_eq!(consumeBool(fdp), *value),
        | LlvmFdpCall::Float { value, range: None } => assert_eq!(consumeFloat(fdp), *value),
        | LlvmFdpCall::Float {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeFloatInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::ProbFloat { value } => assert_eq!(consumeProbabilityFloat(fdp), *value),
        | LlvmFdpCall::Double { value, range: None } => assert_eq!(consumeDouble(fdp), *value),
        | LlvmFdpCall::Double {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeDoubleInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | LlvmFdpCall::ProbDouble { value } => assert_eq!(consumeProbabilityDouble(fdp), *value),
        | LlvmFdpCall::Enum { value, max_k } => assert_eq!(consumeEnum(fdp, *max_k), *value),
        | LlvmFdpCall::Bytes {
            value,
            terminator: None,
        } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeBytes(fdp, buf.as_mut_ptr(), value.len());
            assert_eq!(buf, *value);
        },
        | LlvmFdpCall::Bytes {
            value,
            terminator: Some(terminator),
        } => {
            let mut buf = vec![0; value.len()];
            let _read =
                consumeBytesWithTerminator(fdp, buf.as_mut_ptr(), value.len() - 1, *terminator);
            assert_eq!(buf, *value);
        },
        | LlvmFdpCall::String {
            value,
            requested_length: None,
        } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeBytesAsString(fdp, buf.as_mut_ptr(), value.len());
            assert_eq!(buf, *value);
        },
        | LlvmFdpCall::String {
            value,
            requested_length: Some(requested_length),
        } => {
            let mut buf = vec![0; *requested_length];
            let _read = consumeBytesAsString(fdp, buf.as_mut_ptr(), *requested_length);
            assert_eq!(buf[..value.len()], *value);
        },
        | LlvmFdpCall::RandomString {
            value,
            max_length: None,
        } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeRandomLengthString(fdp, buf.as_mut_ptr());
            assert_eq!(buf, *value);
        },
        | LlvmFdpCall::RandomString {
            value,
            max_length: Some(max_length),
        } => {
            let mut buf = vec![0; *max_length];
            let read = consumeRandomLengthStringWithMaxLength(fdp, buf.as_mut_ptr(), *max_length);
            assert_eq!(buf[..read], *value);
        },
        | LlvmFdpCall::ValuePick {
            value_index,
            array_length,
        } => assert_eq!(pickValueIndexInArray(fdp, *array_length), *value_index),
        | LlvmFdpCall::RemainingBytes { value } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeRemainingBytes(fdp, buf.as_mut_ptr());
            assert_eq!(buf, *value);
        },
        | LlvmFdpCall::RemainingString { value } => {
            let mut buf = vec![0; value.len()];
            let _read = consumeRemainingBytesAsString(fdp, buf.as_mut_ptr());
            assert_eq!(buf, *value);
        },
        | LlvmFdpCall::RemainingBytesMark { value: _ } => unreachable!(),
    }
}

fn test_consume(data: &[u8], call_list: &[LlvmFdpCall]) {
    unsafe {
        let fdp = init(data.as_ptr(), data.len());
        for call in call_list {
            consume_one(fdp, call);
        }
        deinit(fdp);
    }
}

fn permute_n(n: usize) {
    for case in repeat_n(0..18, n).multi_cartesian_product() {
        let mut encoder = LlvmFdpEncoder::new();

        let calls: Vec<_> = case.into_iter().map(|i| generate_one(Some(i))).collect();
        for call in &calls {
            produce_one(&mut encoder, call);
        }
        let output = encoder.finalize().unwrap();
        test_consume(&output, &calls);
    }
}

#[test]
fn permute_one() {
    permute_n(1);
}

#[test]
fn permute_two() {
    permute_n(2);
}

#[test]
fn permute_three() {
    permute_n(3);
}

#[test]
fn try_many() {
    let mut rng = rand::rng();
    for _ in 0..256 {
        let mut encoder = LlvmFdpEncoder::new();

        let depth = rng.random_range(0..512);
        let mut calls: Vec<_> = (0..depth).map(|_| generate_one(None)).collect();
        if rng.random() {
            calls.push(generate_one(Some(rng.random_range(18..20))));
        }
        for call in &calls {
            produce_one(&mut encoder, call);
        }
        let output = encoder.finalize().unwrap();
        test_consume(&output, &calls);
    }
}
