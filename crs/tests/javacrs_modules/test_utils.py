#!/usr/bin/env python3

import os
import sys
import asyncio
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from javacrs_modules.utils import stream_load_json


class TestStreamLoadJson(unittest.TestCase):
    def setUp(self):
        self.resources_dir = Path(__file__).parent / "resources"
        self.test_json_path = self.resources_dir / "test-util-input.json"
        self.log_messages = []
        self.logger = lambda msg: self.log_messages.append(msg)

    def test_stream_load_json_file_not_found(self):
        non_existent_file = Path("/non/existent/file.json")
        result = asyncio.run(self._collect_items(non_existent_file, "some.path"))
        
        self.assertEqual(len(result), 0)
        self.assertTrue(any("JSON file not found" in msg for msg in self.log_messages))
    
    def test_stream_load_json_log_dedup_crash(self):
        result = asyncio.run(self._collect_items(self.test_json_path, "fuzz_data.log_dedup_crash_over_time"))
        
        self.assertEqual(len(result), 1)
        
        crash_array = result[0]
        self.assertEqual(len(crash_array), 9)
        
        # Examine the first crash in the array
        first_crash = crash_array[0]
        self.assertEqual(len(first_crash), 6)
        self.assertEqual(first_crash[0], 67)
        self.assertEqual(first_crash[1], "FuzzerSecurityIssueCritical: Script Engine Injection")
        self.assertIn("Script Engine Injection", first_crash[2])
        self.assertIsInstance(first_crash[3], list)
        self.assertEqual(first_crash[4], "dc783964d5f21ada")
        self.assertEqual(first_crash[5], "crash-b1e1f82111475b7062be5dca0888d136ddd500d9")

    def test_stream_load_json_invalid_field(self):
        result = asyncio.run(self._collect_items(self.test_json_path, "nonexistent.field"))
        self.assertEqual(len(result), 0)
    
    def test_stream_load_json_invalid_json(self):
        invalid_json_path = self.resources_dir / "invalid.json"
        with open(invalid_json_path, 'w') as f:
            f.write("{ this is not valid JSON }")
        
        try:
            result = asyncio.run(self._collect_items(invalid_json_path, "some.field"))
            self.assertEqual(len(result), 0)
            self.assertTrue(any("Error streaming JSON" in msg for msg in self.log_messages))
        finally:
            if invalid_json_path.exists():
                os.unlink(invalid_json_path)
    
    async def _collect_items(self, file_path, field_path):
        items = []
        async for item in stream_load_json(file_path, field_path, self.logger):
            items.append(item)
        return items


if __name__ == "__main__":
    unittest.main()