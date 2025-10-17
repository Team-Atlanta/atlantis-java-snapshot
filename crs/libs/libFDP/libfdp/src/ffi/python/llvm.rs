use std::mem;

use pyo3::prelude::*;

#[pyclass]
#[derive(Default)]
pub struct LlvmFdpEncoder {
    inner: crate::LlvmFdpEncoder,
}

#[pymethods]
impl LlvmFdpEncoder {
    #[new]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn produce_byte_in_range_unchecked(&mut self, value: u8, min: u8, max: u8) -> PyResult<()> {
        Ok(self
            .inner
            .produce_byte_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_char_in_range_unchecked(&mut self, value: i8, min: i8, max: i8) -> PyResult<()> {
        Ok(self
            .inner
            .produce_char_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_short_in_range_unchecked(
        &mut self,
        value: i16,
        min: i16,
        max: i16,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_short_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_unsigned_short_in_range_unchecked(
        &mut self,
        value: u16,
        min: u16,
        max: u16,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_unsigned_short_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_int_in_range_unchecked(
        &mut self,
        value: i32,
        min: i32,
        max: i32,
    ) -> PyResult<()> {
        Ok(self.inner.produce_int_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_unsigned_int_in_range_unchecked(
        &mut self,
        value: u32,
        min: u32,
        max: u32,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_unsigned_int_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_long_long_in_range_unchecked(
        &mut self,
        value: i64,
        min: i64,
        max: i64,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_long_long_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_unsigned_long_long_in_range_unchecked(
        &mut self,
        value: u64,
        min: u64,
        max: u64,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_unsigned_long_long_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_byte_unchecked(&mut self, value: u8) -> PyResult<()> {
        Ok(self.inner.produce_byte_unchecked(value)?)
    }

    pub fn produce_char_unchecked(&mut self, value: i8) -> PyResult<()> {
        Ok(self.inner.produce_char_unchecked(value)?)
    }

    pub fn produce_short_unchecked(&mut self, value: i16) -> PyResult<()> {
        Ok(self.inner.produce_short_unchecked(value)?)
    }

    pub fn produce_unsigned_short_unchecked(&mut self, value: u16) -> PyResult<()> {
        Ok(self.inner.produce_unsigned_short_unchecked(value)?)
    }

    pub fn produce_int_unchecked(&mut self, value: i32) -> PyResult<()> {
        Ok(self.inner.produce_int_unchecked(value)?)
    }

    pub fn produce_unsigned_int_unchecked(&mut self, value: u32) -> PyResult<()> {
        Ok(self.inner.produce_unsigned_int_unchecked(value)?)
    }

    pub fn produce_long_long_unchecked(&mut self, value: i64) -> PyResult<()> {
        Ok(self.inner.produce_long_long_unchecked(value)?)
    }

    pub fn produce_unsigned_long_long_unchecked(&mut self, value: u64) -> PyResult<()> {
        Ok(self.inner.produce_unsigned_long_long_unchecked(value)?)
    }

    pub fn produce_bool_unchecked(&mut self, value: bool) -> PyResult<()> {
        Ok(self.inner.produce_bool_unchecked(value)?)
    }

    pub fn produce_float_in_range_unchecked(
        &mut self,
        value: f32,
        min: f32,
        max: f32,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_float_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_double_in_range_unchecked(
        &mut self,
        value: f64,
        min: f64,
        max: f64,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_double_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_float_unchecked(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_float_unchecked(value)?)
    }

    pub fn produce_double_unchecked(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_double_unchecked(value)?)
    }

    pub fn produce_probability_float_unchecked(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_probability_float_unchecked(value)?)
    }

    pub fn produce_probability_double_unchecked(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_probability_double_unchecked(value)?)
    }

    pub fn produce_enum_unchecked(&mut self, value: u32, max_value: u32) -> PyResult<()> {
        Ok(self.inner.produce_enum_unchecked(value, max_value)?)
    }

    pub fn produce_bytes_unchecked(&mut self, value: &[u8]) -> PyResult<()> {
        Ok(self.inner.produce_bytes_unchecked(value)?)
    }

    pub fn produce_bytes_with_terminator_unchecked(
        &mut self,
        value: &[u8],
        terminator: u8,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_bytes_with_terminator_unchecked(value, terminator)?)
    }

    pub fn produce_remaining_bytes_unchecked(&mut self, value: &[u8]) -> PyResult<()> {
        self.produce_bytes_unchecked(value)
    }

    pub fn produce_remaining_bytes_as_string_unchecked(&mut self, value: &[u8]) -> PyResult<()> {
        self.produce_bytes_unchecked(value)
    }

    pub fn produce_bytes_as_string_unchecked(
        &mut self,
        value: &[u8],
        num_bytes: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_bytes_as_string_unchecked(value, num_bytes)?)
    }

    pub fn produce_random_length_string_with_max_length_unchecked(
        &mut self,
        value: &[u8],
        max_length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_random_length_string_with_max_length_unchecked(value, max_length)?)
    }

    pub fn produce_random_length_string_unchecked(&mut self, value: &[u8]) -> PyResult<()> {
        Ok(self.inner.produce_random_length_string_unchecked(value)?)
    }

    pub fn produce_picked_value_index_in_array_unchecked(
        &mut self,
        value: usize,
        length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_picked_value_index_in_array_unchecked(value, length)?)
    }

    pub fn produce_byte_in_range(&mut self, value: u8, min: u8, max: u8) -> PyResult<()> {
        Ok(self.inner.produce_byte_in_range(value, min, max)?)
    }

    pub fn produce_char_in_range(&mut self, value: i8, min: i8, max: i8) -> PyResult<()> {
        Ok(self.inner.produce_char_in_range(value, min, max)?)
    }

    pub fn produce_short_in_range(&mut self, value: i16, min: i16, max: i16) -> PyResult<()> {
        Ok(self.inner.produce_short_in_range(value, min, max)?)
    }

    pub fn produce_unsigned_short_in_range(
        &mut self,
        value: u16,
        min: u16,
        max: u16,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_unsigned_short_in_range(value, min, max)?)
    }

    pub fn produce_int_in_range(&mut self, value: i32, min: i32, max: i32) -> PyResult<()> {
        Ok(self.inner.produce_int_in_range(value, min, max)?)
    }

    pub fn produce_unsigned_int_in_range(
        &mut self,
        value: u32,
        min: u32,
        max: u32,
    ) -> PyResult<()> {
        Ok(self.inner.produce_unsigned_int_in_range(value, min, max)?)
    }

    pub fn produce_long_long_in_range(&mut self, value: i64, min: i64, max: i64) -> PyResult<()> {
        Ok(self.inner.produce_long_long_in_range(value, min, max)?)
    }

    pub fn produce_unsigned_long_long_in_range(
        &mut self,
        value: u64,
        min: u64,
        max: u64,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_unsigned_long_long_in_range(value, min, max)?)
    }

    pub fn produce_byte(&mut self, value: u8) -> PyResult<()> {
        Ok(self.inner.produce_byte(value)?)
    }

    pub fn produce_char(&mut self, value: i8) -> PyResult<()> {
        Ok(self.inner.produce_char(value)?)
    }

    pub fn produce_short(&mut self, value: i16) -> PyResult<()> {
        Ok(self.inner.produce_short(value)?)
    }

    pub fn produce_unsigned_short(&mut self, value: u16) -> PyResult<()> {
        Ok(self.inner.produce_unsigned_short(value)?)
    }

    pub fn produce_int(&mut self, value: i32) -> PyResult<()> {
        Ok(self.inner.produce_int(value)?)
    }

    pub fn produce_unsigned_int(&mut self, value: u32) -> PyResult<()> {
        Ok(self.inner.produce_unsigned_int(value)?)
    }

    pub fn produce_long_long(&mut self, value: i64) -> PyResult<()> {
        Ok(self.inner.produce_long_long(value)?)
    }

    pub fn produce_unsigned_long_long(&mut self, value: u64) -> PyResult<()> {
        Ok(self.inner.produce_unsigned_long_long(value)?)
    }

    pub fn produce_bool(&mut self, value: bool) -> PyResult<()> {
        Ok(self.inner.produce_bool(value)?)
    }

    pub fn produce_float_in_range(&mut self, value: f32, min: f32, max: f32) -> PyResult<()> {
        Ok(self.inner.produce_float_in_range(value, min, max)?)
    }

    pub fn produce_double_in_range(&mut self, value: f64, min: f64, max: f64) -> PyResult<()> {
        Ok(self.inner.produce_double_in_range(value, min, max)?)
    }

    pub fn produce_float(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_float(value)?)
    }

    pub fn produce_double(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_double(value)?)
    }

