# Submit Database Analysis

## submit.py

Analyzes submit.db files and displays bug findings.

### Usage

```bash
python3 submit.py <db_file> [options]
```

### Options

- `-v, --verbose`: Show full sanitizer output (multiline)
- `-f, --full-finding`: Include non-security findings (NONSEC-, OOM-, timeout, StackOverflow-)

### Examples

```bash
# Basic usage (security findings only)
python3 submit.py crs-workdir/activemq/submit/submit.db

# Show all findings including non-security ones
python3 submit.py -f crs-workdir/activemq/submit/submit.db

# Verbose output with full sanitizer details
python3 submit.py -v crs-workdir/activemq/submit/submit.db

# All findings with verbose output
python3 submit.py -v -f crs-workdir/activemq/submit/submit.db
```

## analyze.py

Analyzes experiment data and generates CPV status reports or finds beep seed paths.

### Usage

```bash
python3 analyze.py {stat,sum,beep,sinks} ...
```

### Subcommands

#### stat/sum - Generate CPV statistics table

```bash
python3 analyze.py stat <project_name>
python3 analyze.py sum <project_name>  # alias for stat
```

Generates a detailed table showing CPV analysis results including exploited, reached, and in-the-wild status across different harnesses and fuzzers.

**Example:**
```bash
python3 analyze.py stat aixcc/jvm/fuzzy
```

#### beep - Find paths of matched beep seeds

```bash
python3 analyze.py beep <project_name> <cpv_name>
```

Finds and prints all file paths of beep seeds that match the specified CPV's sinkpoints.

**Example:**
```bash
python3 analyze.py beep aixcc/jvm/fuzzy cpv_0
```

#### sinks - Convert project CPV data to TOML format

```bash
python3 analyze.py sinks <regex_pattern> [--all|--exploited|--reached|--in-the-wild]
```

Converts project CPV data to TOML format, showing only sinks with `comment: "trigger"` that match the given regex pattern. The script first collects all CPVs from all projects in the format `project-name.cpv-name`, then filters them using the regex pattern. Each matching sink is output as a TOML section with path, line number, and harness information.

**Status Filtering Options:**
- `--all`: Show all CPVs (exploited, reached, in-the-wild)
- `--exploited`: Show only CPVs that have been exploited (security crashes found)
- `--reached`: Show only CPVs that have been reached (beep signals found)
- `--in-the-wild`: Show only CPVs that are in-the-wild (no crashes or beeps found)
- No option (default): Show all CPVs without status filtering

**Note:** When a CPV has multiple trigger sinkpoints, only the first one is used.

**Examples:**
```bash
# Get all CPVs from activemq project
python3 analyze.py sinks "activemq.*"

# Get specific CPV from batik project
python3 analyze.py sinks "batik\.cpv_0"

# Get all cpv_0 from all projects
python3 analyze.py sinks ".*\.cpv_0$"

# Get all CPVs from projects containing "tika" in the name
python3 analyze.py sinks ".*tika.*"

# Get only exploited CPVs
python3 analyze.py sinks ".*\.cpv_0$" --exploited

# Get only in-the-wild CPVs from activemq
python3 analyze.py sinks "activemq.*" --in-the-wild
```

**Output format:**
```toml
[activemq.cpv_0]
path = "repo/src/main/java/org/apache/activemq/openwire/v1/BaseDataStreamMarshaller.java"
line = 234
harness = ["ActivemqOne", "ActivemqOneFDP"]

[batik.cpv_0]
path = "repo/src/main/java/org/apache/batik/util/ParsedURLData.java"
line = 554
harness = ["BatikOne", "BatikOneFDP"]

[beanutils.cpv_0]
path = "repo/src/main/java/com/aixcc/beanutils/harnesses/one/BeanUtilsOne.java"
line = 79
harness = "BeanUtilsOne"
```

### Examples

```bash
# Generate statistics table for fuzzy project
python3 analyze.py stat aixcc/jvm/fuzzy

# Find all beep seed paths for cpv_0 in fuzzy project
python3 analyze.py beep aixcc/jvm/fuzzy cpv_0

# Convert activemq project CPV data to TOML format
python3 analyze.py sinks "activemq.*"

# Get only exploited CPVs
python3 analyze.py sinks ".*\.cpv_0$" --exploited

# Get help
python3 analyze.py --help
```

