use std::{cmp::min, mem, ops::RangeInclusive, vec};

use byteorder::{ByteOrder, LittleEndian};
use bytes::{BufMut, Bytes, BytesMut};
use thiserror::Error;

#[cfg(feature = "debug")]
mod debug;
pub mod jazzer;
pub mod llvm;
#[cfg(test)]
mod tests;

type EncoderResult = Result<(), EncoderError>;
type EncoderCallResult = Result<FdpStagedCall, EncoderError>;
type EncoderCallsResult = Result<Vec<FdpStagedCall>, EncoderError>;
type LengthAdjustment = fn(Bytes, usize) -> Bytes;

#[derive(Debug, Error)]
pub enum EncoderError {
    #[error("Data should at least has size of: {0}")]
    InputTooShort(usize),
    #[error("Data should at most has size of: {0}")]
    InputTooLong(usize),
    #[error("Range argument trying to make reversed range: {0}..={1}")]
    InvalidRangeInput(String, String),
    #[error("Data has the following invalid input: {0}")]
    InvalidInput(String),
    #[error("Data already have reached end of data, so cannot process: {0}")]
    AlreadyReachedEndOfData(String),
    #[error("Input value {0} not in range: {1}..={2}")]
    ValueNotInRange(String, String, String),
    #[error("Input data was determined to {0} before, but now requesting it to be: {1}")]
    TargetInputSizeUnmatched(usize, usize),
    #[error("Cannot fit data to target input size {0}. Please check all FDP calls again.")]
    TargetSizeUnsat(usize),
    #[error("Cannot fit data to have extra bytes {0} after this call.")]
    ExtraBytesUnsat(usize),
    #[cfg(feature = "debug")]
    #[error("Mismatch on call {0}.")]
    OutputMismatch(String),
}

pub struct FdpCallScan {
    finish_marked: Option<usize>,
    commit_allowed_upto: Option<usize>,
    calls_to_mark_final: Vec<usize>,
}

// TODO: Do something with this
#[allow(unused)]
#[derive(Clone, Debug)]
pub struct FdpCallScope {
    method_name: String,
    formatted_method_arguments: Vec<String>,
}

fn adjust_with_zero(bytes: Bytes, size: usize) -> Bytes {
    if size == bytes.len() {
        return bytes;
    }
    let mut bytes = BytesMut::from(bytes);
    bytes.resize(bytes.len() + size, 0);
    bytes.freeze()
}

struct LengthVariance {
    range: RangeInclusive<isize>,
    adjustment_method: LengthAdjustment,
}

impl LengthVariance {
    fn adjust_at_best(&self, bytes: Bytes, target_adjustment: isize) -> (isize, Bytes) {
        let adjustment = if self.range.contains(&target_adjustment) {
            target_adjustment
        } else {
            // if target in range: adjust
            // else: keep when extend, reduce when shrink
            *self.range.start()
        };

        let original_len = bytes.len();
        let target_len = (original_len as isize) - adjustment;
        let target_len = if target_len < 0 {
            0
        } else {
            target_len as usize
        };
        let adjusted = (self.adjustment_method)(bytes, target_len);

        let actual_adjustment = adjusted.len() as isize - original_len as isize;
        (actual_adjustment, adjusted)
    }
}

struct FdpStagedCall {
    id: usize,
    variance: Option<LengthVariance>,
    variance_on_finalization: Option<LengthVariance>,
    extra_bytes_required: usize,
    candidate: Bytes,
    user_call: Option<FdpCallScope>,
    finish_mark: bool,
    reversed: bool,
}

impl FdpStagedCall {
    fn get_min_length(&self) -> usize {
        let min_size = self.candidate.len() as isize
            + match &self.variance_on_finalization {
                | Some(length_variance) => *length_variance.range.start(),
                | None => 0,
            }
            + match &self.variance {
                | Some(length_variance) => *length_variance.range.start(),
                | None => 0,
            };

        min_size as usize
    }

    // Adjust safe only, this action is irreversible.
    fn adjust_safe(&mut self, target_adjustment: isize) -> (isize, usize) {
        let mut candidate = mem::take(&mut self.candidate);
        let mut acc_adjustment = 0;

        if let Some(variance) = &mut self.variance {
            let (actual_adjustment, adjusted) =
                variance.adjust_at_best(candidate, target_adjustment);
            candidate = adjusted;
            acc_adjustment += actual_adjustment;
        }

        let extra_bytes_required = self.extra_bytes_required as isize;
        if extra_bytes_required < acc_adjustment {
            self.extra_bytes_required = 0;
        } else {
            self.extra_bytes_required = (extra_bytes_required - acc_adjustment) as usize;
        }

        self.variance = None;
        self.candidate = candidate;
        (acc_adjustment, self.candidate.len())
    }

