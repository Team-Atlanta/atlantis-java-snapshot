fn main() {
    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo::rerun-if-changed=src/cpp/fdp.cpp");
    println!("cargo::rerun-if-changed=src/cpp/fdp_llvm.cpp");
    println!("cargo::rerun-if-changed=src/cpp/fdp_jazzer.cpp");
    println!("cargo::rerun-if-changed=src/cpp/FuzzedDataProvider.h");
    cc::Build::new()
        .cpp(true)
        .file("./src/cpp/fdp.cpp")
        .file("./src/cpp/fdp_llvm.cpp")
        .file("./src/cpp/fdp_jazzer.cpp")
        .compile("fdp-reference");
}
