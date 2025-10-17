from jazzer_llm.stuck_reason import (
    get_jar_program_execution_tracer_jar, compile_fuzzer_runner,
    parse_execution_trace
)
import pytest

from unittest.mock import patch


def test_get_jar_just_returns_jar_if_present(tmp_path):
    target_folder = tmp_path / 'target'
    target_folder.mkdir()

    jar_file = target_folder / 'ProgramExecutionTracer-1.0-SNAPSHOT-jar-with-dependencies.jar'
    jar_file.touch()

    returned_jar = get_jar_program_execution_tracer_jar(tracer_folder=tmp_path)
    assert returned_jar.name == jar_file.name


def test_get_jar_throws_if_not_present(tmp_path):
    with pytest.raises(ValueError) as e:
        get_jar_program_execution_tracer_jar(tracer_folder=tmp_path)

    assert 'ProgramExecutionTracer jar does not exist' in str(e)


def test_compiling_fuzzer_runner_invokes_javac(tmp_path):
    with patch("subprocess.check_call") as mock_check_call:
        compile_fuzzer_runner(
            fuzzing_class="com.aixcc.bcel.harnesses.one.BCELOne",
            class_path="/work/cp",
            output_dir=tmp_path)
                
        mock_check_call.assert_called_once_with(
            ["javac", "-cp", "/work/cp", "StuckReasonFuzzerRunner.java"],
            cwd=tmp_path
        )


def test_compiling_fuzzer_runner_throws_if_javac_fails(tmp_path):
    with patch("subprocess.check_call") as mock_check_call:
        mock_check_call.side_effect = FileNotFoundError("javac not found")
        with pytest.raises(FileNotFoundError) as e:
            compile_fuzzer_runner(
                fuzzing_class="com.aixcc.bcel.harnesses.one.BCELOne",
                class_path="/work/cp",
                output_dir=tmp_path)

        assert "javac not found" in str(e)


def test_parse_execution_trace_fails_when_no_end_frame():
    output = """\
Hello world
"""
    with pytest.raises(ValueError) as exc:
        parse_execution_trace(output)
    assert "Execution trace does not have stuck frame separator" in str(exc)


def test_parse_execution_trace_correctly_gets_frames():
    output = """\
Hello world!
==== Stuck Frame ====

{
  "stuckCandidateTrace": {
    "frames": [
      {
        "qualifiedClassName": "org.apache.bcel.classfile.ClassParser",
        "methodName": "readID",
        "sourceFileName": "ClassParser.java",
        "lineNumber": 249,
        "signature": "()V"
      },
      {
        "qualifiedClassName": "org.apache.bcel.classfile.ClassParser",
        "methodName": "parse",
        "sourceFileName": "ClassParser.java",
        "lineNumber": 127,
        "signature": "()Lorg/apache/bcel/classfile/JavaClass;"
      },
      {
        "qualifiedClassName": "org.apache.bcel.TestMain",
        "methodName": "fuzzerTestOneInput",
        "sourceFileName": "TestMain.java",
        "lineNumber": 48,
        "signature": "([B)V"
      },
      {
        "qualifiedClassName": "StuckReasonFuzzerRunner",
        "methodName": "main",
        "sourceFileName": "StuckReasonFuzzerRunner.java",
        "lineNumber": 11,
        "signature": "([Ljava/lang/String;)V"
      }
    ]
  },
  "candidateFromException": true,
  "leafFunctions": [
    {
      "qualifiedClassName": "org.apache.bcel.classfile.ClassParser",
      "methodName": "",
      "sourceFileName": "ClassParser.java",
      "lineNumber": 63,
      "signature": "(Ljava/io/InputStream;Ljava/lang/String;)V"
    },
    {
      "qualifiedClassName": "org.apache.bcel.classfile.ClassParser",
      "methodName": "readID",
      "sourceFileName": "ClassParser.java",
      "lineNumber": 249,
      "signature": "()V"
    },
    {
      "qualifiedClassName": "org.apache.bcel.TestMain",
      "methodName": "",
      "sourceFileName": "TestMain.java",
      "lineNumber": 37,
      "signature": "()V"
    }
  ]
}
"""
    trace = parse_execution_trace(output)
    trace = trace.stuckCandidateTrace
    assert trace.frames[0].methodName == "readID"
    assert trace.frames[0].qualifiedClassName == "org.apache.bcel.classfile.ClassParser"
    assert trace.frames[0].sourceFileName == "ClassParser.java"
    assert trace.frames[0].lineNumber == 249

    assert trace.frames[-1].methodName == "main"
    assert trace.frames[-1].qualifiedClassName == "StuckReasonFuzzerRunner"
    assert trace.frames[-1].sourceFileName == "StuckReasonFuzzerRunner.java"
    assert trace.frames[-1].lineNumber == 11
