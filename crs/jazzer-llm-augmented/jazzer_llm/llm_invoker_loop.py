from jazzer_llm import corpus_observer, stuck_reason, prompt_generation, llm_python_runner
from pathlib import Path
import logging
import time
import os
import random
import subprocess
import hashlib


logger = logging.getLogger(__name__)


# 1. Make the observer.
# 2. Check if coverage is stuck.
#   a. If not, sleep.
# 3. If coverage is stuck, select a random corpus item.
# 4. Run with coverage tracer to get where we are stuck and variable states.
# 5. Feed to LLM and generate new corpus.
# 6. Send back to fuzzer through corpus folder.
def run_llm_invoker_loop(
    class_path: str, target_class: str, source_directory: Path, jazzer_directory: Path,
    stuck_wait_time: int,
):
    # Create a working directory for ourselves
    work_directory = jazzer_directory / "jazzer-llm"
    work_directory.mkdir(exist_ok=True)

    stuck_reason.compile_fuzzer_runner(
        fuzzing_class=target_class, class_path=class_path, output_dir=work_directory
    )
    tracer_jar = stuck_reason.get_jar_program_execution_tracer_jar()

    prompt_generator = prompt_generation.PromptGenerator(source_directory=source_directory)

    corpus_dir = jazzer_directory / "corpus_dir"
    logger.info("Monitoring jazzer corpus directory: %s", corpus_dir)

    observer = corpus_observer.JazzerCorpusObserver(
        corpus_dir, time_between_entries=stuck_wait_time
    )
    with observer:
        i = 0
        total_time_slept = 0
        while True:
            # For the first time, always invoke.
            if i == 0:
                time.sleep(10)
                logger.info("Invoking initial LLM run")
            elif not observer.is_coverage_stuck():
                time.sleep(0.5)
                total_time_slept += 0.5
                continue

            total_time_slept = 0
            i += 1

            selected_corpus = observer.get_stuck_corpus()
            get_stuck_reason_and_invoke_llm(
                selected_corpus=selected_corpus, prompt_generator=prompt_generator,
                corpus_dir=corpus_dir, i=i, tracer_jar=tracer_jar,
                work_directory=work_directory, class_path=class_path
            )

            # Select additional corpora.
            additional_corpora = observer.get_random_corpora()
            for corpora in additional_corpora:
                get_stuck_reason_and_invoke_llm(
                    selected_corpus=corpora, prompt_generator=prompt_generator,
                    corpus_dir=corpus_dir, i=i, tracer_jar=tracer_jar,
                    work_directory=work_directory, class_path=class_path
                )

            observer.reset_stuck_coverage_time()


def get_stuck_reason_and_invoke_llm(
        selected_corpus: Path,
        prompt_generator: prompt_generation.PromptGenerator,
        corpus_dir: Path,
        i: int,
        tracer_jar, work_directory, class_path
    ):
    if selected_corpus is None:
        logger.critical("No corpus to base off from")
        return

    # Sometimes corpus files vanish, just try again in that case.
    try:
        corpus_bytes = selected_corpus.read_bytes()
    except FileNotFoundError:
        logging.info("Selected corpus disappeared")
        return

    logger.info("Coverage stuck, computing stuck reason with corpus: %s", selected_corpus)

    try:
        tracer_process = stuck_reason.run_program_execution_tracer(
            tracer_jar=tracer_jar,
            stub_location=work_directory,
            class_path=class_path,
            corpus=selected_corpus,
        )
    except subprocess.TimeoutExpired:
        logger.info("Stuck reason tracer timeout")
        return

    execution_trace = stuck_reason.parse_execution_trace(tracer_process.stdout)

    prompt_strategies = ['regular']
    if random.random() < 0.5:
        prompt_strategies.append('from_scratch')

    for prompt_strategy in prompt_strategies:
        # Use different prompting strategies.
        try:
            if prompt_strategy == 'from_scratch':
                prompt = prompt_from_scratch(prompt_generator, corpus_bytes, execution_trace)
            else:
                prompt = prompt_regular(prompt_generator, corpus_bytes, execution_trace)
        except ValueError:
            logger.exception("Failed to generate prompt")
            return

        try:
            out_corpus_name = f"jazzer-llm-corpus-{i}-{prompt_strategy}"
            prompt_llm_prompt_and_write_output(prompt, corpus_bytes, corpus_dir, out_corpus_name)
        except Exception:
            logger.exception("Failed to prompt llm or write output")
            return

