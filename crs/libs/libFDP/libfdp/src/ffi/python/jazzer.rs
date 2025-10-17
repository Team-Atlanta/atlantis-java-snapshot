use std::{mem, slice};

use pyo3::prelude::*;

#[pyclass]
#[derive(Default)]
pub struct JazzerFdpEncoder {
    inner: crate::JazzerFdpEncoder,
}

#[pymethods]
impl JazzerFdpEncoder {
    #[new]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn produce_jbyte_in_range_unchecked(
        &mut self,
        value: u8,
        min: u8,
        max: u8,
    ) -> PyResult<()> {
        let value = i8::from_ne_bytes(value.to_ne_bytes());
        let min = i8::from_ne_bytes(min.to_ne_bytes());
        let max = i8::from_ne_bytes(max.to_ne_bytes());
        Ok(self
            .inner
            .produce_jbyte_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_jchar_in_range_unchecked(
        &mut self,
        value: u16,
        min: u16,
        max: u16,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_jchar_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_jshort_in_range_unchecked(
        &mut self,
        value: i16,
        min: i16,
        max: i16,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_jshort_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_jint_in_range_unchecked(
        &mut self,
        value: i32,
        min: i32,
        max: i32,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_jint_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_jlong_in_range_unchecked(
        &mut self,
        value: i64,
        min: i64,
        max: i64,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_jlong_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_jbyte_unchecked(&mut self, value: u8) -> PyResult<()> {
        let value = i8::from_ne_bytes(value.to_ne_bytes());
        Ok(self.inner.produce_jbyte_unchecked(value)?)
    }

    pub fn produce_jchar_unchecked(&mut self, value: u16) -> PyResult<()> {
        Ok(self.inner.produce_jchar_unchecked(value)?)
    }

    pub fn produce_jshort_unchecked(&mut self, value: i16) -> PyResult<()> {
        Ok(self.inner.produce_jshort_unchecked(value)?)
    }

    pub fn produce_jint_unchecked(&mut self, value: i32) -> PyResult<()> {
        Ok(self.inner.produce_jint_unchecked(value)?)
    }

    pub fn produce_jlong_unchecked(&mut self, value: i64) -> PyResult<()> {
        Ok(self.inner.produce_jlong_unchecked(value)?)
    }

    pub fn produce_jbool_unchecked(&mut self, value: bool) -> PyResult<()> {
        Ok(self.inner.produce_jbool_unchecked(value)?)
    }

    pub fn produce_regular_jfloat_in_range_unchecked(
        &mut self,
        value: f32,
        min: f32,
        max: f32,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_regular_jfloat_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_regular_jdouble_in_range_unchecked(
        &mut self,
        value: f64,
        min: f64,
        max: f64,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_regular_jdouble_in_range_unchecked(value, min, max)?)
    }

    pub fn produce_regular_jfloat_unchecked(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_regular_jfloat_unchecked(value)?)
    }

    pub fn produce_regular_jdouble_unchecked(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_regular_jdouble_unchecked(value)?)
    }

    pub fn produce_jfloat_unchecked(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_jfloat_unchecked(value)?)
    }

    pub fn produce_jdouble_unchecked(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_jdouble_unchecked(value)?)
    }

    pub fn produce_probability_jfloat_unchecked(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_probability_jfloat_unchecked(value)?)
    }

    pub fn produce_probability_jdouble_unchecked(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_probability_jdouble_unchecked(value)?)
    }

    pub fn produce_jbytes_unchecked(&mut self, value: &[u8]) -> PyResult<()> {
        let value = unsafe { slice::from_raw_parts(value.as_ptr() as *const i8, value.len()) };
        Ok(self.inner.produce_jbytes_unchecked(value)?)
    }

    pub fn produce_jchars_unchecked(&mut self, values: Vec<u16>) -> PyResult<()> {
        Ok(self.inner.produce_jchars_unchecked(&values)?)
    }

    pub fn produce_jshorts_unchecked(&mut self, values: Vec<i16>) -> PyResult<()> {
        Ok(self.inner.produce_jshorts_unchecked(&values)?)
    }

    pub fn produce_jints_unchecked(&mut self, values: Vec<i32>) -> PyResult<()> {
        Ok(self.inner.produce_jints_unchecked(&values)?)
    }

    pub fn produce_jlongs_unchecked(&mut self, values: Vec<i64>) -> PyResult<()> {
        Ok(self.inner.produce_jlongs_unchecked(&values)?)
    }

    pub fn produce_jbools_unchecked(&mut self, values: Vec<bool>) -> PyResult<()> {
        Ok(self.inner.produce_jbools_unchecked(&values)?)
    }

    pub fn produce_remaining_as_jbytes_unchecked(&mut self, value: &[u8]) -> PyResult<()> {
        let value = unsafe { slice::from_raw_parts(value.as_ptr() as *const i8, value.len()) };
        Ok(self.inner.produce_remaining_as_jbytes_unchecked(value)?)
    }

    pub fn produce_ascii_string_unchecked(
        &mut self,
        value: String,
        max_length: i32,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_ascii_string_unchecked(&value, max_length)?)
    }

    pub fn produce_remaining_as_ascii_string_unchecked(&mut self, value: String) -> PyResult<()> {
        Ok(self
            .inner
            .produce_remaining_as_ascii_string_unchecked(&value)?)
    }

    pub fn produce_jstring_unchecked(&mut self, value: String, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_jstring_unchecked(&value, max_length)?)
    }

    pub fn produce_remaining_as_jstring_unchecked(&mut self, value: String) -> PyResult<()> {
        Ok(self.inner.produce_remaining_as_jstring_unchecked(&value)?)
    }

    pub fn produce_picked_value_index_in_jarray_unchecked(
        &mut self,
        value: usize,
        length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_picked_value_index_in_jarray_unchecked(value, length)?)
    }

    pub fn produce_picked_value_indexes_in_jarray_unchecked(
        &mut self,
        values: Vec<usize>,
        length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_picked_value_indexes_in_jarray_unchecked(&values, length)?)
    }

    pub fn produce_jbyte_in_range(&mut self, value: u8, min: u8, max: u8) -> PyResult<()> {
        let value = i8::from_ne_bytes(value.to_ne_bytes());
        let min = i8::from_ne_bytes(min.to_ne_bytes());
        let max = i8::from_ne_bytes(max.to_ne_bytes());
        Ok(self.inner.produce_jbyte_in_range(value, min, max)?)
    }

    pub fn produce_jchar_in_range(&mut self, value: u16, min: u16, max: u16) -> PyResult<()> {
        Ok(self.inner.produce_jchar_in_range(value, min, max)?)
    }

    pub fn produce_jshort_in_range(&mut self, value: i16, min: i16, max: i16) -> PyResult<()> {
        Ok(self.inner.produce_jshort_in_range(value, min, max)?)
    }

    pub fn produce_jint_in_range(&mut self, value: i32, min: i32, max: i32) -> PyResult<()> {
        Ok(self.inner.produce_jint_in_range(value, min, max)?)
    }

    pub fn produce_jlong_in_range(&mut self, value: i64, min: i64, max: i64) -> PyResult<()> {
        Ok(self.inner.produce_jlong_in_range(value, min, max)?)
    }

    pub fn produce_jbyte(&mut self, value: u8) -> PyResult<()> {
        let value = i8::from_ne_bytes(value.to_ne_bytes());
        Ok(self.inner.produce_jbyte(value)?)
    }

    pub fn produce_jchar(&mut self, value: u16) -> PyResult<()> {
        Ok(self.inner.produce_jchar(value)?)
    }

    pub fn produce_jshort(&mut self, value: i16) -> PyResult<()> {
        Ok(self.inner.produce_jshort(value)?)
    }

    pub fn produce_jint(&mut self, value: i32) -> PyResult<()> {
        Ok(self.inner.produce_jint(value)?)
    }

    pub fn produce_jlong(&mut self, value: i64) -> PyResult<()> {
        Ok(self.inner.produce_jlong(value)?)
    }

    pub fn produce_jbool(&mut self, value: bool) -> PyResult<()> {
        Ok(self.inner.produce_jbool(value)?)
    }

    pub fn produce_regular_jfloat_in_range(
        &mut self,
        value: f32,
        min: f32,
        max: f32,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_regular_jfloat_in_range(value, min, max)?)
    }

    pub fn produce_regular_jdouble_in_range(
        &mut self,
        value: f64,
        min: f64,
        max: f64,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_regular_jdouble_in_range(value, min, max)?)
    }

    pub fn produce_regular_jfloat(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_regular_jfloat(value)?)
    }

    pub fn produce_regular_jdouble(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_regular_jdouble(value)?)
    }

    pub fn produce_jfloat(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_jfloat(value)?)
    }

    pub fn produce_jdouble(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_jdouble(value)?)
    }

    pub fn produce_probability_jfloat(&mut self, value: f32) -> PyResult<()> {
        Ok(self.inner.produce_probability_jfloat(value)?)
    }

    pub fn produce_probability_jdouble(&mut self, value: f64) -> PyResult<()> {
        Ok(self.inner.produce_probability_jdouble(value)?)
    }

    pub fn produce_jbytes(&mut self, value: &[u8], max_length: i32) -> PyResult<()> {
        let value = unsafe { slice::from_raw_parts(value.as_ptr() as *const i8, value.len()) };
        Ok(self.inner.produce_jbytes(value, max_length)?)
    }

    pub fn produce_jchars(&mut self, values: Vec<u16>, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_jchars(&values, max_length)?)
    }

    pub fn produce_jshorts(&mut self, values: Vec<i16>, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_jshorts(&values, max_length)?)
    }

    pub fn produce_jints(&mut self, values: Vec<i32>, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_jints(&values, max_length)?)
    }

    pub fn produce_jlongs(&mut self, values: Vec<i64>, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_jlongs(&values, max_length)?)
    }

    pub fn produce_jbools(&mut self, values: Vec<bool>, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_jbools(&values, max_length)?)
    }

    pub fn produce_remaining_as_jbytes(&mut self, value: &[u8]) -> PyResult<()> {
        let value = unsafe { slice::from_raw_parts(value.as_ptr() as *const i8, value.len()) };
        Ok(self.inner.produce_remaining_as_jbytes(value)?)
    }

    pub fn produce_ascii_string(&mut self, value: String, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_ascii_string(&value, max_length)?)
    }

    pub fn produce_remaining_as_ascii_string(&mut self, value: String) -> PyResult<()> {
        Ok(self.inner.produce_remaining_as_ascii_string(&value)?)
    }

    pub fn produce_jstring(&mut self, value: String, max_length: i32) -> PyResult<()> {
        Ok(self.inner.produce_jstring(&value, max_length)?)
    }

    pub fn produce_remaining_as_jstring(&mut self, value: String) -> PyResult<()> {
        Ok(self.inner.produce_remaining_as_jstring(&value)?)
    }

    pub fn produce_picked_value_index_in_jarray(
        &mut self,
        value: usize,
        length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_picked_value_index_in_jarray(value, length)?)
    }

    pub fn produce_picked_value_indexes_in_jarray(
        &mut self,
        values: Vec<usize>,
        length: usize,
    ) -> PyResult<()> {
        Ok(self
            .inner
            .produce_picked_value_indexes_in_jarray(&values, length)?)
    }

    pub fn mark_remaining_bytes(&mut self, value: usize) -> PyResult<()> {
        Ok(self.inner.mark_remaining_bytes(value)?)
    }

    pub fn finalize(&mut self) -> PyResult<Vec<u8>> {
        let encoder = mem::take(&mut self.inner);
        Ok(encoder.finalize()?)
    }
}
