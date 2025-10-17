import libllm.openai as openai
import os
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY")
BASE_URL = os.getenv("LITELLM_URL")

chat = openai.OpenAI(base_url=BASE_URL)
messages = [{'role':'user', 'content':'Write me a haiku'}]
resp = chat.chat.completions.create(model='gpt-4o', messages=messages)
resp_obj = resp.choices[0].message
print(f'OpenAI response: {resp_obj.content}')

chat = openai.AsyncOpenAI(base_url=BASE_URL)
messages = [{'role':'user', 'content':'Write me a haiku'}]
resp = asyncio.run(chat.chat.completions.create(model='gpt-4o', messages=messages))
resp_obj = resp.choices[0].message
print(f'AsyncOpenAI response: {resp_obj.content}')
