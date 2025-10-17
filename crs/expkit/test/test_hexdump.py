#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from expkit.beepobjs import BeepSeed  # noqa: E402
from expkit.cpmeta import CPMetadata  # noqa: E402
from expkit.sinkpoint_beep.prompt import PromptGenerator  # noqa: E402


class TestHexdump(unittest.TestCase):
    def create_beepseed_json(self, hex_data):
        """Create a JSON string for a beepseed with the given hex data."""
        beepseed_dict = {
            "mark_id": 2,
            "data_sha1": "f367243c7a5384b55ec1089662a1ad2736be867c",
            "data": hex_data,
            "coordinate": {
                "class_name": "org.test.TestClass",
                "method_name": "testMethod",
                "method_desc": "()V",
                "bytecode_offset": 42,
                "mark_desc": "TEST_SINK",
                "file_name": "TestClass.java",
                "line_num": 123,
            },
            "stack_hash": "17297787391307745178",
            "stack_trace": [
                {
                    "class_name": "com.code_intelligence.jazzer.api.Jazzer",
                    "method_name": "reportCodeMarkerHit",
                    "file_name": "Jazzer.java",
                    "line_num": 229,
                    "frame_str": "com.code_intelligence.jazzer.api.Jazzer.reportCodeMarkerHit(Jazzer.java:229)",
                },
                {
                    "class_name": "org.test.TestClass",
                    "method_name": "testMethod",
                    "file_name": "TestClass.java",
                    "line_num": 123,
                    "frame_str": "org.test.TestClass.testMethod(TestClass.java:123)",
                },
            ],
        }
        return json.dumps(beepseed_dict, indent=2)

    def setUp(self):
        """Set up test environment."""
        # Keep track of temporary files for cleanup
        self.temp_files = []

    def tearDown(self):
        """Clean up test environment."""
        # Close all temporary files
        for temp_file in self.temp_files:
            temp_file.close()

    def setup_prompt_generator(self, hex_data):
        """Set up a PromptGenerator with the given hex data."""
        beepseed_str = self.create_beepseed_json(hex_data)

        # Create temporary files
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=True)
        temp_file.write(beepseed_str.encode("utf-8"))
        temp_file.flush()  # Ensure data is written to disk
        self.temp_files.append(temp_file)

        beepseed = BeepSeed.frm_beep_file(temp_file.name)

        meta_file = tempfile.NamedTemporaryFile(suffix=".json", delete=True)
        meta_file.write(b'{"cp_name": "test-cp"}')
        meta_file.flush()
        self.temp_files.append(meta_file)

        cp_meta = CPMetadata(meta_file.name)
        prompt_gen = PromptGenerator(cp_meta, beepseed)

        return prompt_gen

    def create_indexed_bytes(self, length):
        """Create bytes where each byte value equals its index (modulo 256)."""
        return bytes(i % 256 for i in range(length))

    def test_hexdump_0_bytes(self):
        """Test hexdump formatting with 0 bytes."""
        data = self.create_indexed_bytes(0)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        print("\nHexdump of 0 bytes:")
        print(hexdump_output)

        # The current implementation returns ""Zero-length data" for empty hex strings
        expected_output = """Zero-length data"""

        self.assertEqual(hexdump_output, expected_output)

    def test_hexdump_1_byte(self):
        """Test hexdump formatting with 1 byte."""
        data = self.create_indexed_bytes(1)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        print("\nHexdump of 1 byte:")
        print(hexdump_output)

        # Capture the actual spacing in the output
        expected_output = """00000000  00  |.|
00000001"""

        self.assertEqual(hexdump_output, expected_output)

    def test_hexdump_8_bytes(self):
        """Test hexdump formatting with 8 bytes."""
        data = self.create_indexed_bytes(8)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        print("\nHexdump of 8 bytes:")
        print(hexdump_output)

        expected_output = """00000000  00 01 02 03 04 05 06 07  |........|
00000008"""

        self.assertEqual(hexdump_output, expected_output)

    def test_hexdump_9_bytes(self):
        """Test hexdump formatting with 9 bytes."""
        data = self.create_indexed_bytes(9)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        print("\nHexdump of 9 bytes:")
        print(hexdump_output)

        expected_output = """00000000  00 01 02 03 04 05 06 07 08  |.........|
00000009"""

        self.assertEqual(hexdump_output, expected_output)

    def test_hexdump_16_bytes(self):
        """Test hexdump formatting with 16 bytes."""
        data = self.create_indexed_bytes(16)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        print("\nHexdump of 16 bytes:")
        print(hexdump_output)

        expected_output = """00000000  00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  |................|
00000010"""

        self.assertEqual(hexdump_output, expected_output)

    def test_hexdump_17_bytes(self):
        """Test hexdump formatting with 17 bytes."""
        data = self.create_indexed_bytes(17)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        print("\nHexdump of 17 bytes:")
        print(hexdump_output)

        expected_output = """00000000  00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  |................|
00000010  10  |.|
00000011"""

        self.assertEqual(hexdump_output, expected_output)

    def test_hexdump_32_bytes(self):
        """Test hexdump formatting with 32 bytes (2 lines)."""
        data = self.create_indexed_bytes(32)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        print("\nHexdump of 32 bytes:")
        print(hexdump_output)

        expected_output = """00000000  00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  |................|
00000010  10 11 12 13 14 15 16 17 18 19 1a 1b 1c 1d 1e 1f  |................|
00000020"""

        self.assertEqual(hexdump_output, expected_output)

    def test_hexdump_256_bytes(self):
        """Test hexdump formatting with 256 bytes (multiple lines)."""
        data = self.create_indexed_bytes(256)
        hex_data = data.hex()

        prompt_gen = self.setup_prompt_generator(hex_data)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        # Print the full output for manual inspection
        print("\nHexdump of 256 bytes:")
        print(hexdump_output)

        # Only check for the first and last few lines to avoid an excessively long test
        self.assertTrue(
            hexdump_output.startswith(
                "00000000  00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  |................|"
            )
        )
        self.assertTrue(
            "000000f0  f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 fa fb fc fd fe ff  |................|"
            in hexdump_output
        )
        self.assertTrue(hexdump_output.endswith("00000100"))

    def test_hexdump_empty_data(self):
        """Test that the hexdump handles empty data."""
        prompt_gen = self.setup_prompt_generator(None)
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        self.assertEqual(hexdump_output, "Zero-length data")

    def test_hexdump_invalid_hex(self):
        """Test that the hexdump handles invalid hex data."""
        prompt_gen = self.setup_prompt_generator("ZZZZ")  # Invalid hex characters
        hexdump_output = prompt_gen.get_beepseed_hexdump()

        self.assertTrue(hexdump_output.startswith("Error: Invalid hex string:"))


if __name__ == "__main__":
    unittest.main()