    // Adjust as much as you can, this action is irreversible.
    fn adjust_at_best(&mut self, mut target_adjustment: isize) -> (isize, usize) {
        let mut candidate = mem::take(&mut self.candidate);
        let mut acc_adjustment = 0;

        if let Some(variance) = &mut self.variance {
            let (actual_adjustment, adjusted) =
                variance.adjust_at_best(candidate, target_adjustment);
            candidate = adjusted;
            acc_adjustment += actual_adjustment;
            target_adjustment -= actual_adjustment;
        }

        if let Some(variance) = &mut self.variance_on_finalization {
            let (actual_adjustment, adjusted) =
                variance.adjust_at_best(candidate, target_adjustment);
            candidate = adjusted;
            acc_adjustment += actual_adjustment;
            if actual_adjustment != 0 {
                self.finish_mark = true;
            }
        }

        let extra_bytes_required = self.extra_bytes_required as isize;
        if extra_bytes_required < acc_adjustment {
            self.extra_bytes_required = 0;
        } else {
            self.extra_bytes_required = (extra_bytes_required - acc_adjustment) as usize;
        }
        self.variance = None;
        self.variance_on_finalization = None;
        self.candidate = candidate;
        (acc_adjustment, self.candidate.len())
    }
}

pub struct FdpEncoder {
    staged: Vec<FdpStagedCall>,
    committed: BytesMut,
    backcommitted: BytesMut,
    #[cfg(feature = "debug")]
    commit_log: Vec<FdpCallScope>,
    current_scope: Option<FdpCallScope>,
    target_size: Option<usize>,
    commission_freezed: bool,
    produced_size: usize,
    next_call_id: usize,
}

fn check_terminator(data: &[u8], terminator: u8) -> EncoderResult {
    if data.is_empty() {
        return Err(EncoderError::InputTooShort(1));
    } else if *data.last().unwrap() != terminator {
        return Err(EncoderError::InvalidInput(
            "data doesn't end with terminator".to_owned(),
        ));
    }
    Ok(())
}

fn prepare_raw_string_to_bytes(data: &[u8], length: usize) -> Result<Bytes, EncoderError> {
    if data.len() > length {
        return Err(EncoderError::InputTooLong(length));
    }

    let mut buffer = BytesMut::with_capacity(length);
    buffer.extend_from_slice(data);
    buffer.extend_from_slice(&vec![0; length - data.len()]);
    let buffer = buffer.freeze();
    Ok(buffer)
}

fn produce_probability_double_target(value: f64) -> Result<u64, EncoderError> {
    if !(0.0..=1.0).contains(&value) {
        return Err(EncoderError::ValueNotInRange(
            value.to_string(),
            0.0.to_string(),
            1.0.to_string(),
        ));
    }
    let max = u64::MAX as f64;
    Ok((max * value) as u64)
}

fn produce_probability_float_target(value: f32) -> Result<u32, EncoderError> {
    if !(0.0..=1.0).contains(&value) {
        return Err(EncoderError::ValueNotInRange(
            value.to_string(),
            0.0.to_string(),
            1.0.to_string(),
        ));
    }
    let max = u32::MAX as f32;
    Ok((max * value) as u32)
}

fn check_array(array_length: usize) -> EncoderResult {
    if array_length == 0 {
        Err(EncoderError::InputTooShort(array_length))
    } else {
        Ok(())
    }
}

impl FdpEncoder {
    pub fn new() -> Self {
        FdpEncoder {
            staged: Vec::new(),
            committed: BytesMut::new(),
            backcommitted: BytesMut::new(),
            #[cfg(feature = "debug")]
            commit_log: Vec::new(),
            current_scope: None,
            target_size: None,
            commission_freezed: false,
            produced_size: 0,
            next_call_id: 0,
        }
    }

    fn get_call_id(&mut self) -> usize {
        let call_id = self.next_call_id;
        self.next_call_id += 1;
        call_id
    }

