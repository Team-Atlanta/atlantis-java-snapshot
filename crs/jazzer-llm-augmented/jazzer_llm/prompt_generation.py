import binascii
import fnmatch
import logging
import os
import random
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass
from jazzer_llm.stuck_reason import StuckExecutionTrace, ExecutionFrame, StackTrace

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser, Tree, Node

logger = logging.getLogger(__name__)

JAVA_LANGUAGE = Language(tsjava.language())
java_parser = Parser(JAVA_LANGUAGE)


class PromptGenerator:
    SOURCE_FILE_GLOB_PATTERN = "*.java"

    def __init__(self, source_directory: Path):
        self.source_directory = source_directory
        self.cached_tree_sitter_trees = {}
        self.find_all_source_files()

    def get_prompt_from_execution_trace(self, corpus: bytes, trace: StuckExecutionTrace, extra_instructions='') -> str:
        # Firstly get the fuzzing harness, the part of the trace that has the
        # fuzzerTestOneInput method in it.
        fuzzing_harness_frame = None
        for frame in reversed(trace.stuckCandidateTrace.frames):
            if frame.methodName == "fuzzerTestOneInput":
                fuzzing_harness_frame = frame

        if fuzzing_harness_frame is None:
            raise ValueError("Could not find fuzzerTestOneInput in trace")
        harness_chunk = self.get_chunk_of_file_for_first_frames(fuzzing_harness_frame)
        
        # If this was caused by an exception, always use the stuckCandidateTrace
        # frames, otherwise, we use a heuristic to weigh our leaf functions and
        # see which ones are the best.
        exception_chunk = ""
        if trace.candidateFromException:
            frame_chunk = self.get_frame_chunk_based_on_trace(trace)
            if trace.exceptionMessage:
                exception_chunk = "Due to this exception " + trace.exceptionMessage[:256] + "\n"
                exception_chunk += self.get_stack_trace_as_string(trace.stuckCandidateTrace)[:512]
                exception_chunk += '\n'
            logging.info("[stuck reason] Based on exception, so picking exception causing method.")
        else:
            weights, nodes = self.weigh_leaf_nodes(trace)
            if sum(weights) <= 0:
                frame_chunk = self.get_frame_chunk_based_on_trace(trace)
                logger.info("[stuck reason] All leaf nodes weight to 0, using trace.")
            else:
                node = random.choices(nodes, weights)[0]
                frame_chunk = self.get_chunk_of_file_for_last_frames(node)
                logger.info("[stuck reason] Used leaf node selection heuristic and picked %s.%s",
                    node.qualifiedClassName, node.methodName)

        # Limit the corpus sample to only 256 bytes.
        corpus_sample = corpus[:256].hex()
        if len(corpus) > 256:
            corpus_sample += "..."

        prompt = f"""\
We are trying to explore all the code paths in a Java program. The entrypoint of
the program is the following:

```
{harness_chunk}
```

The byte array parameter passed in was 0x{corpus_sample}
Execution is stuck in this method:

{frame_chunk}
{exception_chunk}
"""
        if not extra_instructions:
            prompt += f"""\
We need to generate new input for the entrypoint that causes execution to go
further in this method. Think about what the program is doing and what input it
accepts. Do not make assumptions on where to perform your transformation,
find it carefully with knowledge of the format. Use sophisticated approaches,
parsing the input again if needed and comment why your transformation would make
the input progress further.

Respond with just a python script with a function called generate_example
that takes a single parameter input of type bytes and transforms it, returning
bytes. The output should be a valid Python code file with no extra text.
"""
        else:
            prompt += extra_instructions
        return prompt.replace("\r\n", "\n")  # Normalize newlines when returning.

    def get_frame_chunk_based_on_trace(self, trace: StuckExecutionTrace) -> str:
        # Frames are in order of deepest, so just get the first one that works.
        for frame in trace.stuckCandidateTrace.frames:
            frame_chunk = self.get_chunk_of_file_for_last_frames(frame)
            if frame_chunk is not None:
                return frame_chunk
        raise ValueError("Could not find source code for a single frame in trace")

    def weigh_leaf_nodes(self, trace: StuckExecutionTrace) -> tuple[List[int], List[ExecutionFrame]]:
        """
        Takes all the leaf nodes from an execution trace and weighs them to
        figure out which ones are acting as obstacles to fuzzing.
        """
        weights = []
        nodes = []
        for frame in trace.leafFunctions:
            weights.append(self._weigh_leaf_node(frame))
            nodes.append(frame)
        return weights, nodes

    IF_STATEMENT_QUERY =  JAVA_LANGUAGE.query("(if_statement)")
    METHOD_CALL_QUERY = JAVA_LANGUAGE.query("(method_invocation)")

    def _weigh_leaf_node(self, frame: ExecutionFrame) -> int:
        tree = self.get_parsed_tree_for_file(frame.sourceFileName)
        if tree is None:
            logging.info("Could not find file for frame function %s", frame.sourceFileName)
            return 0

        file_contents = self.get_file_source_code(frame.sourceFileName)
        function = get_function_from_tree(tree, file_contents, frame.methodName, frame.lineNumber)
        if function is None:
            logging.info("Could not find function for frame function %s in %s", frame.methodName, frame.sourceFileName)
            return 0

        base_score = 1
        # Add 2 for each if.
        if_statements = self.IF_STATEMENT_QUERY.matches(function.method_declaration)
        base_score += (2 * len(if_statements))
        # Add 1 for each function call.
        method_calls = self.METHOD_CALL_QUERY.matches(function.method_declaration)
        base_score += (1 * len(method_calls))

        # Constructors are boring, reduce their weight.
        if frame.methodName == "<init>" or frame.methodName == "<clinit>":
            base_score /= 3

        return base_score

    def find_all_source_files(self):
        """Computes the paths to all the source files.

        For example (TraceeWithException.java) -> (src/a/b/c/d/TraceeWithException.java)
        """
        self.source_map = {}
        for root, dirs, files in os.walk(self.source_directory, followlinks=True):
            for file in files:
                if fnmatch.fnmatch(file, self.SOURCE_FILE_GLOB_PATTERN):
                    path = Path(root) / file
                    self.source_map[file] = path

    def get_file_source_code(self, file_name: str) -> Optional[bytes]:
        if file_name not in self.source_map:
            return None
        return self.source_map[file_name].read_bytes()

    def get_parsed_tree_for_file(self, file_name: str) -> Optional[Tree]:
        if file_name in self.cached_tree_sitter_trees:
            return self.cached_tree_sitter_trees[file_name]

        contents = self.get_file_source_code(file_name)
        if contents is None:
            return None
        
        tree = java_parser.parse(contents)
        self.cached_tree_sitter_trees[file_name] = tree
        return tree
    
    # Chunk here means a chunk for the llm prompt.
    def get_chunk_of_file_for_last_frames(self, frame: ExecutionFrame) -> Optional[str]:
        """Get a chunk of method from an execution trace for the last few frames.
        
        Since this is usually deep within application code, we only want the
        specific method if source code is available.
        """
        method_body = self._get_method_body(frame.sourceFileName, frame.methodName, frame.lineNumber)
        return f"{frame.qualifiedClassName}.{frame.methodName}:\n```\n{method_body}\n```"
            

    def _get_method_body(self, file_name: str, method_name: str, line: int) -> Optional[str]:
        """Get the body of a method from a particular java file."""
        tree = self.get_parsed_tree_for_file(file_name)
        if tree is None:
            logging.info("Could not find file for frame function %s", file_name)
            return None

        file_contents = self.get_file_source_code(file_name)
        function = get_function_from_tree(tree, file_contents, method_name, line)
        return function.body
    
    def get_chunk_of_file_for_first_frames(self, frame: ExecutionFrame) -> Optional[str]:
        """Get the imports and the chunk of method. This is vital contextual
        information for the first few frames, the fuzzing harness.
        """
        file_contents = self.get_file_source_code(frame.sourceFileName).decode()
        return file_contents

    def get_stack_trace_as_string(self, trace: StackTrace) -> str:
        stack_trace = []
        for frame in trace.frames:
            if frame.methodName == "fuzzerTestOneInput":
                break
            stack_trace.append(
                f"  at {frame.qualifiedClassName}.{frame.methodName}({frame.sourceFileName}:{frame.lineNumber})"
            )
        return '\n'.join(stack_trace)


