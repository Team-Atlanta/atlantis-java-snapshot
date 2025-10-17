import os
import re
import logging
from contextlib import contextmanager
from typing import Iterator, Optional, Dict

logger = logging.getLogger(__name__)


@contextmanager
def cd(pn: str) -> Iterator[None]:
    """Context manager to change the current working directory."""
    cur = os.getcwd()
    os.chdir(os.path.expanduser(pn))
    try:
        yield
    finally:
        os.chdir(cur)


@contextmanager
def environ(
    key: str, value: Optional[str], concat: Optional[str] = None, prepend: bool = True
) -> Iterator[None]:
    """Context manager to temporarily set an environment variable."""

    def _set_env(k: str, v: Optional[str]) -> None:
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    old_value = os.environ.get(key, None)

    if value is None or concat is None or old_value is None:
        new_value = value
    elif prepend:
        new_value = value + concat + old_value
    else:
        new_value = old_value + concat + value

    _set_env(key, new_value)

    try:
        yield
    finally:
        _set_env(key, old_value)


@contextmanager
def environs(env_vars: Dict[str, Optional[str]]) -> Iterator[None]:
    """Context manager to temporarily set multiple environment variables."""
    original_values = {}

    def _set_env(k: str, v: Optional[str]) -> None:
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    try:
        # Store original values and set new ones
        for key, value in env_vars.items():
            original_values[key] = os.environ.get(key, None)
            _set_env(key, value)

        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            _set_env(key, original_value)


def remove_extra_line_breaks(text: str) -> str:
    return re.sub(r"\n{2,}", "\n\n", text)