## Merged ana cmd

```bash
awk '
BEGIN {
    in_the_wild = 0
    exploited = 0
    reached = 0
    total = 0
}
/In-the-wild:/ { in_the_wild += $2 }
/Exploited:/ { exploited += $2 }
/Reached:/ { reached += $2 }
/Total-CPVs:/ { total += $2 }
END {
    printf "%-15s %8s %8s\n", "Status", "Count", "Percentage"
    printf "%-15s %8s %8s\n", "------", "-----", "----------"
    printf "%-15s %8d %7.1f%%\n", "In-the-wild", in_the_wild, (in_the_wild/total)*100
    printf "%-15s %8d %7.1f%%\n", "Reached", reached, (reached/total)*100
    printf "%-15s %8d %7.1f%%\n", "Exploited", exploited, (exploited/total)*100
    printf "%-15s %8s %8s\n", "------", "-----", "----------"
    printf "%-15s %8d %7.1f%%\n", "Total", total, 100.0
}' misc/eva/ana.txt
```

Output:
```
Status             Count Percentage
------             ----- ----------
In-the-wild           44    66.7%
Reached                8    12.1%
Exploited             14    21.2%
------             ----- ----------
Total                 66   100.0%
```

## analyze_coverage.py

Analyzes and compares coverage metrics across different fuzzing experimental conditions (initial-only, pure-fuzz, with-feedback).

### Usage

```bash
# Run from the CRS-java directory
python3 misc/eva/analyze_coverage.py
```

### Features

- Extracts `max_cov` metrics from result.json files in the crs-workdir directory
- Compares coverage across three experimental conditions:
  - **initial-only**: Fuzzing with initial seeds only
  - **pure-fuzz**: Pure fuzzing without feedback
  - **with-feedback**: Fuzzing with feedback mechanisms
- Displays average coverage per test and overall statistics
- Modular metric extraction function for easy customization

### Customization

To change the metric being analyzed, modify the `get_metric()` function in the script:
- Change the `metric_key` parameter to extract different fields from `fuzz_data`
- Update `get_metric_label()` to reflect the new metric name

### Example Output

```
cen@cerebros:~/deepgen/CRS-java$ python3 misc/eva/analyze_coverage.py

Analyzing coverage metrics...

====================================================================================================
Comparison Table - Metric: Average Max Coverage
====================================================================================================
Test Name                 Initial-Only         Pure-Fuzz            With-Feedback        Eqq-Initial
----------------------------------------------------------------------------------------------------
ImagingOne                2440.3 (n=12)        2052.8 (n=12)        2454.2 (n=12)        2238.5 (n=12)
ImagingOneFDP             2546.2 (n=12)        2073.2 (n=12)        2179.8 (n=12)        2221.3 (n=12)
ImagingTwo                1978.1 (n=12)        1960.9 (n=12)        2498.9 (n=12)        2258.1 (n=12)
ImagingTwoFDP             2121.5 (n=12)        1968.6 (n=12)        2094.2 (n=12)        2087.9 (n=12)
----------------------------------------------------------------------------------------------------

Overall Statistics:
----------------------------------------------------------------------------------------------------
Initial-Only   : Avg=2271.5, Std=266.8, Min=1867.0, Max=2745.0, Total runs=48
Pure-Fuzz      : Avg=2013.9, Std=90.6, Min=1788.0, Max=2270.0, Total runs=48
With-Feedback  : Avg=2306.8, Std=291.4, Min=1903.0, Max=2916.0, Total runs=48
Eqq-Initial    : Avg=2201.5, Std=224.5, Min=1786.0, Max=2810.0, Total runs=48
====================================================================================================

Data Summary:
  initial-only: 4 tests, 48 total runs
  pure-fuzz: 4 tests, 48 total runs
  with-feedback: 4 tests, 48 total runs
  eqq-initial: 4 tests, 48 total runs

```

### Unified Cov Results

| Harness         | initial-only | eqq-initial | with-feedback | pure-fuzz |
|-----------------|--------------|-------------|---------------|-----------|
| ImagingOne      | 2853         | 2927        | 3385          | 2419      |
| ImagingOneFDP   | 2940         | 3090        | 2841          | 2418      |
| ImagingTwo      | 2225         | 2730        | 2999          | 2267      |
| ImagingTwoFDP   | 2533         | 2808        | 2572          | 2241      |
