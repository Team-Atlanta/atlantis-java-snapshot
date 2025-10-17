import os
import libllm.openai as openai
import libllm.litellm as litellm

os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY")
BASE_URL = os.getenv("LITELLM_URL")

MODEL = 'gemini-1.5-pro'
messages = [{'role':'user', 'content':'Write me a haiku'}]

chat = openai.OpenAI(base_url=BASE_URL)
resp = chat.chat.completions.create(model=MODEL, messages=messages)
resp_obj = resp.choices[0].message
print(f'OpenAI response: {resp_obj.content}')

response = litellm.completion(base_url=BASE_URL, model=MODEL, messages=messages)
print(response.choices[0].message.content)
