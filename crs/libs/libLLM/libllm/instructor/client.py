from instructor import Instructor as InstructorUnwrapped
from instructor import from_openai as from_openai_unwrapped
from instructor import from_litellm as from_litellm_unwrapped
from ..resources.logging import logger
from ..resources.error_handling import handle_openai_errors, async_handle_openai_errors

class Instructor(InstructorUnwrapped):
    @handle_openai_errors
    def create(self, *args, **kwargs):
        logger.debug("Instructor create wrapped!")
        return super().create(*args, **kwargs)

def from_openai(*args, **kwargs):
    logger.debug("Instructor from_openai wrapped")
    instructor_instance = from_openai_unwrapped(*args, **kwargs)
    instructor_instance.__class__ = Instructor
    return instructor_instance

def from_litellm(*args, **kwargs):
    logger.debug("Instructor from_litellm wrapped")
    instructor_instance = from_litellm_unwrapped(*args, **kwargs)
    instructor_instance.__class__ = Instructor
    return instructor_instance
