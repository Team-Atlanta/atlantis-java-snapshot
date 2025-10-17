import libllm.litellm as litellm
from libllm.resources.logging import logger
import os
import logging
logging.basicConfig(level=logging.DEBUG)

os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY")
BASE_URL = os.getenv("LITELLM_URL")

messages = [{ "content": "Write me a haiku", "role": "user"}]

# openai call
response = litellm.completion(base_url=BASE_URL, model="gpt-3.5-turbo", messages=messages)
print(response.choices[0].message.content)
