# CRS

[Libcrs Index](../README.md#libcrs-index) / [Libcrs](./index.md#libcrs) / CRS

> Auto-generated documentation for [libCRS.crs](../../libCRS/crs.py) module.

- [CRS](#crs)
  - [CRS](#crs-1)
    - [CRS().async_from_shared_file](#crs()async_from_shared_file)
    - [CRS().async_in_llm_limit](#crs()async_in_llm_limit)
    - [CRS().async_llm_total_spend](#crs()async_llm_total_spend)
    - [CRS().async_precompile](#crs()async_precompile)
    - [CRS().async_run](#crs()async_run)
    - [CRS().async_submit_pov](#crs()async_submit_pov)
    - [CRS().async_to_shared_file](#crs()async_to_shared_file)
    - [CRS().async_wait_prepared](#crs()async_wait_prepared)
    - [CRS().get_module](#crs()get_module)
    - [CRS().get_modules](#crs()get_modules)
    - [CRS().get_workdir](#crs()get_workdir)
    - [CRS().log](#crs()log)
    - [CRS().prepare_modules](#crs()prepare_modules)
    - [CRS().run](#crs()run)
    - [CRS().set_commit_hints](#crs()set_commit_hints)
    - [CRS().submit_pov](#crs()submit_pov)
    - [CRS().wait_prepared](#crs()wait_prepared)
  - [HarnessRunner](#harnessrunner)
    - [HarnessRunner().async_run](#harnessrunner()async_run)
    - [HarnessRunner().async_submit_pov](#harnessrunner()async_submit_pov)
    - [HarnessRunner().get_workdir](#harnessrunner()get_workdir)
    - [HarnessRunner().log](#harnessrunner()log)
    - [HarnessRunner().submit_pov](#harnessrunner()submit_pov)

## CRS

[Show source in crs.py:32](../../libCRS/crs.py#L32)

#### Signature

```python
class CRS(ABC):
    def __init__(
        self, name: str, hrunner_class, config: Config, workdir: Path | None = None
    ): ...
```

### CRS().async_from_shared_file

[Show source in crs.py:112](../../libCRS/crs.py#L112)

#### Signature

```python
async def async_from_shared_file(self, dst: Path) -> Path | None: ...
```

### CRS().async_in_llm_limit

[Show source in crs.py:87](../../libCRS/crs.py#L87)

#### Signature

```python
async def async_in_llm_limit(self): ...
```

### CRS().async_llm_total_spend

[Show source in crs.py:83](../../libCRS/crs.py#L83)

#### Signature

```python
async def async_llm_total_spend(self): ...
```

### CRS().async_precompile

[Show source in crs.py:144](../../libCRS/crs.py#L144)

#### Signature

```python
async def async_precompile(self): ...
```

### CRS().async_run

[Show source in crs.py:172](../../libCRS/crs.py#L172)

#### Signature

```python
async def async_run(self, remove_rejected: bool = False): ...
```

### CRS().async_submit_pov

[Show source in crs.py:127](../../libCRS/crs.py#L127)

#### Signature

```python
async def async_submit_pov(
    self,
    harness: CP_Harness,
    pov_path: Path,
    sanitizer_output_hash: str = "",
    finder: str = "",
): ...
```

### CRS().async_to_shared_file

[Show source in crs.py:107](../../libCRS/crs.py#L107)

#### Signature

```python
async def async_to_shared_file(self, src: Path) -> SharedFile: ...
```

### CRS().async_wait_prepared

[Show source in crs.py:157](../../libCRS/crs.py#L157)

#### Signature

```python
async def async_wait_prepared(self): ...
```

### CRS().get_module

[Show source in crs.py:91](../../libCRS/crs.py#L91)

#### Signature

```python
def get_module(self, name: str) -> "Module": ...
```

### CRS().get_modules

[Show source in crs.py:97](../../libCRS/crs.py#L97)

#### Signature

```python
def get_modules(self) -> list["Module"]: ...
```

### CRS().get_workdir

[Show source in crs.py:99](../../libCRS/crs.py#L99)

#### Signature

```python
def get_workdir(self, name: str) -> Path: ...
```

### CRS().log

[Show source in crs.py:66](../../libCRS/crs.py#L66)

#### Signature

```python
def log(self, msg: str): ...
```

### CRS().prepare_modules

[Show source in crs.py:164](../../libCRS/crs.py#L164)

#### Signature

```python
async def prepare_modules(self): ...
```

### CRS().run

[Show source in crs.py:184](../../libCRS/crs.py#L184)

#### Signature

```python
def run(self, remove_rejected: bool = False): ...
```

### CRS().set_commit_hints

[Show source in crs.py:124](../../libCRS/crs.py#L124)

#### Signature

```python
def set_commit_hints(self, commit_hints: Path): ...
```

### CRS().submit_pov

[Show source in crs.py:140](../../libCRS/crs.py#L140)

#### Signature

```python
def submit_pov(
    self,
    harness: CP_Harness,
    pov_path: Path,
    sanitizer_output_hash: str = "",
    finder: str = "",
): ...
```

### CRS().wait_prepared

[Show source in crs.py:161](../../libCRS/crs.py#L161)

#### Signature

```python
def wait_prepared(self): ...
```



## HarnessRunner

[Show source in crs.py:199](../../libCRS/crs.py#L199)

#### Signature

```python
class HarnessRunner(ABC):
    def __init__(self, harness: CP_Harness, crs: CRS): ...
```

#### See also

- [CRS](#crs)

### HarnessRunner().async_run

[Show source in crs.py:219](../../libCRS/crs.py#L219)

#### Signature

```python
@abstractmethod
async def async_run(self): ...
```

### HarnessRunner().async_submit_pov

[Show source in crs.py:213](../../libCRS/crs.py#L213)

#### Signature

```python
async def async_submit_pov(
    self, pov_path: Path, sanitizer_output_hash: str = "", finder: str = ""
): ...
```

### HarnessRunner().get_workdir

[Show source in crs.py:208](../../libCRS/crs.py#L208)

#### Signature

```python
def get_workdir(self, name: str) -> Path: ...
```

### HarnessRunner().log

[Show source in crs.py:205](../../libCRS/crs.py#L205)

#### Signature

```python
def log(self, msg: str): ...
```

### HarnessRunner().submit_pov

[Show source in crs.py:216](../../libCRS/crs.py#L216)

#### Signature

```python
def submit_pov(
    self, pov_path: Path, sanitizer_output_hash: str = "", finder: str = ""
): ...
```