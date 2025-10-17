import os
import logging
import libllm.litellm as litellm
from libllm.openai import OpenAI

def test_all(model):
    print(f'Checking {model}')

    provider = litellm.get_llm_provider(model=model)
    print(f'LLM provider {provider}')

    rpm = litellm.get_requests_per_minute(model=model)
    print(f'Model rpm {rpm}')

    tpm = litellm.get_tokens_per_minute(model=model)
    print(f'Model tpm {tpm}')

    supp_func_call = litellm.supports_function_calling(model=model)
    print(f'Model supports function calling? {supp_func_call}')

    max_tokens = litellm.get_max_tokens(model=model)
    print(f'Max tokens {max_tokens}')

    # NOTE: get_model_info may throw
    context_window = litellm.get_model_info(model=model)['max_input_tokens']
    print(f'Context window {context_window}')

if __name__ == '__main__':
    client = OpenAI(
        api_key = os.getenv('LITELLM_KEY'),
        base_url = os.getenv('LITELLM_URL')
    )
        
    models = client.models.list()

    for m in models.data:
        model = m.id
        test_all(model)
