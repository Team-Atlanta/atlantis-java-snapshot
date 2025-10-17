import libllm.openai as openai
import libllm.instructor as instructor
from libllm.resources.logging import logger
import os
import logging
logging.basicConfig(level=logging.DEBUG)
from pydantic import BaseModel, Field

# use env vars
os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY")
BASE_URL = os.getenv("LITELLM_URL")

messages = [{ "content": "Write me a haiku", "role": "user"}]

class Poem(BaseModel):
    title: str = Field(description='Title of the poem')
    content: str = Field(description='Poem content')

# openai call
chat = openai.OpenAI(base_url=BASE_URL)
messages = [{'role':'user', 'content':'Write me a haiku'}]
client = instructor.from_openai(
    openai.OpenAI(
    api_key=os.environ["LITELLM_KEY"],
    base_url=BASE_URL
))
answer = client.chat.completions.create(
    model = 'gpt-4o',
    response_model=Poem,
    messages=messages,
    temperature = 0.1,
    max_retries=10
)
print(answer)