    // This is irreversible. Should be called with care.
    fn try_fit(&mut self, requirement: isize) -> EncoderResult {
        if requirement == 0 {
            return Ok(());
        }
        let Some(target_size) = self.target_size else {
            return Err(EncoderError::InvalidInput(
                "Requiring size adjustments without explictly marked remaining bytes".to_owned(),
            ));
        };

        // All calls after final marked should contain min range and should be 0
        // Only safe variables and first final marked call can be variable

        let mut acc_adjustments = 0;
        for call in self.staged.iter_mut() {
            let target_adjustment = requirement - acc_adjustments;
            let (actual_adjustment, _adjusted_size) = call.adjust_safe(target_adjustment);
            acc_adjustments += actual_adjustment;
            self.produced_size = ((self.produced_size as isize) + actual_adjustment) as usize;
            if call.finish_mark {
                break;
            }
        }

        let mut acc_bytes = 0;
        let mut adjustments_include_non_zero_length = false;
        for call in self.staged.iter_mut().rev() {
            if call.extra_bytes_required > acc_bytes {
                return Err(EncoderError::ExtraBytesUnsat(call.extra_bytes_required));
            }
            let target_adjustment = requirement - acc_adjustments;

            if adjustments_include_non_zero_length && call.finish_mark {
                // Adjusted with non zero candidate but already marked finished
                return Err(EncoderError::TargetSizeUnsat(target_size));
            } else if acc_adjustments == requirement {
                acc_bytes += call.candidate.len();
                continue;
            } else if adjustments_include_non_zero_length && target_adjustment != 0 {
                // Adjusted with non zero candidate but needs extra adjustments
                return Err(EncoderError::TargetSizeUnsat(target_size));
            } else if adjustments_include_non_zero_length || target_adjustment == 0 {
                acc_bytes += call.candidate.len();
                continue;
            }

            let (actual_adjustment, adjusted_size) = call.adjust_at_best(target_adjustment);
            acc_bytes += adjusted_size;
            acc_adjustments += actual_adjustment;
            self.produced_size = ((self.produced_size as isize) + actual_adjustment) as usize;
            adjustments_include_non_zero_length =
                adjustments_include_non_zero_length || adjusted_size != 0;
        }

        if acc_adjustments == requirement || requirement > 0 {
            Ok(())
        } else {
            Err(EncoderError::TargetSizeUnsat(target_size))
        }
    }

    fn stage(&mut self, call: FdpStagedCall) {
        self.produced_size += call.candidate.len();
        self.staged.push(call);
    }

    fn scan_staged_calls(&mut self) -> Result<FdpCallScan, EncoderError> {
        let mut calls_to_mark_final = Vec::new();
        let mut first_finish_marked = None;
        let mut extra_bytes_required: usize = 0;
        let mut extra_bytes_required_by = None;
        let mut first_blocker = None;
        let mut last_invariant = None;

        for call in &self.staged {
            let extension_blocked = first_finish_marked.is_some() || self.commission_freezed;
            if extension_blocked && call.get_min_length() > 0 {
                return Err(EncoderError::AlreadyReachedEndOfData(format!(
                    "{:?}",
                    call.user_call
                )));
            } else if extension_blocked && !call.candidate.is_empty() {
                calls_to_mark_final.push(call.id);
            }

            let finish_marked = if call.finish_mark {
                Some(call.id)
            } else {
                None
            };

            extra_bytes_required = extra_bytes_required.saturating_sub(call.candidate.len());

            if call.extra_bytes_required > extra_bytes_required {
                extra_bytes_required_by = Some(call.id);
                extra_bytes_required = call.extra_bytes_required;
            }

            let safe_adjustable = call.variance.as_ref().map(|_| call.id);
            let invariant = match call
                .variance_on_finalization
                .as_ref()
                .or(call.variance.as_ref())
            {
                | Some(_) => None,
                | None => Some(call.id),
            };

            first_finish_marked = first_finish_marked.or(finish_marked);
            first_blocker = first_blocker.or(safe_adjustable);
            last_invariant = invariant.or(last_invariant);
        }
        let blocker = if extra_bytes_required > 0 {
            if let Some(first_blocker) = first_blocker {
                Some(min(first_blocker, extra_bytes_required_by.unwrap()))
            } else {
                extra_bytes_required_by
            }
        } else {
            first_blocker
        };

        let commit_upto = match (blocker, last_invariant) {
            | (None, None) => None,
            | (Some(_), None) => None,
            | (Some(0), Some(_)) => None,
            | (None, Some(x)) => Some(x),
            | (Some(x), Some(_)) => Some(x - 1),
        };
        Ok(FdpCallScan {
            finish_marked: first_finish_marked,
            commit_allowed_upto: commit_upto,
            calls_to_mark_final,
        })
    }