def prompt_regular(prompt_generator, corpus_bytes, execution_trace):
    return prompt_generator.get_prompt_from_execution_trace(corpus=corpus_bytes, trace=execution_trace)

def prompt_from_scratch(prompt_generator, corpus_bytes, execution_trace):
    return prompt_generator.get_prompt_from_execution_trace(
        corpus=corpus_bytes, trace=execution_trace,
        extra_instructions="""\
We need to generate new input for the entrypoint that causes execution to go
further in this method. Think about what the program is doing and what input it
accepts.

Respond with just a python script with a function called generate_example
that ignores a single parameter input. It should return bytes.
The output should be a valid Python code file with no extra text.
""")


def prompt_llm_prompt_and_write_output(prompt, corpus_bytes, corpus_dir, out_corpus_name):
    logging.info("Prompt: %s", prompt)
    mutation_code = prompt_llm(prompt)

    logging.info("Code: %s", mutation_code)
    logging.info("Running code provided by LLM...")

    output_bytes = llm_python_runner.run_generate_example_function_with_retry(
        code=mutation_code, input_bytes=corpus_bytes)
    if output_bytes is None:
        logging.error("LLM code failed in all chances, skipping")
    else:
        out_corpus_name += "-" + sha1_hash_of_bytes(output_bytes)

        logging.info(f"New corpus: {output_bytes}")
        new_corpus_file = corpus_dir / out_corpus_name
        new_corpus_file.write_bytes(output_bytes)

def sha1_hash_of_bytes(input_bytes: bytes) -> str:
    return hashlib.sha1(input_bytes).hexdigest()


MODEL = 'o1-mini'
total_tokens = 0
total_cost = 0

# Fallback to asking user to get LLM responses if LITELLM_KEY is not present.
if 'LITELLM_KEY' in os.environ:

    import libllm.openai as openai
    import libllm.instructor as instructor
    from pydantic import BaseModel, Field

    INPUT_COST_PER_TOKEN = 2.5e-06
    OUTPUT_COST_PER_TOKEN = 1e-05

    client = instructor.from_openai(
        openai.OpenAI(api_key=os.environ["LITELLM_KEY"],
                      base_url=os.environ["AIXCC_LITELLM_HOSTNAME"]),
        mode=instructor.Mode.JSON
    )

    class MutationCode(BaseModel):
        code: str = Field(description='Python code to mutate the input')

    def prompt_llm(prompt):
        global total_cost, total_tokens

        messages = [{"role": "user", "content": prompt}]
        response, completion = client.chat.completions.create_with_completion(
            max_tokens=4096,
            model=MODEL,
            messages=messages,
            temperature=0.4,
            response_model=MutationCode,
        )

        usage = completion.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens += usage.total_tokens

        total_cost += (
            prompt_tokens * INPUT_COST_PER_TOKEN +
            completion_tokens * OUTPUT_COST_PER_TOKEN
        )

        logger.info(f"Total cost: ${total_cost:.6f} for {total_tokens} tokens (this time query {usage.total_tokens}: {prompt_tokens}/{completion_tokens} in/out)")

        return response.code

else:

    def prompt_llm(prompt):
        print("Enter/Paste response from LLM below. Ctrl-D or Ctrl-Z ( windows ) to save it.")
        contents = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            contents.append(line)

        return '\n'.join(contents)
