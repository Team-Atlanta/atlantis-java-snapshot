import functools
import logging
import traceback
from enum import Enum

logger = logging.getLogger("Decorators")


class SEVERITY(Enum):
    NORMAL = 0
    WARNING = 1
    ERROR = 2


def async_safe(
    return_value=None, severity: SEVERITY = SEVERITY.NORMAL, module_name: str = ""
):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                if severity == SEVERITY.NORMAL:
                    return return_value

                prefix: str = (
                    "CRS-JAVA-ERR" if severity == SEVERITY.ERROR else "CRS-JAVA-WARN"
                )
                log_level: int = (
                    logging.ERROR if severity == SEVERITY.ERROR else logging.WARNING
                )
                prefix = f"{prefix}-llmpocgen"
                logging.getLogger(module_name).log(
                    log_level, f"{prefix} {traceback.format_exc()}"
                )
                return return_value

        return wrapper

    return decorator


def async_lock(lock_name):
    def decorator(method):
        @functools.wraps(method)
        async def wrapper(self, *args, **kwargs) -> any:
            lock = getattr(self, lock_name)
            async with lock:
                return await method(self, *args, **kwargs)

        return wrapper

    return decorator


def step(
    return_value=None, severity: SEVERITY = SEVERITY.NORMAL, module_name: str = ""
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                if severity == SEVERITY.NORMAL:
                    return return_value

                prefix: str = (
                    "CRS-JAVA-ERR" if severity == SEVERITY.ERROR else "CRS-JAVA-WARN"
                )
                log_level: int = (
                    logging.ERROR if severity == SEVERITY.ERROR else logging.WARNING
                )
                prefix = f"{prefix}-llmpocgen"
                logging.getLogger(module_name).log(
                    log_level, f"{prefix} {traceback.format_exc()}"
                )
                return return_value

        return wrapper

    return decorator


def synchronized(lock_name):
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs) -> any:
            lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kwargs)

        return wrapper

    return decorator
