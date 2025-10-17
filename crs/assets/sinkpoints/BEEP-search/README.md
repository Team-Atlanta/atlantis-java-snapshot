# Intro

Scripts for searching BEEP seeds in one or more corpus directories. If contains, it will save one BEEP seed. It is a portable script which will install all required dependencies for that CP.

## Key Usage

Using `htmlunit` as example.

### Step-1. Get patched CP jars

- Clone the `cp-java-htmlunit` and do `make cpsrc-prepare`
- Apply the `beep-report.patch` into `cp-java-htmlunit/src/htmlunit`
- Build the target CP (`make docker-build && bash run.sh build`)
- Copy the built harness jar dir (`out/harnesses/one`) as `portable-htmlunit/cp/one`

### Step-2. Get Jazzer jars

Put at least one version Jazzer jars to `portable-htmlunit/classpath`. You can get them from `CRS-jenkins` container.

For example, copy `/classpath/jazzer` inside `CRS-jenkins` container as `portable-htmlunit/classpath/jazzer`.

### Step-3. Check script works

There is a manually crafted BEEP seed for testing purpose in `find-sink.sh` (search `hex_data=` in that script). Uncomment related script and directly run `bash find-sink.sh` to check whether BEEP search works. **N.B. comment that part when really searching BEEP seeds**.

### Step-4. Use the script to search BEEP seed in specified corpus dirs

**Read their logic before run**.

- `find-sink.sh`, installs dependencies for that CP, accepting one corpus dir as argument to seach BEEP seed
- `batch-find.sh`, accepting multiple BEEP seed search dirs as arguments and internally calls `find-sink.sh`
