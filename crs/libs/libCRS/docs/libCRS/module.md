# Module

[Libcrs Index](../README.md#libcrs-index) / [Libcrs](./index.md#libcrs) / Module

> Auto-generated documentation for [libCRS.module](../../libCRS/module.py) module.

- [Module](#module)
  - [LLM_Module](#llm_module)
    - [LLM_Module().async_run](#llm_module()async_run)
  - [Module](#module-1)
    - [Module().async_prepare](#module()async_prepare)
    - [Module().async_run](#module()async_run)
    - [Module().async_test](#module()async_test)
    - [Module().async_wait_done](#module()async_wait_done)
    - [Module().async_wait_prepared](#module()async_wait_prepared)
    - [Module().ensure_prepared](#module()ensure_prepared)
    - [Module().get_workdir](#module()get_workdir)
    - [Module().is_on](#module()is_on)
    - [Module().log](#module()log)
    - [Module().logH](#module()logh)
    - [Module().prepare](#module()prepare)
    - [Module().run](#module()run)
    - [Module().test](#module()test)
    - [Module().wait_done](#module()wait_done)
    - [Module().wait_prepared](#module()wait_prepared)

## LLM_Module

[Show source in module.py:102](../../libCRS/module.py#L102)

#### Signature

```python
class LLM_Module(Module): ...
```

#### See also

- [Module](#module)

### LLM_Module().async_run

[Show source in module.py:103](../../libCRS/module.py#L103)

#### Signature

```python
async def async_run(self, harness_runner: HarnessRunner | None = None): ...
```



## Module

[Show source in module.py:11](../../libCRS/module.py#L11)

#### Signature

```python
class Module(ABC):
    def __init__(self, name: str, crs: CRS): ...
```

### Module().async_prepare

[Show source in module.py:32](../../libCRS/module.py#L32)

#### Signature

```python
async def async_prepare(self): ...
```

### Module().async_run

[Show source in module.py:61](../../libCRS/module.py#L61)

#### Signature

```python
async def async_run(self, harness_runner: HarnessRunner | None = None): ...
```

### Module().async_test

[Show source in module.py:74](../../libCRS/module.py#L74)

#### Signature

```python
async def async_test(self, harness_runner: HarnessRunner | None = None) -> bool: ...
```

### Module().async_wait_done

[Show source in module.py:53](../../libCRS/module.py#L53)

#### Signature

```python
async def async_wait_done(self): ...
```

### Module().async_wait_prepared

[Show source in module.py:45](../../libCRS/module.py#L45)

#### Signature

```python
async def async_wait_prepared(self): ...
```

### Module().ensure_prepared

[Show source in module.py:40](../../libCRS/module.py#L40)

#### Signature

```python
def ensure_prepared(self): ...
```

### Module().get_workdir

[Show source in module.py:19](../../libCRS/module.py#L19)

#### Signature

```python
def get_workdir(self, name: str) -> Path: ...
```

### Module().is_on

[Show source in module.py:22](../../libCRS/module.py#L22)

#### Signature

```python
def is_on(self) -> bool: ...
```

### Module().log

[Show source in module.py:25](../../libCRS/module.py#L25)

#### Signature

```python
def log(self, msg: str, prefix: str | None = None): ...
```

### Module().logH

[Show source in module.py:29](../../libCRS/module.py#L29)

#### Signature

```python
def logH(self, hrunner: HarnessRunner, msg: str): ...
```

### Module().prepare

[Show source in module.py:37](../../libCRS/module.py#L37)

#### Signature

```python
def prepare(self): ...
```

### Module().run

[Show source in module.py:71](../../libCRS/module.py#L71)

#### Signature

```python
def run(self, harness_runner: HarnessRunner | None = None): ...
```

### Module().test

[Show source in module.py:79](../../libCRS/module.py#L79)

#### Signature

```python
def test(self, harness_runner: HarnessRunner | None = None) -> bool: ...
```

### Module().wait_done

[Show source in module.py:58](../../libCRS/module.py#L58)

#### Signature

```python
def wait_done(self): ...
```

### Module().wait_prepared

[Show source in module.py:50](../../libCRS/module.py#L50)

#### Signature

```python
def wait_prepared(self): ...
```