@dataclass
class JavaFunction:
    identifier: str
    body: str
    method_declaration: Tree


java_function_query = JAVA_LANGUAGE.query("""\
(method_declaration
  name: (identifier) @method.identifier)
""")

java_constructor_query = JAVA_LANGUAGE.query("""\
(constructor_declaration) @constructor
""")


def node_to_source(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode()

def get_all_functions_from_tree(tree: Tree, source: str):
    matches = java_function_query.matches(tree.root_node)

    for match in matches:
        identifier = match[1]["method.identifier"][0]
        full_method = identifier.parent

        yield JavaFunction(identifier=node_to_source(identifier, source),
                           body=node_to_source(full_method, source),
                           method_declaration=full_method)

def get_constructor_from_tree(tree: Tree, source: str, line: int) -> Optional[JavaFunction]:
    matches = java_constructor_query.matches(tree.root_node)
    for match in matches:
        constructor = match[1]["constructor"][0]
        if line != -1 and (constructor.start_point.row + 1) > line:
            continue
        if line != -1 and (constructor.end_point.row + 1) < line:
            continue

        return JavaFunction(identifier="<init>",
            body=node_to_source(constructor, source), method_declaration=constructor)

def get_function_from_tree(tree: Tree, source: str, method_name: str, line: int) -> Optional[JavaFunction]:
    if method_name == "<init>":
        return get_constructor_from_tree(tree, source, line)

    for method in get_all_functions_from_tree(tree, source):
        if method.identifier != method_name:
            continue
        # Check if it's in the line range.
        if line != -1 and (method.method_declaration.start_point.row + 1) > line:
            continue
        if line != -1 and (method.method_declaration.end_point.row + 1) < line:
            continue
        return method
