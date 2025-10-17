use std::{ffi::c_void, ops::RangeInclusive};

use fdp_reference::*;
use itertools::{repeat_n, Itertools};
use rand::prelude::*;
use simd_cesu8::mutf8;

use crate::encoder::jazzer::*;

fn generate_float(range: Option<RangeInclusive<f32>>) -> f32 {
    const F32_MIN_POSITIVE_SUBNORMAL: f32 = 1e-45;
    let mut rng = rand::rng();
    let range = match range {
        | Some(x) => x,
        | None => {
            let type_val: u8 = rng.random();
            match type_val {
                | 0 => return 0.0,
                | 1 => return -0.0,
                | 2 => return f32::INFINITY,
                | 3 => return f32::NEG_INFINITY,
                | 4 => return f32::NAN,
                | 5 => return F32_MIN_POSITIVE_SUBNORMAL,
                | 6 => return -F32_MIN_POSITIVE_SUBNORMAL,
                | 7 => return f32::MIN_POSITIVE,
                | 8 => return -f32::MIN_POSITIVE,
                | 9 => return -f32::MAX,
                | 10 => return f32::MIN,
                | _ => f32::MIN..=f32::MAX,
            }
        },
    };

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

fn generate_double(range: Option<RangeInclusive<f64>>) -> f64 {
    const F64_MIN_POSITIVE_SUBNORMAL: f64 = 5e-324;
    let mut rng = rand::rng();
    let range = match range {
        | Some(x) => x,
        | None => {
            let type_val: u8 = rng.random();
            match type_val {
                | 0 => return 0.0,
                | 1 => return -0.0,
                | 2 => return f64::INFINITY,
                | 3 => return f64::NEG_INFINITY,
                | 4 => return f64::NAN,
                | 5 => return F64_MIN_POSITIVE_SUBNORMAL,
                | 6 => return -F64_MIN_POSITIVE_SUBNORMAL,
                | 7 => return f64::MIN_POSITIVE,
                | 8 => return -f64::MIN_POSITIVE,
                | 9 => return -f64::MAX,
                | 10 => return f64::MIN,
                | _ => f64::MIN..=f64::MAX,
            }
        },
    };

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

fn generate_one(fixed_choice: Option<u32>) -> JazzerFdpCall {
    let mut rng = rand::rng();
    // Do not generate remaining* calls when choice is not intended to be fixed.
    let call_choice = fixed_choice.unwrap_or_else(|| rng.random_range(0..20));

    match call_choice {
        | 0 => {
            let value = rng.random();
            JazzerFdpCall::JBool { value }
        },
        | 1 => {
            let array_len = rng.random_range(0..1024);
            let values = (0..array_len).map(|_| rng.random()).collect();
            JazzerFdpCall::JBools { values }
        },
        | 2 => {
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if rng.random() {
                JazzerFdpCall::JByte {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                JazzerFdpCall::JByte {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 3 => {
            let array_len = rng.random_range(0..1024);
            let values = (0..array_len).map(|_| rng.random()).collect();
            JazzerFdpCall::JBytes { values }
        },
        | 4 => {
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if rng.random() {
                JazzerFdpCall::JChar {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                    no_surrogates: false,
                }
            } else {
                JazzerFdpCall::JChar {
                    value: randoms[1],
                    range: None,
                    no_surrogates: false,
                }
            }
        },
        | 5 => {
            let array_len = rng.random_range(0..1024);
            let values = (0..array_len).map(|_| rng.random()).collect();
            JazzerFdpCall::JChars { values }
        },
        | 6 => {
            if rng.random() {
                let mut randoms = [
                    generate_double(Some(f64::MIN..=f64::MAX)),
                    generate_double(Some(f64::MIN..=f64::MAX)),
                ];
                randoms.sort_by(|a, b| a.partial_cmp(b).unwrap());
                JazzerFdpCall::JDouble {
                    value: generate_double(Some(randoms[0]..=randoms[1])),
                    range: Some(randoms[0]..=randoms[1]),
                }
            } else {
                JazzerFdpCall::JDouble {
                    value: generate_double(None),
                    range: None,
                }
            }
        },
        | 7 => {
            if rng.random() {
                let mut randoms = [
                    generate_float(Some(f32::MIN..=f32::MAX)),
                    generate_float(Some(f32::MIN..=f32::MAX)),
                ];
                randoms.sort_by(|a, b| a.partial_cmp(b).unwrap());
                JazzerFdpCall::JFloat {
                    value: generate_float(Some(randoms[0]..=randoms[1])),
                    range: Some(randoms[0]..=randoms[1]),
                }
            } else {
                JazzerFdpCall::JFloat {
                    value: generate_float(None),
                    range: None,
                }
            }
        },
        | 8 => {
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if rng.random() {
                JazzerFdpCall::JInt {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                JazzerFdpCall::JInt {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 9 => {
            let array_len = rng.random_range(0..1024);
            let values = (0..array_len).map(|_| rng.random()).collect();
            JazzerFdpCall::JInts { values }
        },
        | 10 => {
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if rng.random() {
                JazzerFdpCall::JLong {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                JazzerFdpCall::JLong {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 11 => {
            let array_len = rng.random_range(0..1024);
            let values = (0..array_len).map(|_| rng.random()).collect();
            JazzerFdpCall::JLongs { values }
        },
        | 12 => {
            let mut randoms = [rng.random(), rng.random(), rng.random()];
            randoms.sort();
            if rng.random() {
                JazzerFdpCall::JShort {
                    value: randoms[1],
                    range: Some(randoms[0]..=randoms[2]),
                }
            } else {
                JazzerFdpCall::JShort {
                    value: randoms[1],
                    range: None,
                }
            }
        },
        | 13 => {
            let array_len = rng.random_range(0..1024);
            let values = (0..array_len).map(|_| rng.random()).collect();
            JazzerFdpCall::JShorts { values }
        },
        | 14 => {
            let random = generate_prob_double();
            JazzerFdpCall::ProbJDouble { value: random }
        },
        | 15 => {
            let random = generate_prob_float();
            JazzerFdpCall::ProbJFloat { value: random }
        },
        | 16 => {
            let array_length = rng.random_range(1..1048576);
            let value_index = rng.random_range(0..array_length);
            JazzerFdpCall::ValuePick {
                value_index,
                array_length,
            }
        },
        | 17 => {
            let mut randoms: [u64; 2] = [rng.random_range(0..1024), rng.random_range(0..1024)];
            randoms.sort();
            let array_length = randoms[1] as usize;
            let value_indexes = (0..array_length).choose_multiple(&mut rng, randoms[0] as usize);
            JazzerFdpCall::ValuePicks {
                value_indexes,
                array_length,
            }
        },
        | 18 => {
            let array_len = rng.random_range(0..1024);
            let mut input = vec![0; array_len];
            rng.fill_bytes(&mut input);

            let mut output = vec![0; array_len * 2];
            let mut utf8_length = [0];
            let byte_length = unsafe {
                fixJString(
                    input.as_ptr(),
                    array_len,
                    output.as_mut_ptr(),
                    array_len * 2,
                    utf8_length.as_mut_ptr(),
                    true,
                    true,
                )
            };

            let decoded = mutf8::decode_strict(&output[..byte_length]).unwrap();
            JazzerFdpCall::AsciiString {
                value: decoded.into_owned(),
                max_length: utf8_length[0],
            }
        },
        | 19 => {
            let array_len = rng.random_range(0..1024);
            let mut input = vec![0; array_len];
            rng.fill_bytes(&mut input);

            let mut output = vec![0; array_len * 6];
            let mut utf8_length = [0];
            let byte_length = unsafe {
                fixJString(
                    input.as_ptr(),
                    array_len,
                    output.as_mut_ptr(),
                    array_len * 6,
                    utf8_length.as_mut_ptr(),
                    false,
                    true,
                )
            };

            let decoded = mutf8::decode_strict(&output[..byte_length]).unwrap();
            JazzerFdpCall::JString {
                value: decoded.into_owned(),
                max_length: utf8_length[0],
            }
        },
        | 20 => {
            let array_len = rng.random_range(0..1024);
            let values = (0..array_len).map(|_| rng.random()).collect();
            JazzerFdpCall::RemainingJBytes { values }
        },
        | 21 => {
            // Remaining ascii string can't be length 1
            let array_len = rng.random_range(1..1024);
            let array_len = if array_len == 1 { 0 } else { array_len };
            let mut input = vec![0; array_len];
            rng.fill_bytes(&mut input);

            let mut output = vec![0; array_len * 2];
            let mut utf8_length = [0];
            let byte_length = unsafe {
                fixJString(
                    input.as_ptr(),
                    array_len,
                    output.as_mut_ptr(),
                    array_len * 2,
                    utf8_length.as_mut_ptr(),
                    true,
                    false,
                )
            };

            let decoded = mutf8::decode_strict(&output[..byte_length]).unwrap();
            JazzerFdpCall::RemainingAsciiString {
                value: decoded.into_owned(),
            }
        },
        | 22 => {
            let array_len = rng.random_range(0..1024);
            let mut input = vec![0; array_len];
            rng.fill_bytes(&mut input);

            let mut output = vec![0; array_len * 6];
            let mut utf8_length = [0];
            let byte_length = unsafe {
                fixJString(
                    input.as_ptr(),
                    array_len,
                    output.as_mut_ptr(),
                    array_len * 6,
                    utf8_length.as_mut_ptr(),
                    false,
                    false,
                )
            };

            let decoded = mutf8::decode_strict(&output[..byte_length]).unwrap();
            JazzerFdpCall::RemainingJString {
                value: decoded.into_owned(),
            }
        },
        | _ => unreachable!(),
    }
}

fn produce_one(encoder: &mut JazzerFdpEncoder, call: &JazzerFdpCall) {
    match call {
        | JazzerFdpCall::JByte { value, range: None } => encoder.produce_jbyte(*value).unwrap(),
        | JazzerFdpCall::JByte {
            value,
            range: Some(range),
        } => encoder
            .produce_jbyte_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | JazzerFdpCall::JChar {
            value,
            range: None,
            no_surrogates: _,
        } => encoder.produce_jchar(*value).unwrap(),
        | JazzerFdpCall::JChar {
            value,
            range: Some(range),
            no_surrogates: _,
        } => encoder
            .produce_jchar_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | JazzerFdpCall::JShort { value, range: None } => encoder.produce_jshort(*value).unwrap(),
        | JazzerFdpCall::JShort {
            value,
            range: Some(range),
        } => encoder
            .produce_jshort_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | JazzerFdpCall::JInt { value, range: None } => encoder.produce_jint(*value).unwrap(),
        | JazzerFdpCall::JInt {
            value,
            range: Some(range),
        } => encoder
            .produce_jint_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | JazzerFdpCall::JLong { value, range: None } => encoder.produce_jlong(*value).unwrap(),
        | JazzerFdpCall::JLong {
            value,
            range: Some(range),
        } => encoder
            .produce_jlong_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | JazzerFdpCall::JBool { value } => encoder.produce_jbool(*value).unwrap(),
        | JazzerFdpCall::JFloat { value, range: None } => encoder.produce_jfloat(*value).unwrap(),
        | JazzerFdpCall::JFloat {
            value,
            range: Some(range),
        } => encoder
            .produce_regular_jfloat_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | JazzerFdpCall::ProbJFloat { value } => {
            encoder.produce_probability_jfloat(*value).unwrap()
        },
        | JazzerFdpCall::JDouble { value, range: None } => encoder.produce_jdouble(*value).unwrap(),
        | JazzerFdpCall::JDouble {
            value,
            range: Some(range),
        } => encoder
            .produce_regular_jdouble_in_range(*value, *range.start(), *range.end())
            .unwrap(),
        | JazzerFdpCall::ProbJDouble { value } => {
            encoder.produce_probability_jdouble(*value).unwrap()
        },
        | JazzerFdpCall::JBytes { values } => {
            encoder.produce_jbytes(values, values.len() as i32).unwrap()
        },
        | JazzerFdpCall::JChars { values } => {
            encoder.produce_jchars(values, values.len() as i32).unwrap()
        },
        | JazzerFdpCall::JShorts { values } => encoder
            .produce_jshorts(values, values.len() as i32)
            .unwrap(),
        | JazzerFdpCall::JInts { values } => {
            encoder.produce_jints(values, values.len() as i32).unwrap()
        },
        | JazzerFdpCall::JLongs { values } => {
            encoder.produce_jlongs(values, values.len() as i32).unwrap()
        },
        | JazzerFdpCall::JBools { values } => {
            encoder.produce_jbools(values, values.len() as i32).unwrap()
        },
        | JazzerFdpCall::ValuePick {
            value_index,
            array_length,
        } => encoder
            .produce_picked_value_index_in_jarray(*value_index, *array_length)
            .unwrap(),
        | JazzerFdpCall::ValuePicks {
            value_indexes,
            array_length,
        } => encoder
            .produce_picked_value_indexes_in_jarray(value_indexes, *array_length)
            .unwrap(),
        | JazzerFdpCall::RemainingJBytes { values } => {
            encoder.produce_remaining_as_jbytes(values).unwrap()
        },
        | JazzerFdpCall::RemainingBytesMark { value } => {
            encoder.mark_remaining_bytes(*value).unwrap()
        },
        | JazzerFdpCall::AsciiString { value, max_length } => encoder
            .produce_ascii_string(value, *max_length as i32)
            .unwrap(),
        | JazzerFdpCall::JString { value, max_length } => {
            encoder.produce_jstring(value, *max_length as i32).unwrap()
        },
        | JazzerFdpCall::RemainingAsciiString { value } => {
            encoder.produce_remaining_as_ascii_string(value).unwrap()
        },
        | JazzerFdpCall::RemainingJString { value } => {
            encoder.produce_remaining_as_jstring(value).unwrap()
        },
    }
}

unsafe fn consume_one(fdp: *mut c_void, call: &JazzerFdpCall) {
    match call {
        | JazzerFdpCall::JByte { value, range: None } => assert_eq!(consumeJByte(fdp), *value),
        | JazzerFdpCall::JByte {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeJByteInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | JazzerFdpCall::JChar {
            value,
            range: None,
            no_surrogates: _,
        } => assert_eq!(consumeJChar(fdp), *value),
        | JazzerFdpCall::JChar {
            value,
            range: Some(range),
            no_surrogates: _,
        } => assert_eq!(
            consumeJCharInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | JazzerFdpCall::JInt { value, range: None } => assert_eq!(consumeJInt(fdp), *value),
        | JazzerFdpCall::JInt {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeJIntInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | JazzerFdpCall::JLong { value, range: None } => assert_eq!(consumeJLong(fdp), *value),
        | JazzerFdpCall::JLong {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeJLongInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | JazzerFdpCall::JShort { value, range: None } => assert_eq!(consumeJShort(fdp), *value),
        | JazzerFdpCall::JShort {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeJShortInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | JazzerFdpCall::JBool { value } => assert_eq!(consumeJBoolean(fdp) != 0, *value),
        | JazzerFdpCall::JDouble { value, range: None } => {
            let out = consumeJDouble(fdp);
            if out.is_nan() {
                assert!(value.is_nan())
            } else {
                assert_eq!(out, *value)
            }
        },
        | JazzerFdpCall::JDouble {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeRegularJDoubleInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | JazzerFdpCall::ProbJDouble { value } => {
            assert_eq!(consumeProbabilityJDouble(fdp), *value)
        },
        | JazzerFdpCall::JFloat { value, range: None } => {
            let out = consumeJFloat(fdp);
            if out.is_nan() {
                assert!(value.is_nan())
            } else {
                assert_eq!(out, *value)
            }
        },
        | JazzerFdpCall::JFloat {
            value,
            range: Some(range),
        } => assert_eq!(
            consumeRegularJFloatInRange(fdp, *range.start(), *range.end()),
            *value
        ),
        | JazzerFdpCall::ProbJFloat { value } => assert_eq!(consumeProbabilityJFloat(fdp), *value),
        | JazzerFdpCall::JBools { values } => {
            let mut buf = vec![0; values.len()];
            consumeJBooleans(fdp, buf.as_mut_ptr(), buf.len());
            assert_eq!(*values, buf.iter().map(|x| *x != 0).collect::<Vec<_>>())
        },
        | JazzerFdpCall::JBytes { values } => {
            let mut buf = vec![0; values.len()];
            consumeJBytes(fdp, buf.as_mut_ptr(), buf.len());
            assert_eq!(*values, buf)
        },
        | JazzerFdpCall::JChars { values } => {
            let mut buf = vec![0; values.len()];
            consumeJChars(fdp, buf.as_mut_ptr(), buf.len());
            assert_eq!(*values, buf)
        },
        | JazzerFdpCall::JInts { values } => {
            let mut buf = vec![0; values.len()];
            consumeJInts(fdp, buf.as_mut_ptr(), buf.len());
            assert_eq!(*values, buf)
        },
        | JazzerFdpCall::JLongs { values } => {
            let mut buf = vec![0; values.len()];
            consumeJLongs(fdp, buf.as_mut_ptr(), buf.len());
            assert_eq!(*values, buf)
        },
        | JazzerFdpCall::JShorts { values } => {
            let mut buf = vec![0; values.len()];
            consumeJShorts(fdp, buf.as_mut_ptr(), buf.len());
            assert_eq!(*values, buf)
        },
        | JazzerFdpCall::ValuePick {
            value_index,
            array_length,
        } => assert_eq!(pickValueIndexInJArray(fdp, *array_length), *value_index),
        | JazzerFdpCall::ValuePicks {
            value_indexes,
            array_length,
        } => {
            let mut buf = vec![0; value_indexes.len()];
            pickValueIndexesInJArray(fdp, buf.as_mut_ptr(), buf.len(), *array_length);
            assert_eq!(*value_indexes, buf)
        },
        | JazzerFdpCall::AsciiString { value, max_length } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let out_len = consumeAsciiString(fdp, buf.as_mut_ptr(), *max_length);
            assert_eq!(out_len, encoded.len());
            assert_eq!(*encoded, buf);
        },
        | JazzerFdpCall::JString { value, max_length } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let out_len = consumeJString(fdp, buf.as_mut_ptr(), *max_length);
            assert_eq!(out_len, encoded.len());
            assert_eq!(*encoded, buf);
        },
        | JazzerFdpCall::RemainingJBytes { values } => {
            let mut buf = vec![0; values.len()];
            consumeRemainingAsJBytes(fdp, buf.as_mut_ptr());
            assert_eq!(*values, buf)
        },
        | JazzerFdpCall::RemainingAsciiString { value } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let out_len = consumeRemainingAsAsciiString(fdp, buf.as_mut_ptr());
            assert_eq!(out_len, encoded.len());
            assert_eq!(*encoded, buf);
        },
        | JazzerFdpCall::RemainingJString { value } => {
            let encoded = mutf8::encode(value);
            let mut buf = vec![0; encoded.len()];
            let out_len = consumeRemainingAsJString(fdp, buf.as_mut_ptr());
            assert_eq!(out_len, encoded.len());
            assert_eq!(*encoded, buf);
        },
        | JazzerFdpCall::RemainingBytesMark { value: _ } => unreachable!(),
    }
}

fn test_consume(data: &[u8], call_list: &[JazzerFdpCall]) {
    unsafe {
        let fdp = init(data.as_ptr(), data.len());
        for call in call_list {
            consume_one(fdp, call);
        }
        deinit(fdp);
    }
}

fn permute_n(n: usize) {
    for case in repeat_n(0..20, n).multi_cartesian_product() {
        let mut encoder = JazzerFdpEncoder::new();

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
        let mut encoder = JazzerFdpEncoder::new();

        let depth = rng.random_range(0..128);
        let mut calls: Vec<_> = (0..depth).map(|_| generate_one(None)).collect();
        if rng.random() {
            calls.push(generate_one(Some(rng.random_range(20..23))));
        }
        for call in &calls {
            produce_one(&mut encoder, call);
        }
        let output = encoder.finalize().unwrap();
        test_consume(&output, &calls);
    }
}
