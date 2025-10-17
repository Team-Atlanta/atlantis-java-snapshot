# Setting up local litellm

1. Clone https://github.com/Team-Atlanta/asc-crs-team-atlanta
2. Copy `sandbox/example.env` to `sandbox/env` and populate with API keys
3. In `sandbox/compose.yaml`, rename `services.litellm.expose` to `services.litellm.ports`
    a. Optionally fix the host port, e.g. `32770:80`
4. `cd sandbox` and `docker compose up litellm` to start the litellm docker
5. `cd sandbox` and `docker compose ps` to get the host port number for the proxy
6. Use `http://localhost:<LITELLM_HOST_PORT>` as `base_url` field for LLM client APIs
7. Use `sk-1234` or change `sandbox/litellm/local_litellm_config.yaml` for the master key
