genrule(
    name = "libafl_compiled_libfuzzer_lib",
    srcs = glob([
        "**/*.rs",
        "**/*.c",
        "**/*.h",
        "**/*.cpp",
    ]) + [
        "libafl_libfuzzer_runtime/build.sh",
    ],
    outs = [
        "libafl_libfuzzer_runtime/libFuzzer.a",
    ],
    cmd = """
        ./$(location libafl_libfuzzer_runtime/build.sh)
        BUILD_SH_LOC="$(location libafl_libfuzzer_runtime/build.sh)"
        cp "`dirname $$BUILD_SH_LOC`"/libFuzzer.a $@
    """,
    local = True,  # Required to disable bazel sandboxing.
)

cc_import(
    name = "libfuzzer_no_main",
    hdrs = [],
    static_library = ":libafl_libfuzzer_runtime/libFuzzer.a",
    visibility = ["//visibility:public"],
)
