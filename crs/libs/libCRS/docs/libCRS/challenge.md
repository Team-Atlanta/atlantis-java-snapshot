# Challenge

[Libcrs Index](../README.md#libcrs-index) / [Libcrs](./index.md#libcrs) / Challenge

> Auto-generated documentation for [libCRS.challenge](../../libCRS/challenge.py) module.

- [Challenge](#challenge)
  - [CP](#cp)
    - [CP().build](#cp()build)
    - [CP().build_ok](#cp()build_ok)
    - [CP().clean_up](#cp()clean_up)
    - [CP().clone](#cp()clone)
    - [CP().log](#cp()log)
  - [CP_Harness](#cp_harness)
    - [CP_Harness().build_ok](#cp_harness()build_ok)
    - [CP_Harness().clean_up](#cp_harness()clean_up)
  - [CP_Src](#cp_src)
    - [CP_Src().build_ok](#cp_src()build_ok)
    - [CP_Src().checkout](#cp_src()checkout)
    - [CP_Src().clean_up](#cp_src()clean_up)

## CP

[Show source in challenge.py:45](../../libCRS/challenge.py#L45)

#### Signature

```python
class CP:
    def __init__(self, base: Path): ...
```

### CP().build

[Show source in challenge.py:81](../../libCRS/challenge.py#L81)

#### Signature

```python
def build(self) -> bool: ...
```

### CP().build_ok

[Show source in challenge.py:91](../../libCRS/challenge.py#L91)

#### Signature

```python
def build_ok(self) -> bool: ...
```

### CP().clean_up

[Show source in challenge.py:87](../../libCRS/challenge.py#L87)

#### Signature

```python
def clean_up(self): ...
```

### CP().clone

[Show source in challenge.py:70](../../libCRS/challenge.py#L70)

Return a CP cloned at dst

Copy the current CP directory into dst and return the CP object for dst

#### Signature

```python
def clone(self, dst: Path): ...
```

### CP().log

[Show source in challenge.py:67](../../libCRS/challenge.py#L67)

#### Signature

```python
def log(self, msg: str): ...
```



## CP_Harness

[Show source in challenge.py:11](../../libCRS/challenge.py#L11)

#### Signature

```python
class CP_Harness:
    def __init__(self, base: Path, id: str, info: dict[str, str]): ...
```

### CP_Harness().build_ok

[Show source in challenge.py:21](../../libCRS/challenge.py#L21)

#### Signature

```python
def build_ok(self): ...
```

### CP_Harness().clean_up

[Show source in challenge.py:18](../../libCRS/challenge.py#L18)

#### Signature

```python
def clean_up(self): ...
```



## CP_Src

[Show source in challenge.py:23](../../libCRS/challenge.py#L23)

#### Signature

```python
class CP_Src:
    def __init__(self, base: Path, name: str, info: dict[str, str]): ...
```

### CP_Src().build_ok

[Show source in challenge.py:42](../../libCRS/challenge.py#L42)

#### Signature

```python
def build_ok(self): ...
```

### CP_Src().checkout

[Show source in challenge.py:35](../../libCRS/challenge.py#L35)

#### Signature

```python
def checkout(self, commit_idx: int, force: bool = True): ...
```

### CP_Src().clean_up

[Show source in challenge.py:39](../../libCRS/challenge.py#L39)

#### Signature

```python
def clean_up(self): ...
```