    fn flush(&mut self) -> EncoderResult {
        let FdpCallScan {
            commit_allowed_upto,
            calls_to_mark_final,
            finish_marked,
        } = self.scan_staged_calls()?;

        let Some(commit_upto) = commit_allowed_upto else {
            return Ok(());
        };

        let keep_staged_from_idx = match self
            .staged
            .binary_search_by_key(&(commit_upto + 1), |x| x.id)
        {
            | Ok(pos) | Err(pos) => pos,
        };

        let mut to_extend = BytesMut::new();
        let mut to_backextend = BytesMut::new();
        let mut calls_iter_to_mark_final = calls_to_mark_final.iter().peekable();
        for call in &mut self.staged.iter().filter(|x| x.id <= commit_upto) {
            if let Some(skip_id) = calls_iter_to_mark_final.peek() {
                if **skip_id == call.id {
                    calls_iter_to_mark_final.next();
                    continue;
                }
            }

            if call.reversed {
                to_backextend.extend(call.candidate.iter().rev());
            } else {
                to_extend.extend_from_slice(&call.candidate);
            }
        }

        let to_extend = to_extend.freeze();
        let to_backextend = to_backextend.freeze();
        let expected_size =
            self.committed.len() + self.backcommitted.len() + to_extend.len() + to_backextend.len();
        if let Some(target_size) = self.target_size {
            if target_size < expected_size {
                return Err(EncoderError::TargetInputSizeUnmatched(
                    target_size,
                    expected_size,
                ));
            }
        }

        let mut calls_iter_to_mark_final = calls_to_mark_final.iter().peekable();
        for call in self.staged.iter_mut() {
            if let Some(target_id) = calls_iter_to_mark_final.peek() {
                if **target_id == call.id {
                    // This should succeed due to the check before the index was inserted.
                    let (adjustment, _adjusted_size) =
                        call.adjust_at_best(-(call.candidate.len() as isize));
                    self.produced_size -= adjustment as usize;
                    calls_iter_to_mark_final.next();
                    continue;
                }
            }
        }

        let new_staged = self.staged.drain(keep_staged_from_idx..).collect();
        let _ = mem::replace(&mut self.staged, new_staged);
        self.committed.extend(to_extend);
        self.backcommitted.extend(to_backextend);
        let need_to_freeze = finish_marked.is_some_and(|x| x <= commit_upto);
        self.commission_freezed = self.commission_freezed || need_to_freeze;

        Ok(())
    }

    fn flush_check_extra_bytes_only(&mut self) -> usize {
        if self.staged.is_empty() {
            return 0;
        }

        let mut acc_bytes = 0;
        let mut stop_idx = None;
        let mut needs = 0;
        for (idx, call) in self.staged.iter().enumerate().rev() {
            if call.extra_bytes_required > acc_bytes {
                stop_idx = Some(idx);
                let needs_here = call.extra_bytes_required - acc_bytes;
                if needs < needs_here {
                    needs = needs_here;
                }
            }
            acc_bytes += call.candidate.len()
        }
        let to_keep = match stop_idx {
            | Some(idx) => self.staged.drain(idx..).collect(),
            | None => Vec::new(),
        };

        let to_commit = mem::replace(&mut self.staged, to_keep);
        for call in to_commit.into_iter() {
            if call.reversed {
                self.backcommitted.extend(call.candidate.iter().rev());
            } else {
                self.committed.extend_from_slice(&call.candidate);
            }
        }

        needs
    }

    fn flush_unchecked(&mut self) {
        if self.staged.is_empty() {
            return;
        }
        let staged = mem::take(&mut self.staged);
        for call in staged.into_iter() {
            if call.reversed {
                self.backcommitted.extend(call.candidate.iter().rev());
            } else {
                self.committed.extend_from_slice(&call.candidate);
            }
        }
    }

    fn revoke(&mut self, down_to: usize) -> EncoderResult {
        let staged_revoke_pos = match self.staged.binary_search_by_key(&down_to, |x| x.id) {
            | Ok(pos) | Err(pos) => pos,
        };

        let revoked_size = if !self.staged.is_empty() && staged_revoke_pos < self.staged.len() {
            let revoked_size = self.staged[staged_revoke_pos..]
                .iter()
                .fold(0, |acc, x| acc + x.candidate.len());
            revoked_size
        } else {
            0
        };
        self.staged.truncate(staged_revoke_pos);
        self.produced_size -= revoked_size;
        self.next_call_id = down_to;
        Ok(())
    }

    fn stage_and_flush_calls_unchecked(&mut self, calls: Vec<FdpStagedCall>) {
        for call in calls {
            self.stage(call);
        }
        self.flush_unchecked();
    }

