from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path
import litellm
from ..resources.logging import logger

@dataclass
class AIxCCModel:
    name: str           # model name that is used by application to call completions
    pin: str            # litellm's model_prices_and_context_window.json name
    rpm: Optional[int]  # requests per minute
    tpm: Optional[int]  # tokens per minute

_AIXCC_LITELLM_MODEL_LIST = [
    AIxCCModel(
        'gpt-4o',        # name
        'gpt-4o-2024-05-13', # pin
        400,                 # rpm
        300000               # tpm
    ),
    AIxCCModel(
        'gpt-4o-mini',
        'gpt-4o-mini',
        400,
        300000
    ),
    AIxCCModel(
        'o1',
        'o1-2024-12-17',
        400,
        300000
    ),
    AIxCCModel(
        'o1-preview',
        'o1-preview-2024-09-12',
        400,
        300000
    ),
    AIxCCModel(
        'o1-mini',
        'o1-mini-2024-09-12',
        400,
        300000
    ),
    AIxCCModel(
        'gpt-3.5-turbo',
        'gpt-3.5-turbo-0125',
        800,
        80000
    ),
    AIxCCModel(
        'gpt-4',
        'gpt-4-0613',
        400,
        20000
    ),
    AIxCCModel(
        'gpt-4-turbo',
        'gpt-4-turbo-2024-04-09',
        400,
        60000
    ),
    AIxCCModel(
        'text-embedding-3-large',
        'text-embedding-3-large',
        500,
        200000
    ),
    AIxCCModel(
        'text-embedding-3-small',
        'text-embedding-3-small',
        500,
        200000
    ),
    AIxCCModel(
        'text-embedding-004', # NOTE not prefixed w/ oai
        'text-embedding-004',
        500,
        200000
    ),
    AIxCCModel(
        'claude-3-sonnet-20240229',
        'claude-3-sonnet-20240229',
        1000,
        80000
    ),
    AIxCCModel(
        'claude-3-opus-20240229',
        'claude-3-opus-20240229',
        1000,
        40000
    ),
    AIxCCModel(
        'claude-3-haiku-20240307',
        'claude-3-haiku-20240307',
        1000,
        100000
    ),
    AIxCCModel(
        'claude-3-5-sonnet-20241022',
        'claude-3-5-sonnet-20241022',
        1000,
        80000
    ),
    AIxCCModel(
        'claude-3-5-haiku-20241022',
        'claude-3-5-haiku-20241022',
        1000,
        100000
    ),
    AIxCCModel(
        'gemini-pro',
        'gemini-1.0-pro-002',
        120,
        None
    ),
    AIxCCModel(
        'gemini-1.5-pro',
        'gemini-1.5-pro-preview-0514',
        120,
        None
    ),
    AIxCCModel(
        'gemini-2.0-flash',
        'gemini-1.5-flash', # FIXME 2.0 is not in litellm upstream models.json yet
        None,
        None
    ),
    AIxCCModel(
        'gemini-1.5-flash',
        'gemini-1.5-flash',
        None,
        None
    ),
    AIxCCModel(
        'gemini-1.5-flash-8b',
        'gemini/gemini-1.5-flash-8b',
        None,
        None
    ),
    AIxCCModel(
        'textembedding-gecko',
        'textembedding-gecko@003',
        None,
        None
    ),
    AIxCCModel(
        'azure-gpt-3.5-turbo',
        'azure/gpt-35-turbo-0125',
        800,
        80000
    ),
    AIxCCModel(
        'azure-gpt-4',
        'azure/gpt-4-0613',
        400,
        20000
    ),
    AIxCCModel(
        'azure-gpt-4-turbo',
        'azure/gpt-4-turbo-2024-04-09',
        400,
        60000
    ),
    AIxCCModel(
        'azure-gpt-4o',
        'azure/gpt-4o',
        400,
        300000
    ),
    AIxCCModel(
        'azure-text-embedding-3-large',
        'azure/text-embedding-3-large',
        500,
        200000
    ),
    AIxCCModel(
        'azure-text-embedding-3-small',
        'azure/text-embedding-3-small',
        500,
        200000
    ),
    AIxCCModel(
        'llama-3.1-8b',
        'vertex_ai/meta/llama3-8b-instruct-maas', # FIXME litellm hasn't added llama 3.1 instruct maas from vertex ai yet
        None,
        None
    ),
    AIxCCModel(
        'llama-3.1-70b',
        'vertex_ai/meta/llama3-70b-instruct-maas',
        None,
        None
    )
]

_AIXCC_LITELLM_MODEL_MAP = dict([(model.name, model) for model in _AIXCC_LITELLM_MODEL_LIST])

def _register_all_models():
    logger.debug('registering custom model names')
    litellm.suppress_debug_info = True
    with open(Path(__file__).parent / 'model_prices_and_context_window.json') as f:
        upstream_prices = json.loads(f.read())
    custom_models = {}
    for model in _AIXCC_LITELLM_MODEL_LIST:
        custom_models[model.name] = upstream_prices[model.pin]
        # TODO check azure and generally other regressions
        custom_models[model.name]['litellm_provider'] = 'openai'
    litellm.register_model(custom_models)
    litellm.suppress_debug_info = False

def get_tokens_per_minute(model: str) -> Optional[int]:
    if model in _AIXCC_LITELLM_MODEL_MAP:
        return _AIXCC_LITELLM_MODEL_MAP[model].tpm
    return None

def get_requests_per_minute(model: str) -> Optional[int]:
    if model in _AIXCC_LITELLM_MODEL_MAP:
        return _AIXCC_LITELLM_MODEL_MAP[model].rpm
    return None

_register_all_models()
