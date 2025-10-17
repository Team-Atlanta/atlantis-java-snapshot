# libLLM

## How to install

Ensure that packages in `libLLM/requirements.txt` (e.g. `litellm`) are not installed already!  We want to pin the LLM API versions.
Please remove such packages from existing module-level `requirements.txt`.

If you're a CRS module developer, you'll have to manually clone libLLM to some relative directory for testing purposes.

In the command line
```
# provide path to libLLM
pip3 install ../libLLM
```

In a module's `requirements.txt`
```
# provide path to libLLM
-e ../libLLM
```

For `crs-cp-user`, we install libLLM in `Dockerfile` so no modification to `requirements.txt` is needed.

## How to use 

For the under-the-hood features such as `completion` rate limit retries, LibLLM
is a drop-in replacement for existing LLM libraries.

``` py
import libllm.openai as openai
import libllm.litellm as litellm
import libllm.instructor as instructor

chat = openai.OpenAI()
messages = [{'role':'user', 'content':'Write me a haiku'}]
resp = chat.chat.completions.create(model='gpt-4o', messages=messages)
```

## Features

- Wrapped error handling for
    - OpenAI `completions.create()` for `OpenAI` and `AsyncOpenAI`
    - LiteLLM `completion()`
    - Instructor `from_openai()` and `completions.create()`
- LiteLLM  token counting, completion cost, and others in 
  [Token Usage](https://litellm.vercel.app/docs/completion/token_usage) for
  AIxCC model names (e.g. `gpt-4`)
- New functions (bundled in `libllm.litellm`) for getting AIxCC specific
  requests per minute and tokens per minute

## Integration with ell

[ell](https://github.com/MadcowD/ell) is a lightweight, 
functional prompt engineering framework that decorates functions for prompts,
and simplifies the usage of LLM API's.

Using `libllm.openai` in `ell` is as simple as defining a custom client:
``` python
import libllm.openai as openai
import os

os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY")
BASE_URL = os.getenv("AIXCC_LITELLM_HOSTNAME")

client = openai.Client(base_url=BASE_URL)

@ell.simple(model="gpt-4o", client=client)
def hello(name: str):
    # """You are a helpful and expressive assistant."""
    adjective = get_random_adjective()
    punctuation = get_random_punctuation()
    return f"Say a {adjective} hello to {name}{punctuation}"

greeting = hello("Sam Altman")
print(greeting)
```

It's tested to work for structured output and tools as well:
``` python
# import and get env vars ...

client = openai.Client(base_url=BASE_URL)

class MovieReview(BaseModel):
    title: str = Field(description="The title of the movie")
    rating: int = Field(description="The rating of the movie out of 10")
    summary: str = Field(description="A brief summary of the movie")

@ell.complex(model="gpt-4o", response_format=MovieReview, client=client)
def generate_movie_review(movie: str) -> MovieReview:
    """You are a movie review generator. Given the name of a movie, you need to return a structured review."""
    return f"generate a review for the movie {movie}"

@ell.tool()
def get_weather(location: str = Field(description="The full name of a city and country, e.g. San Francisco, CA, USA")):
    """Get the current weather for a given location."""
    # Simulated weather API call
    return f"The weather in {location} is sunny."

@ell.complex(model="gpt-4-turbo", tools=[get_weather], client=client)
def travel_planner(destination: str):
    """Plan a trip based on the destination and current weather."""
    return [
        ell.system("You are a travel planner. Use the weather tool to provide relevant advice."),
        ell.user(f"Plan a trip to {destination}")
    ]
```