    fn stage_and_flush_calls(&mut self, calls: Vec<FdpStagedCall>) -> EncoderResult {
        if calls.is_empty() {
            return Ok(());
        }
        let revoke_down_to = calls.first().unwrap().id;

        for call in calls {
            self.stage(call);
        }
        if let Err(e) = self.flush() {
            self.revoke(revoke_down_to)?;
            Err(e)
        } else {
            Ok(())
        }
    }

    fn stage_and_flush(&mut self, call: FdpStagedCall) -> EncoderResult {
        let revoke_down_to = call.id;
        self.stage(call);
        if let Err(e) = self.flush() {
            self.revoke(revoke_down_to)?;
            Err(e)
        } else {
            Ok(())
        }
    }

    fn stage_and_flush_unchecked(&mut self, call: FdpStagedCall) {
        self.stage(call);
        self.flush_unchecked();
    }

    pub fn produce_bytes_unchecked(&mut self, data: &[u8]) {
        let call_id = self.get_call_id();
        self.stage_and_flush_unchecked(FdpStagedCall {
            id: call_id,
            variance: None,
            variance_on_finalization: None,
            extra_bytes_required: 0,
            candidate: Bytes::copy_from_slice(data),
            user_call: self.current_scope.clone(),
            finish_mark: false,
            reversed: false,
        });
    }

    pub fn produce_bytes(&mut self, data: &[u8], num_bytes: usize) -> EncoderResult {
        if data.len() > num_bytes {
            return Err(EncoderError::InputTooLong(num_bytes));
        }

        let call_id = self.get_call_id();
        self.stage_and_flush(FdpStagedCall {
            id: call_id,
            variance: None,
            variance_on_finalization: None,
            extra_bytes_required: 0,
            candidate: Bytes::copy_from_slice(data),
            user_call: self.current_scope.clone(),
            finish_mark: num_bytes > data.len(),
            reversed: false,
        })?;

        Ok(())
    }

    pub fn produce_remaining_bytes_unchecked(&mut self, data: &[u8]) {
        let call_id = self.get_call_id();
        self.stage_and_flush_unchecked(FdpStagedCall {
            id: call_id,
            variance: None,
            variance_on_finalization: None,
            extra_bytes_required: 0,
            candidate: Bytes::copy_from_slice(data),
            user_call: self.current_scope.clone(),
            finish_mark: true,
            reversed: false,
        });
    }

    pub fn produce_remaining_bytes(&mut self, data: &[u8]) -> EncoderResult {
        let call_id = self.get_call_id();
        self.stage_and_flush(FdpStagedCall {
            id: call_id,
            variance: None,
            variance_on_finalization: None,
            extra_bytes_required: 0,
            candidate: Bytes::copy_from_slice(data),
            user_call: self.current_scope.clone(),
            finish_mark: true,
            reversed: false,
        })?;

        Ok(())
    }

    // Input data must contain terminator
    pub fn produce_bytes_with_terminator_unchecked(
        &mut self,
        data: &[u8],
        terminator: u8,
    ) -> EncoderResult {
        check_terminator(data, terminator)?;
        self.produce_bytes_unchecked(&data[..data.len() - 1]);
        Ok(())
    }

    pub fn produce_bytes_with_terminator(
        &mut self,
        data: &[u8],
        num_bytes: usize,
        terminator: u8,
    ) -> EncoderResult {
        check_terminator(data, terminator)?;
        self.produce_bytes(&data[..data.len() - 1], num_bytes)
    }

    pub fn produce_string_unchecked(&mut self, data: &[u8], length: usize) -> EncoderResult {
        let buffer = prepare_raw_string_to_bytes(data, length)?;
        self.produce_bytes_unchecked(&buffer);
        Ok(())
    }

    pub fn produce_string(&mut self, data: &[u8], length: usize) -> EncoderResult {
        let buffer = prepare_raw_string_to_bytes(data, length)?;
        self.produce_bytes(&buffer, length)
    }

