# Exploit Kit

A tool for exploiting sinkpoint BEEPs to generate proof-of-concept (POC) exploits for various vulnerabilities.

## Installation

```bash
pip3 install -r requirements.txt
pip3 install -e .
```

## Env Setup

Before using the tool, set the following environment variables:

```bash
export LITELLM_KEY=your_api_key_here
export AIXCC_LITELLM_HOSTNAME=your_litellm_endpoint
export ATL_JAZZER_DIR=/path/to/jazzer/dir  # By default have in javacrs env
```

## Usage

```bash
python -m expkit.exploit \
            /path/to/beepseed.json \
	    /path/to/output.json \
	    --metadata /path/to/cpmetadata.json \
	    --exp-time 300 \
	    --workdir /path/to/working/directory \
	    --verbose
```

## Output Format

The output JSON file contains:

- Exploitation status (success/failure)
- Used beepseed path
- CP name
- Sinkpoint coordinate
- Working directory used for the exploitation
- Fuzzing ID
- Path to results JSON file (if available)

## Testing

```bash
python -m unittest test/test_llm.py
python -m unittest test.test_llm.TestLLMClient.test_basic_completion
```
