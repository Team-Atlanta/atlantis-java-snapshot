#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from expkit.beepobjs import BeepSeed  # noqa: E402
from expkit.cpmeta import CPMetadata  # noqa: E402
from expkit.sinkpoint_beep.prompt import PromptGenerator  # noqa: E402


class TestStackTraceParsing(unittest.TestCase):
    def setUp(self):
        test_beepseed_str = """
{
  "mark_id": 2,
  "data_sha1": "f367243c7a5384b55ec1089662a1ad2736be867c",
  "data": "0a021010101010100d0000260000021000",
  "coordinate": {
    "class_name": "org/apache/activemq/openwire/OpenWireFormat",
    "method_name": "setVersion",
    "method_desc": "(I)V",
    "bytecode_offset": 16,
    "mark_desc": "sink-UnsafeReflectiveCall",
    "file_name": "OpenWireFormat.java",
    "line_num": 345
  },
  "stack_hash": "17297787391307745178",
  "stack_trace": [
    {
      "class_name": "com.code_intelligence.jazzer.runtime.JazzerInternal",
      "method_name": "lambda$reportCodeMarkerHit$0",
      "file_name": "JazzerInternal.java",
      "line_num": 43,
      "frame_str": "com.code_intelligence.jazzer.runtime.JazzerInternal.lambda$reportCodeMarkerHit$0(JazzerInternal.java:43)"
    },
    {
      "class_name": "java.util.concurrent.ConcurrentHashMap",
      "method_name": "computeIfAbsent",
      "file_name": "ConcurrentHashMap.java",
      "line_num": 1708,
      "frame_str": "java.base/java.util.concurrent.ConcurrentHashMap.computeIfAbsent(ConcurrentHashMap.java:1708)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.runtime.JazzerInternal",
      "method_name": "reportCodeMarkerHit",
      "file_name": "JazzerInternal.java",
      "line_num": 43,
      "frame_str": "com.code_intelligence.jazzer.runtime.JazzerInternal.reportCodeMarkerHit(JazzerInternal.java:43)"
    },
    {
      "class_name": "jdk.internal.reflect.NativeMethodAccessorImpl",
      "method_name": "invoke0",
      "file_name": "NativeMethodAccessorImpl.java",
      "line_num": -2,
      "frame_str": "java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke0(Native Method)"
    },
    {
      "class_name": "jdk.internal.reflect.NativeMethodAccessorImpl",
      "method_name": "invoke",
      "file_name": "NativeMethodAccessorImpl.java",
      "line_num": 77,
      "frame_str": "java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:77)"
    },
    {
      "class_name": "jdk.internal.reflect.DelegatingMethodAccessorImpl",
      "method_name": "invoke",
      "file_name": "DelegatingMethodAccessorImpl.java",
      "line_num": 43,
      "frame_str": "java.base/jdk.internal.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)"
    },
    {
      "class_name": "java.lang.reflect.Method",
      "method_name": "invoke",
      "file_name": "Method.java",
      "line_num": 568,
      "frame_str": "java.base/java.lang.reflect.Method.invoke(Method.java:568)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.api.Jazzer",
      "method_name": "reportCodeMarkerHit",
      "file_name": "Jazzer.java",
      "line_num": 229,
      "frame_str": "com.code_intelligence.jazzer.api.Jazzer.reportCodeMarkerHit(Jazzer.java:229)"
    },
    {
      "class_name": "org.apache.activemq.openwire.OpenWireFormat",
      "method_name": "setVersion",
      "file_name": "OpenWireFormat.java",
      "line_num": 345,
      "frame_str": "org.apache.activemq.openwire.OpenWireFormat.setVersion(OpenWireFormat.java:345)"
    },
    {
      "class_name": "org.apache.activemq.openwire.OpenWireFormat",
      "method_name": "<init>",
      "file_name": "OpenWireFormat.java",
      "line_num": 76,
      "frame_str": "org.apache.activemq.openwire.OpenWireFormat.<init>(OpenWireFormat.java:76)"
    },
    {
      "class_name": "org.apache.activemq.openwire.OpenWireFormat",
      "method_name": "<init>",
      "file_name": "OpenWireFormat.java",
      "line_num": 72,
      "frame_str": "org.apache.activemq.openwire.OpenWireFormat.<init>(OpenWireFormat.java:72)"
    },
    {
      "class_name": "com.aixcc.activemq.harnesses.one.ActivemqOne",
      "method_name": "fuzzerTestOneInput",
      "file_name": "ActivemqOne.java",
      "line_num": 27,
      "frame_str": "com.aixcc.activemq.harnesses.one.ActivemqOne.fuzzerTestOneInput(ActivemqOne.java:27)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.driver.FuzzTargetRunner",
      "method_name": "runOne",
      "file_name": "FuzzTargetRunner.java",
      "line_num": 247,
      "frame_str": "com.code_intelligence.jazzer.driver.FuzzTargetRunner.runOne(FuzzTargetRunner.java:247)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.runtime.FuzzTargetRunnerNatives",
      "method_name": "startLibFuzzer",
      "file_name": "FuzzTargetRunnerNatives.java",
      "line_num": -2,
      "frame_str": "com.code_intelligence.jazzer.runtime.FuzzTargetRunnerNatives.startLibFuzzer(Native Method)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.driver.FuzzTargetRunner",
      "method_name": "startLibFuzzer",
      "file_name": "FuzzTargetRunner.java",
      "line_num": 590,
      "frame_str": "com.code_intelligence.jazzer.driver.FuzzTargetRunner.startLibFuzzer(FuzzTargetRunner.java:590)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.driver.FuzzTargetRunner",
      "method_name": "startLibFuzzer",
      "file_name": "FuzzTargetRunner.java",
      "line_num": 480,
      "frame_str": "com.code_intelligence.jazzer.driver.FuzzTargetRunner.startLibFuzzer(FuzzTargetRunner.java:480)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.driver.Driver",
      "method_name": "start",
      "file_name": "Driver.java",
      "line_num": 174,
      "frame_str": "com.code_intelligence.jazzer.driver.Driver.start(Driver.java:174)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.Jazzer",
      "method_name": "start",
      "file_name": "Jazzer.java",
      "line_num": 118,
      "frame_str": "com.code_intelligence.jazzer.Jazzer.start(Jazzer.java:118)"
    },
    {
      "class_name": "com.code_intelligence.jazzer.Jazzer",
      "method_name": "main",
      "file_name": "Jazzer.java",
      "line_num": 77,
      "frame_str": "com.code_intelligence.jazzer.Jazzer.main(Jazzer.java:77)"
    }
  ]
}
"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=True) as temp_file:
            temp_file.write(test_beepseed_str.encode("utf-8"))
            temp_path = temp_file.name

            self.beepseed = BeepSeed.frm_beep_file(temp_path)

            with tempfile.NamedTemporaryFile(suffix=".json", delete=True) as meta_file:
                meta_path = meta_file.name
                with open(meta_path, "w") as f:
                    f.write('{"cp_name": "test-cp"}')

                self.cp_meta = CPMetadata(meta_path)
                self.prompt_generator = PromptGenerator(self.cp_meta, self.beepseed)

    def test_stacktrace_filtering(self):
        """Test that the stack trace is correctly filtered"""
        filtered_trace = self.prompt_generator.get_beepseed_stacktrace()

        self.assertTrue(
            filtered_trace.startswith(
                "== Stacktrace when the given input reaches the sinkpoint:"
            )
        )

        self.assertNotIn(
            "com.code_intelligence.jazzer.api.Jazzer.reportCodeMarkerHit(Jazzer.java:229)",
            filtered_trace,
        )

        self.assertIn(
            "at org.apache.activemq.openwire.OpenWireFormat.setVersion", filtered_trace
        )
        self.assertIn(
            "at org.apache.activemq.openwire.OpenWireFormat.<init>", filtered_trace
        )
        self.assertIn(
            "at com.aixcc.activemq.harnesses.one.ActivemqOne.fuzzerTestOneInput",
            filtered_trace,
        )

        expected_frames = 11
        actual_frames = filtered_trace.count("at ")
        self.assertEqual(
            expected_frames,
            actual_frames,
            f"Expected {expected_frames} frames, got {actual_frames}. Filtered trace: {filtered_trace}",
        )

        print("Filtered trace:")
        print(filtered_trace)


if __name__ == "__main__":
    unittest.main()
