mod encoder;
mod ffi;

pub use encoder::jazzer::{JazzerFdpCall, JazzerFdpEncoder};
pub use encoder::llvm::{LlvmFdpCall, LlvmFdpEncoder};
pub use encoder::{EncoderError, FdpEncoder};

pub enum FdpEncoderChoice {
    Plain(FdpEncoder),
    Llvm(LlvmFdpEncoder),
    Jazzer(JazzerFdpEncoder),
}
