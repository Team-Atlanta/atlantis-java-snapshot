import os
import logging
import libllm.litellm as litellm
import libllm.openai as openai

# https://litellm.vercel.app/docs/completion/token_usage

LITELLM_KEY = os.getenv("LITELLM_KEY")
os.environ["OPENAI_API_KEY"] = LITELLM_KEY
BASE_URL = os.getenv("LITELLM_URL")

MODEL='o1-mini'
PROMPT='Write me a haiku'
messages = [{'role':'user', 'content':PROMPT}]

# model cost of all models
print(f'LiteLLM model cost {litellm.model_cost}')

# encoding and decoding
tokens = litellm.encode(model=MODEL, text=PROMPT)
decoded = litellm.decode(model=MODEL, tokens=tokens)
print(f'Decoded prompt: {decoded}')

# token counting
count = litellm.token_counter(model=MODEL, messages=messages)
print(f'Tokens in messages: {count}')

# creating tokenizer: not related to custom model names

# cost per token
prompt_tokens =  5
completion_tokens = 10
prompt_tokens_cost_usd_dollar, completion_tokens_cost_usd_dollar = litellm.cost_per_token(model=MODEL, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
print(prompt_tokens_cost_usd_dollar, completion_tokens_cost_usd_dollar)

# completion cost
chat = openai.OpenAI(base_url=BASE_URL)
resp = chat.chat.completions.create(model=MODEL, messages=messages)
resp_obj = resp.choices[0].message
print(f'OpenAI response: {resp_obj.content}')

comp_cost = litellm.completion_cost(model=MODEL, prompt=PROMPT, completion=resp_obj.content)
print(f'Completion cost: ${comp_cost}')

# max tokens
max_tokens = litellm.get_max_tokens('gpt-4o')
print(f'Max tokens: {max_tokens}')

# Litellm completion
response = litellm.completion(model=MODEL, base_url=BASE_URL, api_key=LITELLM_KEY, messages=messages, custom_llm_provider='openai')
print(f'LiteLLM completion: {response.choices[0].message.content}')
# completion cost for litellm completion
comp_cost = litellm.completion_cost(completion_response=response)
print(f'Completion cost (litellm): {comp_cost}')
