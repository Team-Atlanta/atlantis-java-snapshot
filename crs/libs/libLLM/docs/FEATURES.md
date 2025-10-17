# Planned Features

- universal error handling
- **LLM result caching**
- functional LiteLLM API for AIxCC env
- Google Gemini support and testing
- cost calculation (soln could just be a remapping of model names in LiteLLM)
- handling completions hangs
- LLM call scheduling
- budget management
- TODO grep repos for current LLM usage

# Initial Comments from Members

I thought it would be good to have the following features when using an LLM:
- A cost calculation feature, considering the errors that occurred with the completion\_cost litellm API.
- A distinction between errors that need to be retried(RateLimitError) and those that should not be retried (such as Authentication Failure, Budget Exceeds etc.) when an error occurs during completion.
- Budget management at the CRS level?
- Policies for handling hang while completion.
- Calculating the number of tokens of given prompt before completion.

I think we should initially focus on creating wrapped LiteLLM APIs to address the following issues:
1. Errors specific to the unique AIxCC LLM environment.
2. Handling non-fatal exceptions that can be resolved through retries.
3. Common unresolved errors in LiteLLM.
This approach will save team members significant time by mitigating common problems. Additionally, using a common version of LiteLLM will eliminate version-dependent errors.
Regarding high-level convenient APIs (e.g., handling max tokens, function calling), we can provide these as long as team members retain access to the low-level APIs. Since a lack of flexibility might be problematic, offering guidelines instead of restrictive APIs might be more beneficial.

- For the handling of exceptions, expose a wrapped completions function that handles said exceptions ~~+ return an error value (instead of rethrow)?~~
- If we support and wrap both OpenAI API and LiteLLM API, we need a good way to sync the changes (e.g. if we change error handling for wrapped openai, make sure wrapped litellm error handling behaves same)
Features for down the road
- Async / batching support
- LLM call scheduling (HyungSeok may have done sth similar)

In addition, it would be awesome if we can support the LLM result cache
This is for reducing the usage of LLM credit while developing code not related to LLM and testing
