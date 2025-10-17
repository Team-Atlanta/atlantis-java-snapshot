# Submit

[Libcrs Index](../README.md#libcrs-index) / [Libcrs](./index.md#libcrs) / Submit

> Auto-generated documentation for [libCRS.submit](../../libCRS/submit.py) module.

- [Submit](#submit)
  - [Status](#status)
  - [SubmitDB](#submitdb)
    - [SubmitDB().check](#submitdb()check)
    - [SubmitDB().show](#submitdb()show)
    - [SubmitDB().submit_gp](#submitdb()submit_gp)
    - [SubmitDB().submit_vd](#submitdb()submit_vd)
  - [VAPI](#vapi)
    - [VAPI().check_gp](#vapi()check_gp)
    - [VAPI().check_vd](#vapi()check_vd)
    - [VAPI().log](#vapi()log)
    - [VAPI().precompile](#vapi()precompile)
    - [VAPI().submit_gp](#vapi()submit_gp)
    - [VAPI().submit_vd](#vapi()submit_vd)
  - [file_hash](#file_hash)
  - [get_commit_hints_from_file](#get_commit_hints_from_file)
  - [main](#main)
  - [main_check](#main_check)
  - [main_precompile](#main_precompile)
  - [main_show](#main_show)
  - [main_submit_gp](#main_submit_gp)
  - [main_submit_vd](#main_submit_vd)
  - [parse_args](#parse_args)

## Status

[Show source in submit.py:39](../../libCRS/submit.py#L39)

#### Signature

```python
class Status: ...
```



## SubmitDB

[Show source in submit.py:129](../../libCRS/submit.py#L129)

#### Signature

```python
class SubmitDB:
    def __init__(self): ...
```

### SubmitDB().check

[Show source in submit.py:213](../../libCRS/submit.py#L213)

#### Signature

```python
def check(self, remove_rejected: bool): ...
```

### SubmitDB().show

[Show source in submit.py:237](../../libCRS/submit.py#L237)

#### Signature

```python
def show(self): ...
```

### SubmitDB().submit_gp

[Show source in submit.py:190](../../libCRS/submit.py#L190)

#### Signature

```python
def submit_gp(self, patch: Path, cpv_uuid: str, finder: str): ...
```

### SubmitDB().submit_vd

[Show source in submit.py:174](../../libCRS/submit.py#L174)

#### Signature

```python
def submit_vd(
    self,
    harness: str,
    pov_path: Path,
    hints_file: Path | None,
    sanitizer_output_hash: str,
    finder: str,
): ...
```



## VAPI

[Show source in submit.py:46](../../libCRS/submit.py#L46)

#### Signature

```python
class VAPI:
    def __init__(self): ...
```

### VAPI().check_gp

[Show source in submit.py:119](../../libCRS/submit.py#L119)

#### Signature

```python
def check_gp(self, uuid: str) -> Status: ...
```

#### See also

- [Status](#status)

### VAPI().check_vd

[Show source in submit.py:94](../../libCRS/submit.py#L94)

#### Signature

```python
def check_vd(self, uuid: str) -> Status: ...
```

#### See also

- [Status](#status)

### VAPI().log

[Show source in submit.py:50](../../libCRS/submit.py#L50)

#### Signature

```python
def log(self, msg): ...
```

### VAPI().precompile

[Show source in submit.py:67](../../libCRS/submit.py#L67)

#### Signature

```python
def precompile(self, hints_file: Path | None = None): ...
```

### VAPI().submit_gp

[Show source in submit.py:106](../../libCRS/submit.py#L106)

#### Signature

```python
def submit_gp(self, cpv_uuid: str, patch: Path) -> str: ...
```

### VAPI().submit_vd

[Show source in submit.py:78](../../libCRS/submit.py#L78)

#### Signature

```python
def submit_vd(self, harness: str, pov: Path, hints_file: Path | None = None) -> str: ...
```



## file_hash

[Show source in submit.py:33](../../libCRS/submit.py#L33)

#### Signature

```python
def file_hash(path: Path) -> str: ...
```



## get_commit_hints_from_file

[Show source in submit.py:20](../../libCRS/submit.py#L20)

#### Signature

```python
def get_commit_hints_from_file(path: Path) -> list[str]: ...
```



## main

[Show source in submit.py:308](../../libCRS/submit.py#L308)

#### Signature

```python
def main(argv: list[str] | None = None) -> None: ...
```



## main_check

[Show source in submit.py:254](../../libCRS/submit.py#L254)

#### Signature

```python
def main_check(args: argparse.Namespace) -> None: ...
```



## main_precompile

[Show source in submit.py:241](../../libCRS/submit.py#L241)

#### Signature

```python
def main_precompile(args: argparse.Namespace) -> None: ...
```



## main_show

[Show source in submit.py:251](../../libCRS/submit.py#L251)

#### Signature

```python
def main_show(args: argparse.Namespace) -> None: ...
```



## main_submit_gp

[Show source in submit.py:248](../../libCRS/submit.py#L248)

#### Signature

```python
def main_submit_gp(args: argparse.Namespace) -> None: ...
```



## main_submit_vd

[Show source in submit.py:244](../../libCRS/submit.py#L244)

#### Signature

```python
def main_submit_vd(args: argparse.Namespace) -> None: ...
```



## parse_args

[Show source in submit.py:257](../../libCRS/submit.py#L257)

#### Signature

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace: ...
```