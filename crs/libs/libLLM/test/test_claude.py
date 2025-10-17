import os
import libllm.openai as openai
import libllm.litellm as litellm

os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY")
BASE_URL = os.getenv("LITELLM_URL")

MODEL = 'claude-3-sonnet'

def test_claude(model):
    messages = [{'role':'user', 'content':'Write me a haiku'}]

    chat = openai.OpenAI(base_url=BASE_URL)
    resp = chat.chat.completions.create(model=model, messages=messages)
    resp_obj = resp.choices[0].message
    print(f'Claude response: {resp_obj.content}')

    response = litellm.completion(base_url=BASE_URL, model=model, messages=messages)
    print(response.choices[0].message.content)

models = [
    'claude-3-sonnet-20240229',
    'claude-3-opus-20240229',
    'claude-3-haiku-20240307',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022'
]

for model in models:
    test_claude(model)
