# Config

[Libcrs Index](../README.md#libcrs-index) / [Libcrs](./index.md#libcrs) / Config

> Auto-generated documentation for [libCRS.config](../../libCRS/config.py) module.

- [Config](#config)
  - [Config](#config-1)
    - [Config().distribute](#config()distribute)
    - [Config().is_module_on](#config()is_module_on)
    - [Config().is_target_harness](#config()is_target_harness)
    - [Config().load](#config()load)
    - [Config().log](#config()log)

## Config

[Show source in config.py:35](../../libCRS/config.py#L35)

#### Signature

```python
class Config:
    def __init__(self, node_idx: int | None = None, node_cnt: int | None = None): ...
```

### Config().distribute

[Show source in config.py:70](../../libCRS/config.py#L70)

#### Signature

```python
def distribute(self, cp: CP, shared_dir: Path): ...
```

### Config().is_module_on

[Show source in config.py:62](../../libCRS/config.py#L62)

#### Signature

```python
def is_module_on(self, module_name: str) -> bool: ...
```

### Config().is_target_harness

[Show source in config.py:97](../../libCRS/config.py#L97)

#### Signature

```python
def is_target_harness(self, harness: CP_Harness): ...
```

### Config().load

[Show source in config.py:49](../../libCRS/config.py#L49)

#### Signature

```python
def load(self, conf_path: Path | str): ...
```

### Config().log

[Show source in config.py:36](../../libCRS/config.py#L36)

#### Signature

```python
def log(self, msg: str): ...
```