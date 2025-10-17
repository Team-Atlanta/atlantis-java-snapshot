# Util

[Libcrs Index](../README.md#libcrs-index) / [Libcrs](./index.md#libcrs) / Util

> Auto-generated documentation for [libCRS.util](../../libCRS/util.py) module.

- [Util](#util)
  - [SharedFile](#sharedfile)
    - [SharedFile().async_wait](#sharedfile()async_wait)
    - [SharedFile().finalize](#sharedfile()finalize)
    - [SharedFile().wait](#sharedfile()wait)
    - [SharedFile().write](#sharedfile()write)
  - [TODO](#todo)
  - [cp](#cp)

## SharedFile

[Show source in util.py:31](../../libCRS/util.py#L31)

#### Signature

```python
class SharedFile:
    def __init__(self, path: Path): ...
```

### SharedFile().async_wait

[Show source in util.py:53](../../libCRS/util.py#L53)

#### Signature

```python
async def async_wait(self): ...
```

### SharedFile().finalize

[Show source in util.py:39](../../libCRS/util.py#L39)

#### Signature

```python
def finalize(self): ...
```

### SharedFile().wait

[Show source in util.py:47](../../libCRS/util.py#L47)

#### Signature

```python
def wait(self): ...
```

### SharedFile().write

[Show source in util.py:43](../../libCRS/util.py#L43)

#### Signature

```python
def write(self, data: bytes): ...
```



## TODO

[Show source in util.py:15](../../libCRS/util.py#L15)

#### Signature

```python
def TODO(msg=""): ...
```



## cp

[Show source in util.py:97](../../libCRS/util.py#L97)

#### Signature

```python
def cp(src: Path, dst: Path): ...
```