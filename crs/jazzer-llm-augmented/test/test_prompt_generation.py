from jazzer_llm import prompt_generation
from jazzer_llm.stuck_reason import ExecutionFrame, StackTrace, StuckExecutionTrace
from pathlib import Path

import pytest


@pytest.fixture
def test_project(tmp_path):
    src_file_1 = tmp_path / 'src' / 'com' / 'test' / 'Foo.java'
    src_file_2 = tmp_path / 'src' / 'org' / 'apache' / 'Bar.java'

    src_file_1.parent.mkdir(parents=True)
    src_file_1.write_text("""\
package com.test;

class Foo {
    public Foo() {
        System.out.println("Hello!");
    }

    public void foo_method(String x) {
        return x + "foo";
    }

    public void twoBranches(int x, int y) {
        if (x < 2 && y > 2) {}
        if (x > 1 && y > 1) {}
    }

    public void oneCall() {
        foo_method("x");
    }
}
""")
    src_file_2.parent.mkdir(parents=True)
    src_file_2.write_text("""\
package org.apache;

import java.io.IOException;
import org.apache.bcel.classfile.ClassParser;

class Bar {
    public static void fuzzerTestOneInput(byte[] input) throws Exception {
        foo_method(new String(input));
    }
}
""")
    return tmp_path


def test_prompt_generator_throws_exception_when_no_fuzzerTestOneInput(test_project):
    trace = StuckExecutionTrace(stuckCandidateTrace=StackTrace(
        frames=[
            ExecutionFrame(sourceFileName="Foo.java", lineNumber=1, methodName="inner", qualifiedClassName="Foo"),
            ExecutionFrame(sourceFileName="Foo.java", lineNumber=5, methodName="outer", qualifiedClassName="Foo"),
        ]),
        candidateFromException=False,
        leafFunctions=[],
    )
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    with pytest.raises(ValueError) as e:
        generator.get_prompt_from_execution_trace(corpus=b"", trace=trace)
    assert "Could not find fuzzerTestOneInput" in str(e)


def test_prompt_generator_weighs_leaf_nodes_correctly(test_project):
    trace = StuckExecutionTrace(
        stuckCandidateTrace=StackTrace(frames=[]),
        candidateFromException=False,
        leafFunctions=[
            ExecutionFrame(sourceFileName="Foo.java", lineNumber=13, methodName="twoBranches", qualifiedClassName="Foo"),
            ExecutionFrame(sourceFileName="Foo.java", lineNumber=18, methodName="oneCall", qualifiedClassName="Foo"),
        ]
    )

    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    weights, nodes = generator.weigh_leaf_nodes(trace)

    assert len(weights) == 2
    assert weights[0] == 5
    assert weights[1] == 2


def test_prompt_generator_makes_correct_prompt(test_project):
    trace = StuckExecutionTrace(stuckCandidateTrace=StackTrace(
        frames=[
                ExecutionFrame(sourceFileName="Foo.java", lineNumber=9, methodName="foo_method", qualifiedClassName="Foo"),
                ExecutionFrame(sourceFileName="Bar.java", lineNumber=8, methodName="fuzzerTestOneInput", qualifiedClassName="Foo"),
                ExecutionFrame(sourceFileName="StuckReasonFuzzerRunner.java", lineNumber=5, methodName="main", qualifiedClassName="StuckReasonFuzzerRunner"),
            ]
        ),
        candidateFromException=True,
        leafFunctions=[],
    )
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    prompt = generator.get_prompt_from_execution_trace(corpus=b"hi", trace=trace)
    assert prompt == """\
We are trying to explore all the code paths in a Java program. The entrypoint of
the program is the following:

```
package org.apache;

import java.io.IOException;
import org.apache.bcel.classfile.ClassParser;

class Bar {
    public static void fuzzerTestOneInput(byte[] input) throws Exception {
        foo_method(new String(input));
    }
}

```

The byte array parameter passed in was 0x6869
Execution is stuck in this method:

Foo.foo_method:
```
public void foo_method(String x) {
        return x + "foo";
    }
```

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

def test_prompt_generator_makes_correct_prompt_with_exception(test_project):
    trace = StuckExecutionTrace(stuckCandidateTrace=StackTrace(
        frames=[
                ExecutionFrame(sourceFileName="Bar.java", lineNumber=8, methodName="fuzzerTestOneInput", qualifiedClassName="Foo"),
                ExecutionFrame(sourceFileName="StuckReasonFuzzerRunner.java", lineNumber=5, methodName="main", qualifiedClassName="StuckReasonFuzzerRunner"),
            ]
        ),
        exceptionMessage="IllegalArgumentException (index out of bounds)",
        candidateFromException=True,
        leafFunctions=[],
    )
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    prompt = generator.get_prompt_from_execution_trace(corpus=b"hi", trace=trace)

    assert 'Due to this exception' in prompt
    assert 'IllegalArgumentException (index out of bounds)' in prompt

def test_prompt_generator_makes_correct_source_map(test_project):
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    assert generator.source_map['Foo.java'].name == 'Foo.java'
    assert generator.source_map['Bar.java'].name == 'Bar.java'


def test_prompt_generator_can_parse_source(test_project):
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    tree = generator.get_parsed_tree_for_file('Foo.java')

    assert tree is not None

def test_function_retrieval_for_source(test_project):
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    tree = generator.get_parsed_tree_for_file('Foo.java')
    source = generator.get_file_source_code('Foo.java')

    functions = list(prompt_generation.get_all_functions_from_tree(tree, source=source))

    foo = functions[0]
    assert foo.identifier == "foo_method"
    assert 'public void foo_method(String x) {' in foo.body
    assert 'return x + "foo"' in foo.body
    assert '}' in foo.body

def test_function_retrieval_for_constructor(test_project):
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    tree = generator.get_parsed_tree_for_file('Foo.java')
    source = generator.get_file_source_code('Foo.java')

    function = prompt_generation.get_function_from_tree(tree, source, '<init>', line=5)
    assert function.identifier == '<init>'
    assert 'public Foo() {' in function.body
    assert '    System.out.println("Hello!");' in function.body
    assert '}' in function.body

def test_get_chunk_for_last_frames(test_project):
    frame = ExecutionFrame(sourceFileName="Foo.java", lineNumber=8,
                           methodName="foo_method", qualifiedClassName="com.test.Foo")
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    chunk = generator.get_chunk_of_file_for_last_frames(frame=frame)

    assert 'public void foo_method(String x) {' in chunk
    assert 'return x + "foo"' in chunk
    assert '}' in chunk

def test_get_chunk_for_first_frames(test_project):
    frame = ExecutionFrame(sourceFileName="Bar.java", lineNumber=8, qualifiedClassName="org.apache.Bar",
                           methodName="fuzzerTestOneInput")
    generator = prompt_generation.PromptGenerator(source_directory=test_project)
    chunk = generator.get_chunk_of_file_for_first_frames(frame=frame)

    lines = chunk.splitlines()
    assert len(lines) == 10
    assert chunk == """\
package org.apache;

import java.io.IOException;
import org.apache.bcel.classfile.ClassParser;

class Bar {
    public static void fuzzerTestOneInput(byte[] input) throws Exception {
        foo_method(new String(input));
    }
}
"""
