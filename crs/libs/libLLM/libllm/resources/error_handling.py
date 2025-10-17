from functools import wraps
import asyncio
import time
import openai
from .logging import logger

def handle_openai_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug("OpenAI wrapped error handling")
        MAX_RETRIES = 5
        save_error = None
        delayed_time = 0
        for retry_counter in range(MAX_RETRIES):
            try:
                ret = func(*args, **kwargs)
                if isinstance(ret, object) and hasattr(ret, '__dict__'):
                    ret.__dict__['libllm_delayed_time'] = delayed_time
                return ret
            # follow recommended "solution" https://platform.openai.com/docs/guides/error-codes/python-library-error-types
            except (openai.RateLimitError,
                    openai.APITimeoutError,
                    openai.InternalServerError,
                    openai.UnprocessableEntityError) as e:
                logger.error("OpenAI rate limit or similar, sleeping and retrying")
                save_error = e
                # some sleep logic
                sleep_time = min(2 ** retry_counter, 8)
                delayed_time += sleep_time
                time.sleep(sleep_time)
            except (openai.APIConnectionError,
                    openai.NotFoundError,
                    openai.BadRequestError,
                    openai.AuthenticationError,
                    openai.ConflictError,
                    openai.PermissionDeniedError) as e:
                logger.error("OpenAI other error: %s", e)
                # pass the error through
                raise e
        logger.error("OpenAI unhandled error after retries")
        raise save_error
    return wrapper

def async_handle_openai_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.debug("AsyncOpenAI wrapped error handling")
        MAX_RETRIES = 5
        save_error = None
        delayed_time = 0
        for retry_counter in range(MAX_RETRIES):
            try:
                ret = await func(*args, **kwargs)
                if isinstance(ret, object) and hasattr(ret, '__dict__'):
                    ret.__dict__['libllm_delayed_time'] = delayed_time
                return ret
            # follow recommended "solution" https://platform.openai.com/docs/guides/error-codes/python-library-error-types
            except (openai.RateLimitError,
                    openai.APITimeoutError,
                    openai.InternalServerError,
                    openai.UnprocessableEntityError) as e:
                logger.error("OpenAI rate limit or similar, sleeping and retrying")
                save_error = e
                # some sleep logic
                sleep_time = min(2 ** retry_counter, 8)
                delayed_time += sleep_time
                await asyncio.sleep(sleep_time)
            except (openai.APIConnectionError,
                    openai.NotFoundError,
                    openai.BadRequestError,
                    openai.AuthenticationError,
                    openai.ConflictError,
                    openai.PermissionDeniedError) as e:
                logger.error("OpenAI other error: %s", e)
                # pass the error through
                raise e
        logger.error("OpenAI unhandled error after retries")
        raise save_error
    return wrapper
    
