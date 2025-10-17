pub use jazzer::JazzerFdpEncoder;
pub use llvm::LlvmFdpEncoder;
use pyo3::{exceptions::PyValueError, prelude::*};

use crate::EncoderError;

pub mod jazzer;
pub mod llvm;

impl From<EncoderError> for PyErr {
    fn from(err: EncoderError) -> PyErr {
        PyValueError::new_err(err.to_string())
    }
}

#[pymodule]
fn libfdp(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<LlvmFdpEncoder>()?;
    m.add_class::<JazzerFdpEncoder>()?;
    Ok(())
}