    pub fn produce_probability_float(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_probability_float(value)?)
    }

    pub fn produce_probability_double(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_probability_double(value)?)
    }

    pub fn produce_enum(&mut self, value: u32, max_value: u32) -> PyResult<()> {
        Ok(self.inner.produce_enum(value, max_value)?)
    }

    pub fn produce_bytes(&mut self, value: &[u8], num_bytes: usize) -> PyResult<()> {
        Ok(self.inner.produce_bytes(value, num_bytes)?)
    }

    pub fn produce_bytes_with_terminator(
        &mut self,
        value: &[u8],
        num_bytes: usize,
        terminator: u8,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_bytes_with_terminator(value, num_bytes, terminator)?)
    }

    pub fn produce_remaining_bytes(&mut self, value: &[u8]) -> PyResult<()> {
        Ok(self.inner.produce_remaining_bytes(value)?)
    }

    pub fn produce_remaining_bytes_as_string(&mut self, value: &[u8]) -> PyResult<()> {
        Ok(self.inner.produce_remaining_bytes_as_string(value)?)
    }

    pub fn produce_bytes_as_string(&mut self, value: &[u8], num_bytes: usize) -> PyResult<()> {
        Ok(self.inner.produce_bytes_as_string(value, num_bytes)?)
    }

    pub fn produce_random_length_string_with_max_length(
        &mut self,
        value: &[u8],
        max_length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_random_length_string_with_max_length(value, max_length)?)
    }

    pub fn produce_random_length_string(&mut self, value: &[u8]) -> PyResult<()> {
        Ok(self.inner.produce_random_length_string(value)?)
    }

    pub fn produce_picked_value_index_in_array(
        &mut self,
        value: usize,
        length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_picked_value_index_in_array(value, length)?)
    }

    pub fn mark_remaining_bytes(&mut self, value: usize) -> PyResult<()> {
        Ok(self.inner.mark_remaining_bytes(value)?)
    }

    pub fn finalize(&mut self) -> PyResult<Vec<u8>> {
        let encoder = mem::take(&mut self.inner);
        Ok(encoder.finalize()?)
    }
}
