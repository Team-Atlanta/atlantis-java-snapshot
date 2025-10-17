# LLMPOCGEN

LLMPOCGEN is a tool/service that generate seed for fuzzing in given code base.
LLMPOCGEN uses llm, call graph analysis using joern to achieve a goal.

## prerequisite

### Poetry

LLMPOCGEN uses `poetry` for managing dependencies and packaging.
Please follow below instructions before you start.

Install `poetry`: `curl -sSL https://install.python-poetry.org | python -`
Install dependencies: `poetry install`

### Java Agent

LLMPOCGEN uses java agents to run jazzer harnesses. You can build it using `init.sh`.

## usage

Basically, you can run LLMPOCGEN using below command.
`LITELLM_KEY=... RUN_FUZZER_MODE=interactive FUZZING_ENGINE=libfuzzer OUT=... poetry run python -m vuli.main`

### Environment variables

|variables|description|
|LITELLM_KEY|Key to litellm to use LLM|
|RUN_FUZZER_MODE|This is for PoV validation. Simply put interactive here.|
|FUZZING_ENGINE|This is for PoV validation. Simply put libfuzzer here.|
|OUT|This is for PoV validation. Put harness built directory here.|

### options

| option          | required | description                                                                                                                                                                                                                                               |
| --------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| cp_meta         | O        | cp meta file, which is created by crs-java. This file stores information of cp(challenge project)                                                                                                                                                         |
| harnesses       | X        | target harness names. Any possible harness can be target unless specified. You can specify more than one harnesses using `,` as a separator                                                                                                               |
| jazzer          | O        | The directory that jazzer executable and its standalone jar located                                                                                                                                                                                       |
| joern_dir       | O        | The directory of joern codebase. Of course, joern should be built first                                                                                                                                                                                   |
| log_level       | X        | You can choose one of DEBUG, INFO, WARN, ERROR. Default is INFO                                                                                                                                                                                           |
| model_cache     | X        | LLM caches. Every llm interaction are stored in thie cache file, you can reuse previous LLM interaction by using this option to specify the cache file path                                                                                               |
| workers         | X        | Generation workers. This worker assigned to each identified path. Most of tasks that workers do is LLM interaction. So set this carefully considering LLM limits such as TPM. Default is 1                                                                |
| output_dir      | O        | Output directory                                                                                                                                                                                                                                          |
| query           | O        | Query file name. You can choose a file name among files in `queries` directory.                                                                                                                                                                           |
| cg              | X        | Callgraph files. LLMPOCGEN can accept callgraph file whose format is a networkx graph. LLMPOCGEN try to update its callgraph by using these files every 3 minutes. This option only works with the mode `crs`.                                            |
| report          | X        | Print detailed information of identified path. This is stored as a file for each path in output directory.                                                                                                                                                |
| server_dir      | X        | The path to store intermediate result. When rerun LLMPOCGEN if this option is specified, then LLMPOCGEN try to download files in this directory, and skip its initialization stage. This can significanly save time. This only works with the mode `crs`. |
| shared_dir      | X        | The path to store seeds. This is only used with the mode `c-sarif`                                                                                                                                                                                        |
| diff_threashold | X        | Threshold to determine whether start analyze diff file or not. Theshold is file size of diff, it's used to save LLM tokens because LLMPOCGEN analyzes diff by putting all diff files into LLM prompt.                                                     |
| mode            | X        | There are 5 options. You can find details in the below.                                                                                                                                                                                                   |

### modes

#### crs

CRS mode. Run as a service and all features are used. This especially includes synchronizing sinks, intermediate result, call graph. And every some minutes, LLMPOCGEN try to update sinks from outside and if there is any update then it can run all workflow again for new sinks. Also, LLMPOCGEN try to update call graph from outside and if there is any update then it can run all workflow again for sinks whose path not found.

#### onetime

Onetime mode. Run as a onetime tool and workflow executed only once.

#### c_sarif

C program mode only for sarif. Run as a onetime tool but only uses sinks in sarif file. LLMPOCGEN does not have an own scanner for C program.

#### static

Run LLMPOCGEN as a static analyzer. From scanning sinks to finding paths for them. No LLM is used in this mode.

#### sink

Run LLMPOCGEN as a sink scanner. Only scanning sinks works.

## test

You should build sample project first before running unit test. You can install it using below command.
`tests/sample/prepare.sh`

Now, you can run test using below command.
`poetry run pytest -s tests`
