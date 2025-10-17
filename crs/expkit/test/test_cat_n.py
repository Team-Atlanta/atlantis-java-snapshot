#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from expkit.sinkpoint_beep.pyshellcmd import cat_n  # noqa: E402


class TestCatN(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        # Keep track of temporary files for cleanup
        self.temp_files = []

    def tearDown(self):
        """Clean up test environment."""
        # Delete the temporary files
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except (OSError, FileNotFoundError):
                pass

    def create_temp_file(self, content):
        """Create a temporary file with the given content."""
        # Use delete=False so the file isn't immediately deleted when closed
        temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()  # Close so it can be reopened by the function

        # Keep the path to delete it in tearDown
        self.temp_files.append(temp_file.name)
        return temp_file.name

    def test_single_line_file(self):
        """Test cat_n with a file containing a single line."""
        test_content = "This is a single line test file"
        file_path = self.create_temp_file(test_content)

        result = cat_n(file_path)
        separator = "-" * 80
        print(f"\ncat_n of single line file:\n{separator}")
        print(result)
        print(separator)

        expected = "     1\tThis is a single line test file"
        self.assertEqual(result, expected)

    def test_empty_file(self):
        """Test cat_n with an empty file."""
        file_path = self.create_temp_file("")

        result = cat_n(file_path)
        separator = "-" * 80
        print(f"\ncat_n of empty file:\n{separator}")
        print(result)
        print(separator)

        # An empty file would result in an empty string
        self.assertEqual(result, "")

    def test_nonexistent_file(self):
        """Test cat_n with a non-existent file."""
        nonexistent_path = "/this/file/does/not/exist.txt"

        result = cat_n(nonexistent_path)
        separator = "-" * 80
        print(f"\ncat_n of nonexistent file:\n{separator}")
        print(result)
        print(separator)

        self.assertTrue("No such file or directory" in result)

    def test_multiple_lines_file(self):
        """Test cat_n with a file containing multiple lines."""
        test_content = "Line 1\nLine 2\nLine 3"
        file_path = self.create_temp_file(test_content)

        result = cat_n(file_path)
        separator = "-" * 80
        print(f"\ncat_n of multiple lines file:\n{separator}")
        print(result)
        print(separator)

        expected = "     1\tLine 1\n     2\tLine 2\n     3\tLine 3"
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
