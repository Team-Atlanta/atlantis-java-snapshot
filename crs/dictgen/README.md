# Dictionary generator

## Installation

### Install packages

(In virtuanl env)
```sh
pip install -r requirements.txt
```

## How to run

### Setting environment variables

```sh
export LITELLM_KEY=sk-...
export LITELLM_URL=...
export WORKDIR=/path/to/CRS-multilang/workdir
```

Setting `WORKDIR` can be skipped (but still `dictgen` will use it). See `Running tests`.

### Running basic tests

To run basic tests,
```sh
cd src
python3 dictgen.py --test basic
```

If `WORKDIR` is not set, the workdir path can be given as an argument
```sh
cd src
python3 dictgen.py --test basic --workdir /path/to/workdir
```

To test for a specific language (eg, `c`),
```sh
cd src
python3 dictgen.py --test c
```

Currently, `c`, `java`, `python`, and `go` tests exist.

It will exit with exitcode 0 if all basic tests are passed


### Running a single test on oss-fuzz projects

```sh
python3 dictgen.py --test oss-fuzz --test-dict /path/to/oss-fuzz/projects/jvm/fuzzy/.aixcc/dict/test_info.json
```

`--test oss-fuzz` tells `dictgen` to read test information (eg, input functions, answers) from a file given to `--test-dict`.
The json file looks like as follow:

```json
{
  "functions": ["getRatio","getConfigValue","getTagXPath"],
  "answers": ["xcost", ":", "'[^']+'"]
}
```
In `answers`, each string represents a necessary token that should be generated in a form of regular expression.
`dictgen` will find `project.yaml` based on the path of `test_info.json`, clone the repo into `WORKDIR/oss-fuzz`, and run against the cloned repo to check the answers.

### Running all tests on oss-fuzz projects

```sh
python3 dictgen.py --test oss-fuzz-all --path /path/to/oss-fuzz
```

It will look for projects that contain `.aixcc/dict/test_info.json*` and run tests for those projects.
To get the source code, `dictgen` clones the source code into `WORKDIR/oss-fuzz/PROJECT_NAME` (`PROJECT_NAME` is the directory name under `/path/to/oss-fuzz/projects/aixcc/{jvm, c}`).

If `--path` is omitted, `dictgen` uses the `benchmark` directory in the root.


### Running all tests

```sh
python3 dictgen.py --test all --path /path/to/oss-fuzz
```
If `--path` is omitted, `dictgen` uses the `benchmark` directory in the root.


### Running `dictgen`

```sh
python3 dictgen.py --path /path/to/cp-java-fuzzy-source --func getRatio,getConfigValue,getTagXPath
```

NOTE: function names given to `--func` do not contain a corresponding class name. It may be changed in a future.
