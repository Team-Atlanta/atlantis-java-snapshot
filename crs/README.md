# CRS-java Source Code

## CRS Component Source Code

- [javacrs_modules](./javacrs_modules)
  - CRS manager layer, gluing all CRS components, managing corpus, crashes, sinkpoints, callgraphs, CP metadata info, etc
- [fuzzers](./fuzzers)
  - jazzer, atl-jazzer, atl-directed-jazzer, atl-libafl-jazzer
- [llm-poc-gen](./llm-poc-gen)
  - Joern-based, path-based, LLM-based, sinkpoint-centered fuzzing input generator
- [static-analysis](./static-analysis)
  - bytecode analyzer for locating & filtering sinkpoints, generating and scheduling direct fuzzer targets
- [codeql](./codeql)
  - adding additional sinkpoints to crs
- [concolic](./concolic)
  - concolic executor
- [expkit](./expkit)
  - beep seed exploitation tool
- [deepgen](./deepgen)
  - fuzzing mutator generation agent (only for initial corpus generation)
- [dictgen](./dictgen)
  - harness dictionary generator
- [jazzer-llm-augmented](./jazzer-llm-augmented)
  - LLM-based coverage enhancer, disabled in competition

## Entry Script

- `run-crs-java.sh` -> Entry script for k8s competition environment
- `dev-run.sh` -> Entry script for local testing & dev environment

## Miscs

- `crs-java.config` -> Default configuration
- `Dockerfile.crs` -> Dockerfile