    // This is not actually random.
    fn produce_random_string_call(
        &mut self,
        data: &[u8],
        max_length: Option<usize>,
    ) -> EncoderCallResult {
        let mut converted = BytesMut::with_capacity(data.len());
        for byte in data {
            if *byte == 0x5C {
                converted.put_u16(0x5C5C);
            } else {
                converted.put_u8(*byte);
            }
        }

        let length_variance = match max_length {
            | Some(max_length) if data.len() < max_length => {
                converted.put_u16(0x5C00);
                Some(LengthVariance {
                    range: -2..=0,
                    adjustment_method: adjust_with_zero,
                })
            },
            | None => {
                converted.put_u16(0x5C00);
                Some(LengthVariance {
                    range: -2..=0,
                    adjustment_method: adjust_with_zero,
                })
            },
            | Some(max_length) if data.len() > max_length => {
                return Err(EncoderError::InputTooLong(max_length));
            },
            | _ => None,
        };

        let call = FdpStagedCall {
            id: self.get_call_id(),
            variance: None,
            variance_on_finalization: length_variance,
            extra_bytes_required: 0,
            candidate: converted.freeze(),
            user_call: self.current_scope.clone(),
            finish_mark: false,
            reversed: false,
        };

        Ok(call)
    }

    // This is not actually random.
    pub fn produce_random_string_unchecked(
        &mut self,
        data: &[u8],
        max_length: Option<usize>,
    ) -> EncoderResult {
        let call = self.produce_random_string_call(data, max_length)?;
        self.stage_and_flush_unchecked(call);
        Ok(())
    }

    // This is not actually random.
    pub fn produce_random_string(
        &mut self,
        data: &[u8],
        max_length: Option<usize>,
    ) -> EncoderResult {
        let call = self.produce_random_string_call(data, max_length)?;
        self.stage_and_flush(call)
    }

    fn produce_integral_in_range_call(
        &mut self,
        value: i128,
        range: RangeInclusive<i128>,
    ) -> EncoderCallResult {
        if !range.contains(&value) {
            return Err(EncoderError::ValueNotInRange(
                value.to_string(),
                range.start().to_string(),
                range.end().to_string(),
            ));
        }
        let range_width = range.end() - range.start();
        let target_output = (value - range.start()) as u128;
        let max_bit_pos = range_width.checked_ilog2();
        let minimum_bytes_required = target_output
            .checked_ilog2()
            .map(|x| 1 + (x / 8))
            .unwrap_or(0) as usize;

        Ok(match max_bit_pos {
            | Some(max_bit_pos) => {
                let bytes_len = ((max_bit_pos / 8) + 1) as usize;
                let mut buffer = BytesMut::zeroed(bytes_len);
                LittleEndian::write_uint128(&mut buffer, target_output, bytes_len);
                let length_variance = if minimum_bytes_required == bytes_len {
                    None
                } else {
                    let range_min = minimum_bytes_required as isize - bytes_len as isize;
                    Some(LengthVariance {
                        range: range_min..=0,
                        adjustment_method: adjust_with_zero,
                    })
                };
                FdpStagedCall {
                    id: self.get_call_id(),
                    candidate: buffer.freeze(),
                    variance: None,
                    variance_on_finalization: length_variance,
                    extra_bytes_required: 0,
                    user_call: self.current_scope.clone(),
                    finish_mark: false,
                    reversed: true,
                }
            },
            | None => {
                let buffer = Bytes::new();
                FdpStagedCall {
                    id: self.get_call_id(),
                    candidate: buffer,
                    variance: None,
                    variance_on_finalization: None,
                    extra_bytes_required: 0,
                    user_call: self.current_scope.clone(),
                    finish_mark: false,
                    reversed: true,
                }
            },
        })
    }

    pub fn produce_integral_in_range_unchecked(
        &mut self,
        value: i128,
        range: RangeInclusive<i128>,
    ) -> EncoderResult {
        let call = self.produce_integral_in_range_call(value, range)?;
        self.stage_and_flush_unchecked(call);
        Ok(())
    }

    pub fn produce_integral_in_range(
        &mut self,
        value: i128,
        range: RangeInclusive<i128>,
    ) -> EncoderResult {
        let call = self.produce_integral_in_range_call(value, range)?;
        self.stage_and_flush(call)
    }

