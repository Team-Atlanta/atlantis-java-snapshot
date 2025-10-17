use std::ffi::c_void;

unsafe extern "C" {
    pub unsafe fn init(buf: *const u8, size: usize) -> *mut c_void;
    pub safe fn deinit(fdp: *mut c_void);
    pub safe fn remainingBytes(fdp: *mut c_void) -> usize;

    // LLVM
    pub safe fn consumeByteInRange(fdp: *mut c_void, min: u8, max: u8) -> u8;
    pub safe fn consumeCharInRange(fdp: *mut c_void, min: i8, max: i8) -> i8;
    pub safe fn consumeShortInRange(fdp: *mut c_void, min: i16, max: i16) -> i16;
    pub safe fn consumeUnsignedShortInRange(fdp: *mut c_void, min: u16, max: u16) -> u16;
    pub safe fn consumeIntInRange(fdp: *mut c_void, min: i32, max: i32) -> i32;
    pub safe fn consumeUnsignedIntInRange(fdp: *mut c_void, min: u32, max: u32) -> u32;
    pub safe fn consumeLongLongInRange(fdp: *mut c_void, min: i64, max: i64) -> i64;
    pub safe fn consumeUnsignedLongLongInRange(fdp: *mut c_void, min: u64, max: u64) -> u64;
    pub safe fn consumeByte(fdp: *mut c_void) -> u8;
    pub safe fn consumeChar(fdp: *mut c_void) -> i8;
    pub safe fn consumeShort(fdp: *mut c_void) -> i16;
    pub safe fn consumeUnsignedShort(fdp: *mut c_void) -> u16;
    pub safe fn consumeInt(fdp: *mut c_void) -> i32;
    pub safe fn consumeUnsignedInt(fdp: *mut c_void) -> u32;
    pub safe fn consumeLongLong(fdp: *mut c_void) -> i64;
    pub safe fn consumeUnsignedLongLong(fdp: *mut c_void) -> u64;
    pub safe fn consumeBool(fdp: *mut c_void) -> bool;
    pub safe fn consumeFloatInRange(fdp: *mut c_void, min: f32, max: f32) -> f32;
    pub safe fn consumeDoubleInRange(fdp: *mut c_void, min: f64, max: f64) -> f64;
    pub safe fn consumeFloat(fdp: *mut c_void) -> f32;
    pub safe fn consumeDouble(fdp: *mut c_void) -> f64;
    pub safe fn consumeProbabilityFloat(fdp: *mut c_void) -> f32;
    pub safe fn consumeProbabilityDouble(fdp: *mut c_void) -> f64;
    pub safe fn consumeEnum(fdp: *mut c_void, max_value: u32) -> u32;
    pub unsafe fn consumeBytes(fdp: *mut c_void, output: *mut u8, num_bytes: usize) -> usize;
    pub unsafe fn consumeBytesWithTerminator(
        fdp: *mut c_void,
        output: *mut u8,
        num_bytes: usize,
        terminator: u8,
    ) -> usize;
    pub unsafe fn consumeRemainingBytes(fdp: *mut c_void, output: *mut u8) -> usize;
    pub unsafe fn consumeBytesAsString(
        fdp: *mut c_void,
        output: *mut u8,
        num_bytes: usize,
    ) -> usize;
    pub unsafe fn consumeRandomLengthStringWithMaxLength(
        fdp: *mut c_void,
        output: *mut u8,
        max_length: usize,
    ) -> usize;
    pub unsafe fn consumeRandomLengthString(fdp: *mut c_void, output: *mut u8) -> usize;
    pub unsafe fn consumeRemainingBytesAsString(fdp: *mut c_void, output: *mut u8) -> usize;
    pub safe fn pickValueIndexInArray(fdp: *mut c_void, size: usize) -> usize;

    // Jazzer
    pub safe fn consumeJByteInRange(fdp: *mut c_void, min: i8, max: i8) -> i8;
    pub safe fn consumeJCharInRange(fdp: *mut c_void, min: u16, max: u16) -> u16;
    pub safe fn consumeJShortInRange(fdp: *mut c_void, min: i16, max: i16) -> i16;
    pub safe fn consumeJIntInRange(fdp: *mut c_void, min: i32, max: i32) -> i32;
    pub safe fn consumeJLongInRange(fdp: *mut c_void, min: i64, max: i64) -> i64;
    pub safe fn consumeJByte(fdp: *mut c_void) -> i8;
    pub safe fn consumeJChar(fdp: *mut c_void) -> u16;
    pub safe fn consumeJCharNoSurrogates(fdp: *mut c_void) -> u16;
    pub safe fn consumeJShort(fdp: *mut c_void) -> i16;
    pub safe fn consumeJInt(fdp: *mut c_void) -> i32;
    pub safe fn consumeJLong(fdp: *mut c_void) -> i64;
    pub safe fn consumeJBoolean(fdp: *mut c_void) -> u8;
    pub safe fn consumeRegularJFloatInRange(fdp: *mut c_void, min: f32, max: f32) -> f32;
    pub safe fn consumeRegularJDoubleInRange(fdp: *mut c_void, min: f64, max: f64) -> f64;
    pub safe fn consumeRegularJFloat(fdp: *mut c_void) -> f32;
    pub safe fn consumeRegularJDouble(fdp: *mut c_void) -> f64;
    pub safe fn consumeJFloat(fdp: *mut c_void) -> f32;
    pub safe fn consumeJDouble(fdp: *mut c_void) -> f64;
    pub safe fn consumeProbabilityJFloat(fdp: *mut c_void) -> f32;
    pub safe fn consumeProbabilityJDouble(fdp: *mut c_void) -> f64;
    pub unsafe fn consumeJBytes(fdp: *mut c_void, out: *mut i8, max_length: usize) -> usize;
    pub unsafe fn consumeJChars(fdp: *mut c_void, out: *mut u16, max_length: usize) -> usize;
    pub unsafe fn consumeJShorts(fdp: *mut c_void, out: *mut i16, max_length: usize) -> usize;
    pub unsafe fn consumeJInts(fdp: *mut c_void, out: *mut i32, max_length: usize) -> usize;
    pub unsafe fn consumeJLongs(fdp: *mut c_void, out: *mut i64, max_length: usize) -> usize;
    pub unsafe fn consumeJBooleans(fdp: *mut c_void, out: *mut u8, max_length: usize) -> usize;
    pub unsafe fn consumeRemainingAsJBytes(fdp: *mut c_void, out: *mut i8) -> usize;
    pub unsafe fn consumeAsciiString(fdp: *mut c_void, out: *mut u8, max_length: usize) -> usize;
    pub unsafe fn consumeJString(fdp: *mut c_void, out: *mut u8, max_length: usize) -> usize;
    pub unsafe fn consumeRemainingAsAsciiString(fdp: *mut c_void, out: *mut u8) -> usize;
    pub unsafe fn consumeRemainingAsJString(fdp: *mut c_void, out: *mut u8) -> usize;
    pub safe fn pickValueIndexInJArray(fdp: *mut c_void, size: usize) -> usize;
    pub unsafe fn pickValueIndexesInJArray(
        fdp: *mut c_void,
        out: *mut usize,
        pick_count: usize,
        array_size: usize,
    ) -> usize;
    pub unsafe fn fixJString(
        input: *const u8,
        input_size: usize,
        output: *mut u8,
        max_length: usize,
        utf8_length: *mut usize,
        ascii_only: bool,
        stop_on_backslash: bool,
    ) -> usize;
}
