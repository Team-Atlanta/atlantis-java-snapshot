import libllm.litellm as litellm

try:
    litellm._logging
except AttributeError:
    raise AssertionError("Failed to import private components")
