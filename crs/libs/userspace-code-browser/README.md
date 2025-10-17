# Code Browser

Utility that builds and queries a database containing function definitions from a source code directory.

Features
- Function definition (with leading comments) lookup via function name 
- Function cross reference lookup via function name
- Struct and type querying
- Preprocessor definition lookup
- Condition block lookup
- Supports parsing C
- Parallelize database creation
- Client mode which queries over gRPC to indradb-server
- pyo3 bindings for Python

Planned
- Service in libmsa

Issues
- Python bindings on cutthroat env
- Autoconf files (e.g. `asn1.h.in` in `openssl/include/openssl`)
    - Pay attention to other build systems as well? cmake, meson...
    - Or LLM to analyze the build system? Overkill?
- weird file name but format is mostly C (`ext/standard/var_unserializer.re`),
  this is Ragel file state machine that can by transpiled into C

Low priority
- Optimize queries
- Deduplicate typedef

## Dependencies

Install clang version < 13 due to a bug in the pinned version of RocksDB.

Everything is tested inside a Nix environment, which comes packaged with clang-12.
If [the Nix package manager](https://nixos.org/download/) is installed, 
the `code-browser` binary can be installed with the following command.
```sh
nix --experimental-features 'nix-command flakes' develop --command cargo install --path .
```

Or use the following to enter a dev shell.
```sh
nix --experimental-features 'nix-command flakes' develop
```

If you prefer the nix way:
```sh
nix run <path-to-code-browser-repo> <code-browser-arguments>
# for example
nix run "git+ssh://git@github.com/Team-Atlanta/userspace-code-browser" -- -h
# or install the binary to nix profile
nix profile install <path-to-code-browser-repo>
```

## Python bindings (gRPC client for code-browser-server)

Installable from the `python-client` subdirectory, and example API usage is in `python-client/run.py`.
Requires protobuf.

```sh
pip3 install userspace-code-browser/python-client
```

Simple example:

```py
client = CodeBrowserClient("codebrowser:50051")
response = client.get_function_definition("png_get_mem_ptr")
```

**IMPORTANT** Make sure to handle the error when the code-browser server
has not yet finished indexing for the first time.
The gRPC server will not be initialized until the first-time indexing is finished 
(unless no path is specified to server at startup).
This will be reported as service unavailable in gRPC.
The following example is a simple retry loop.

```py
while True: # or up to certain number of retries
    try:
        client = CodeBrowserClient("codebrowser:50051")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            continue
    break
```

### Managing multiple databases

You can manage multiple source codes being indexed through the `project` field
of both `BuildRequest` and `CodeRequest`.

In `BuildRequest`, please provide the absolute path of the source code which is
in the same container as the `code-browser-server`.
You can specify `force = true` if you want to force the browser to reindex,
otherwise it will ignore dublicate build requests.
The use case here is when the code base has changed and you want to index the
new changes.

The following are a subset of the function prototypes provided.
```py
def build(self, project: str, force: bool)
def get_function_definition(self, name: str, project: Optional[str]=None)
def get_function_cross_references(self, name: str, project: Optional[str]=None)
```

## Python bindings (deprecated pyo3 version)

Tested building in a nix shell nested inside a Python venv.

```sh
source venv/bin/activate                         # enter Python venv
nix develop -c maturin build --release           # create bindings inside Nix env
pip3 install target/wheels/*.whl                 # install wheel

# install server binary
nix --experimental-features 'nix-command flakes' develop -c cargo install indradb
# install code browser binary
nix --experimental-features 'nix-command flakes' develop -c cargo install --path .

code-browser build <REPO>                        # index source code
indradb-server rocksdb ./project_db              # serve
```

Now you can use the code browser in a Python program.
If you want to manage the connections manually, you can use the `CodeBrowser` object.

```py
from userspace_code_browser import CodeBrowser
try:
    client = CodeBrowser()
    print(client.get_function_cross_references("aout_volume_New", json=False))
except Exception as e:
    print(e)
```

Alternatively, you can use the `get_function_cross_references` function directly.
```py
import userspace_code_browser
try:
    print(userspace_code_browser.get_function_cross_references("aout_volume_New", json=False))
except Exception as e:
    print(e)
```

Here is a comparison of the different interfaces on 100 parallel queries.
The benchmark code can be found in `scripts/`.
Managing a single `CodeBrowser` object and querying from there is the fastest
in a multiple process setting.
```
query_from_client_obj: 0.13284792704507709
query_standalone:      0.31265159510076046
query_from_binary:     0.3775522490032017
```

## CLI Usage

There are two main modes: build and query. 
Typically you need to build the database before querying,
and make sure the database location is specified when
querying from another location than where the database was built.

The following commands require the database to be built:
- function definition
- cross references
- type lookup

```
Usage: code-browser [OPTIONS] <COMMAND>

Commands:
  build        Construct a database for quick lookup
  definition   Get function definition
  xref         Get cross references for specific function
  conditional  Get a conditional block given a file and line number
  type         Get type definition
  help         Print this message or the help of the given subcommand(s)

Options:
  -d, --database <DATABASE>  Path to desired database storage. Defaults to "./project_db/"
  -j, --json                 Output function definitions in JSON format
  -c, --client               Enable client mode
  -g, --grpc <GRPC>...       Client mode: optionally specify a port and address
  -v, --verbose              Verbose, mainly to check error message
  -h, --help                 Print help
```

### Client mode

By default, querying from the database is done in disk mode where
the database is read directly from disk.
This may be faster for single threaded use of xref, but does not scale at all to
concurrent accesses due to naive locking done in library dependencies.

Instead, opt for client mode with the flag `-c`.
By default the grpc address used is `127.0.0.1:27615`, but
can be adjusted with `--grpc <port> <address>`.
(FIXME maybe make this option cleaner)

A server needs to be spawned for the client to connect to.
There server just needs the path to the database generated.

This was tested to work for up to 1000 concurrent clients.

```sh
# Compile the server, needs the aforementioned clang-12 dependency
cargo install indradb

# Generate database
code-browser --database ./project_db build <REPO>

# Serve
indradb-server rocksdb ./project_db
```

### Definitions and Cross References

```sh
# Build the database by searching the code at ~/vlc
code-browser -d /tmp/vlc-browser-db build $HOME/vlc

# Get the definition of the vlc_custom_create function
code-browser -d /tmp/vlc-browser-db definition "vlc_custom_create"

# Get all functions that call "vlc_custom_create", output in JSON format
code-browser -j -d /tmp/vlc-browser-db xref "vlc_custom_create"
```

The default format is plaintext source code, prepended with the file path.
For example, using `code-browser definition vlc_custom_create` produces
```sh
/home/andrew/userspace-code-browser/sandbox/vlc/src/misc/objects.c
void *(vlc_custom_create)(vlc_object_t *parent, size_t length,
                          const char *typename)
{
    assert(length >= sizeof (vlc_object_t));

    vlc_object_t *obj = calloc(length, 1);
    if (unlikely(obj == NULL || vlc_object_init(obj, parent, typename))) {
        free(obj);
        obj = NULL;
    }
    return obj;
}
```

While using the JSON flag using `code-browser -j definition vlc_custom_create` produces
```json
[{
    "name": "vlc_custom_create",
    "definition": "void *(vlc_custom_create)(vlc_object_t *parent, size_t length,\n                          const char *typename)\n{\n    assert(length >= sizeof (vlc_object_t));\n\n    vlc_object_t *obj = calloc(length, 1);\n    if (unlikely(obj == NULL || vlc_object_init(obj, parent, typename))) {\n        free(obj);\n        obj = NULL;\n    }\n    return obj;\n}",
    "filename": "/home/andrew/userspace-code-browser/sandbox/vlc/src/misc/objects.c",
    "references": ["assert","calloc","unlikely","vlc_object_init","free"]
}]
```

### Type Definitions

```
Usage: code-browser type [OPTIONS] <TYPE>

Arguments:
  <TYPE>  Name of type to query

Options:
  -k, --kind <KIND>  What kind of type to query. Defaults to all [possible values: all, struct, enum, union, typedef]
  -h, --help         Print help
```

To get all definitions for a particular symbol, you may for example use `code-browser type sout_stream_id_sys_t`.

If you need only the struct definitions, you may specify so using `code-browser type -k struct sout_stream_id_sys_t`.

### Conditional Blocks

```sh
Get a conditional block given a file and line number

Usage: code-browser conditional <PATH> <LINE>

Arguments:
  <PATH>  Path to single source code file
  <LINE>  Line number, starting at 1

Options:
  -h, --help  Print help
```

Here is a simple C program
```c
int main() {
    int cond = (1 + 2) < 30 % 10 - 2;
    int a;
    if (cond || !(cond) && 1) {
        a = 1;
    }
    else if (cond + cond < cond) { // this is considered (else_clause (if_statement))
        a = 2;
    }
    else if (cond && cond) {
        a = 3;
    }
    else {
        a = 4;
    }
    switch (cond) {
        case 1:
            a = 3;
            break;
        case 2: {
            int c = 12;
            a = 4 + c;
            break;
        }
        default:
            a = 10;
            break;
    }
}
```

Using the browser via `code-browser conditional simple.c 7` produces the
following.
Whitespace format fixing TODO if poses an issue.
```c
int cond = (1 + 2) < 30 % 10 - 2;
    int a;
    if (cond || !(cond) && 1) {
        a = 1;
    }
    else if (cond + cond < cond) { // this is considered (else_clause (if_statement))
        a = 2;
    }
    else if (cond && cond) {
        a = 3;
    }
    else {
        a = 4;
    }
```
