# Intro

- `aixcc-jazzer` -> link to AIxCC official Jazzer [repo](https://github.com/aixcc-finals/jazzer-aixcc)
- `atl-jazzer` -> Team Atlanta Jazzer
- `atl-libafl-jazzer` -> Jazzer frontend for libAFL-based Jazzer
- `jazzer-libafl` -> libAFL backend for libAFL-based Jazzer

# Feature list of `atl-jazzer`

| Feature | PRs/Commits (With link) | Comment |
| --- | --- | --- |
| set timeout upper bound to 1s for java.nio.channels.SocketChannel.connect | [commit-33a673](https://github.com/Team-Atlanta/CRS-cp-jenkins/commit/33a6732f4fef76b65221b7f813eaa142f0edf69c) | - |
| GEP value profile guidance on InputStream | [PR-104](https://github.com/Team-Atlanta/CRS-cp-jenkins/pull/104), [PR-105](https://github.com/Team-Atlanta/CRS-cp-jenkins/pull/105) | - |
| Disable LLVMFuzzerCustomMutator and LLVMFuzzerCustomCrossOver | [PR-111](https://github.com/Team-Atlanta/CRS-cp-jenkins/pull/111) | - |
| (WIP) Add codemarker instrumentation for beep seed collection in exploitation workflow | [PR-113](https://github.com/Team-Atlanta/CRS-cp-jenkins/pull/113) | New cmdline options `--xcode` & `--beep_seed_dir` for Jazzer |
| Fix sanitizer funcs hook failures (`. -> /, Sting -> String, String -> String[]`) | [PR-114](https://github.com/Team-Atlanta/CRS-cp-jenkins/pull/114) | This exist in any Jazzer, fails the hook of some funcs in LdapInjection and RegexInjection |
| Add cpmeta beepseeds for cp harness meta inference | [commit-5536f3](https://github.com/Team-Atlanta/CRS-java/commit/5536f342bc0e6a9c328984dbb56a412d5bb0d1e1) | Do codemarker instrumentation to init and entry point func when ATLJAZZER_INFER_CPMETA_OUTPUT is set, for harness meta data inference |
| Supp reload in libafl-Jazzer | [commit-455825](https://github.com/Team-Atlanta/CRS-java/commit/455825818844fa2e34ab49e30f189e8cd5510553) | Support reload feature in libafl-Jazzer |
| Supp custom sink point list in Atl-/libafl-Jazzer | [commit-83f2e4](https://github.com/Team-Atlanta/CRS-java/commit/83f2e4c7d22371a92e6e0e4d4eb199f55eadd106) | now we can specify coord or APIs for extending the sinkpoint |
| Fix Atl-/libafl-Jazzer len_control issue | [PR-307](https://github.com/Team-Atlanta/CRS-java/pull/307) [commit-5196e2](https://github.com/Team-Atlanta/CRS-java/pull/307/commits/5196e2931e8f927358d0f44699d1ec054d681f4f) [commit-f6a09a](https://github.com/Team-Atlanta/CRS-java/pull/307/commits/f6a09a5393b2ab7ff79d8617431d217265f65c94) | len_control has bugs when disabling custom mutator |
| Add OOFMutator to ATL-Jazzer | [PR-307](https://github.com/Team-Atlanta/CRS-java/pull/307) | OOFMutator for accepting out of fuzzer seeds such as from libDeepGen |
| Port dict reload back to ATL-Jazzer | [PR-310](https://github.com/Team-Atlanta/CRS-java/pull/310) | ATL-Jazzer auto-reload dict |
| Add corpus coverage reproduction mode to ATL-Jazzer | [commit-c047bd](https://github.com/Team-Atlanta/CRS-java/commit/c047bdcbf2d91435ed52117ff1c51bfb299fda9f) | Sort corpus by mtime and output coverage after each seed when ATLJAZZER_COV_REPRO_BASE_TIMESTAMP is set, useful for tracking coverage growth over time with -runs=0 |