    fn produce_double_in_range_call(
        &mut self,
        value: f64,
        range: RangeInclusive<f64>,
    ) -> EncoderCallsResult {
        if !range.contains(&value) {
            return Err(EncoderError::ValueNotInRange(
                value.to_string(),
                range.start().to_string(),
                range.end().to_string(),
            ));
        }
        let mut calls = Vec::new();
        let zero = 0.0f64;
        let min = *range.start();
        let max = *range.end();

        let (range_width, result_base) = if max > zero && min < zero && max > min + f64::MAX {
            let range = (max / 2.0) - (min / 2.0);

            // Note: Ambiguous when min + range == value
            let target_bool = value > range + min;
            calls.push(self.produce_bool_call(target_bool)?);
            if target_bool {
                (range, min + range)
            } else {
                (range, min)
            }
        } else {
            (max - min, min)
        };

        let mut bit_now: u64 = 1 << (u64::BITS - 1);
        let mut now = 0;
        let int_max = u64::MAX as f64;
        while bit_now > 0 {
            let trial_consume = bit_now + now;
            let prob = (trial_consume as f64) / int_max;
            let trial_value = result_base + range_width * prob;
            if value >= trial_value {
                now = trial_consume;
            }
            if value == trial_value {
                break;
            }
            bit_now >>= 1;
        }
        let target_range = (u64::MIN as i128)..=(u64::MAX as i128);
        calls.push(self.produce_integral_in_range_call(now as i128, target_range)?);
        Ok(calls)
    }

    pub fn produce_double_in_range_unchecked(
        &mut self,
        value: f64,
        range: RangeInclusive<f64>,
    ) -> EncoderResult {
        let calls = self.produce_double_in_range_call(value, range)?;
        self.stage_and_flush_calls_unchecked(calls);
        Ok(())
    }

    pub fn produce_double_in_range(
        &mut self,
        value: f64,
        range: RangeInclusive<f64>,
    ) -> EncoderResult {
        let calls = self.produce_double_in_range_call(value, range)?;
        self.stage_and_flush_calls(calls)
    }

    fn produce_float_in_range_call(
        &mut self,
        value: f32,
        range: RangeInclusive<f32>,
    ) -> EncoderCallsResult {
        if !range.contains(&value) {
            return Err(EncoderError::ValueNotInRange(
                value.to_string(),
                range.start().to_string(),
                range.end().to_string(),
            ));
        }
        let mut calls = Vec::new();
        let zero = 0.0f32;
        let min = *range.start();
        let max = *range.end();

        let (range_width, result_base) = if max > zero && min < zero && max > min + f32::MAX {
            let range = (max / 2.0) - (min / 2.0);

            // Note: Ambiguous when min + range == value
            // This case is chosen as it can handle when remaining bytes is insufficient when
            // producing probability
            let target_bool = value >= range + min;
            calls.push(self.produce_bool_call(target_bool)?);
            if target_bool {
                (range, min + range)
            } else {
                (range, min)
            }
        } else {
            (max - min, min)
        };

        let mut bit_now: u32 = 1 << (u32::BITS - 1);
        let mut now = 0;
        let int_max = u32::MAX as f32;
        while bit_now > 0 {
            let trial_consume = bit_now + now;
            let prob = (trial_consume as f32) / int_max;
            let trial_value = result_base + range_width * prob;
            if value >= trial_value {
                now = trial_consume;
            }
            if value == trial_value {
                break;
            }
            bit_now >>= 1;
        }
        let target_range = (u32::MIN as i128)..=(u32::MAX as i128);
        calls.push(self.produce_integral_in_range_call(now as i128, target_range)?);
        Ok(calls)
    }

    pub fn produce_float_in_range_unchecked(
        &mut self,
        value: f32,
        range: RangeInclusive<f32>,
    ) -> EncoderResult {
        let calls = self.produce_float_in_range_call(value, range)?;
        self.stage_and_flush_calls_unchecked(calls);
        Ok(())
    }

    pub fn produce_float_in_range(
        &mut self,
        value: f32,
        range: RangeInclusive<f32>,
    ) -> EncoderResult {
        let calls = self.produce_float_in_range_call(value, range)?;
        self.stage_and_flush_calls(calls)
    }

    pub fn produce_probability_double_unchecked(&mut self, value: f64) -> EncoderResult {
        let target_range = (u64::MIN as i128)..=(u64::MAX as i128);
        let target = produce_probability_double_target(value)?;
        self.produce_integral_in_range_unchecked(target as i128, target_range)
    }

    pub fn produce_probability_double(&mut self, value: f64) -> EncoderResult {
        let target_range = (u64::MIN as i128)..=(u64::MAX as i128);
        let target = produce_probability_double_target(value)?;
        self.produce_integral_in_range(target as i128, target_range)
    }

    pub fn produce_probability_float_unchecked(&mut self, value: f32) -> EncoderResult {
        let target_range = (u32::MIN as i128)..=(u32::MAX as i128);
        let target = produce_probability_float_target(value)?;
        self.produce_integral_in_range_unchecked(target as i128, target_range)
    }

    pub fn produce_probability_float(&mut self, value: f32) -> EncoderResult {
        let target_range = (u32::MIN as i128)..=(u32::MAX as i128);
        let target = produce_probability_float_target(value)?;
        self.produce_integral_in_range(target as i128, target_range)
    }

    fn produce_bool_call(&mut self, value: bool) -> EncoderCallResult {
        self.produce_integral_in_range_call(value as i128, u8::MIN as i128..=u8::MAX as i128)
    }

    pub fn produce_bool_unchecked(&mut self, value: bool) -> EncoderResult {
        self.produce_integral_in_range_unchecked(value as i128, u8::MIN as i128..=u8::MAX as i128)
    }

    pub fn produce_bool(&mut self, value: bool) -> EncoderResult {
        self.produce_integral_in_range(value as i128, u8::MIN as i128..=u8::MAX as i128)
    }

    pub fn produce_enum_unchecked(&mut self, value: u32, enum_k_max_value: u32) -> EncoderResult {
        self.produce_integral_in_range_unchecked(value as i128, 0..=enum_k_max_value as i128)
    }

    pub fn produce_enum(&mut self, value: u32, enum_k_max_value: u32) -> EncoderResult {
        self.produce_integral_in_range(value as i128, 0..=enum_k_max_value as i128)
    }

    pub fn produce_array_value_picker_unchecked(
        &mut self,
        target_idx: usize,
        array_length: usize,
    ) -> EncoderResult {
        check_array(array_length)?;
        self.produce_integral_in_range_unchecked(target_idx as i128, 0..=(array_length - 1) as i128)
    }

    pub fn produce_array_value_picker(
        &mut self,
        target_idx: usize,
        array_length: usize,
    ) -> EncoderResult {
        check_array(array_length)?;
        self.produce_integral_in_range(target_idx as i128, 0..=(array_length - 1) as i128)
    }

    pub fn mark_remaining_bytes(&mut self, value: usize) -> EncoderResult {
        match self.target_size {
            | Some(target_extension) => {
                self.try_fit(
                    (target_extension as isize - value as isize) - self.produced_size as isize,
                )
                .map_err(|_| {
                    EncoderError::TargetInputSizeUnmatched(
                        target_extension,
                        value + self.produced_size,
                    )
                })?;
                Ok(())
            },
            | None => {
                self.flush_check_extra_bytes_only();
                self.target_size = Some(value + self.produced_size);
                Ok(())
            },
        }
    }

    pub fn finalize_unchecked(mut self) -> Vec<u8> {
        const EXTENSION_SEQUENCE: [u8; 5] =
            [0b11101101, 0b10100000, 0b10000000, 0b11101101, 0b10110000];
        self.flush_unchecked();
        if let Some(target_extension) = self.target_size {
            if target_extension > self.produced_size {
                let to_extend = target_extension - self.produced_size;
                if to_extend <= 5 {
                    self.committed
                        .extend_from_slice(&EXTENSION_SEQUENCE[..to_extend]);
                } else {
                    self.committed.extend_from_slice(&EXTENSION_SEQUENCE);
                    self.committed.extend_from_slice(&vec![0; to_extend - 5]);
                }
            }
        }
        self.backcommitted.reverse();
        self.committed.extend_from_slice(&self.backcommitted);
        self.committed.to_vec()
    }

    pub fn finalize(mut self) -> Result<Vec<u8>, EncoderError> {
        const EXTENSION_SEQUENCE: [u8; 5] =
            [0b11101101, 0b10100000, 0b10000000, 0b11101101, 0b10110000];
        let to_extend = if let Some(target_size) = self.target_size {
            let target_adjustment = target_size as isize - self.produced_size as isize;
            self.try_fit(target_adjustment)?;
            self.flush()?;
            let target_extend = target_size - self.produced_size;
            let needs = self.flush_check_extra_bytes_only();
            if needs > target_extend {
                let unsat = self.staged[0].extra_bytes_required;
                return Err(EncoderError::ExtraBytesUnsat(unsat));
            }
            target_extend
        } else {
            self.flush_check_extra_bytes_only()
        };
        self.flush_unchecked();
        if to_extend <= 5 {
            self.committed
                .extend_from_slice(&EXTENSION_SEQUENCE[..to_extend]);
        } else {
            self.committed.extend_from_slice(&EXTENSION_SEQUENCE);
            self.committed.extend_from_slice(&vec![0; to_extend - 5]);
        }

        self.backcommitted.reverse();
        self.committed.extend_from_slice(&self.backcommitted);
        Ok(self.committed.to_vec())
    }
}

impl Default for FdpEncoder {
    fn default() -> Self {
        Self::new()
    }
}
