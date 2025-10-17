import os

import pytest
from coordinates.inspector import BytecodeInspector


@pytest.fixture
def bytecode_jar_path():
    """Fixture that provides the path to the bytecode parser JAR file."""
    # Get the directory of the current script (tests/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to get to the project root
    project_root = os.path.dirname(script_dir)
    # Path to the bytecode-parser JAR - use the one that's already compiled
    jar_path = os.path.join(
        project_root,
        "bytecode-parser",
        "target",
        "bytecode-parser-1.0-SNAPSHOT-jar-with-dependencies.jar",
    )

    # Make sure the JAR exists
    if not os.path.exists(jar_path):
        pytest.skip(f"Bytecode parser JAR not found at {jar_path}")
    return jar_path


def test_bytecode_inspector_initialization():
    """Test that the BytecodeInspector initializes correctly."""
    inspector = BytecodeInspector()
    assert inspector is not None
    assert os.path.exists(inspector.jar_path)


def test_handle_default_package():
    """Test handling of default package names."""
    inspector = BytecodeInspector()

    # Test with empty string (should convert to "<default>")
    result = inspector._handle_default_package([""])
    assert "<default>" in result

    # Test with a mix of empty strings and regular packages
    result = inspector._handle_default_package(["", "com.example", "org.test", ""])
    assert "<default>" in result
    assert "com.example" in result
    assert "org.test" in result
    assert len(result) == 3  # No duplicates

    # Test with no empty strings
    result = inspector._handle_default_package(["com.example", "org.test"])
    assert "<default>" not in result
    assert "com.example" in result
    assert "org.test" in result


def test_query_coordinates(bytecode_jar_path, tmp_path):
    """Test querying for source coordinates."""
    # Create a temporary jar for testing
    test_jar = os.path.join(tmp_path, "test.jar")

    # Copy the bytecode-parser JAR to our test location for testing
    import shutil

    shutil.copy(bytecode_jar_path, test_jar)

    # Initialize the inspector with our test jar
    inspector = BytecodeInspector()
    inspector.init_mapping(pkg_list=["<default>"], cp_list=[test_jar])

    # Query for coordinates in BytecodeInspector class (which should exist in the test jar)
    # Note: We now need to use class name, not source file name
    # The full class name should be "BytecodeInspector" (or the actual fully qualified name)
    coordinates = inspector.query("BytecodeInspector", 128)

    # Check if we got any coordinates
    assert coordinates is not None, "No coordinates returned"

    # Verify the structure of the coordinates
    assert hasattr(coordinates, "jar_file")
    assert hasattr(coordinates, "class_file_path")
    assert hasattr(coordinates, "class_name")
    assert hasattr(coordinates, "file_name")
    assert hasattr(coordinates, "method_name")
    assert hasattr(coordinates, "method_desc")
    assert hasattr(coordinates, "bytecode_offset")
    assert hasattr(coordinates, "line_number")


def test_query_coordinates_with_empty_pkg(bytecode_jar_path, tmp_path):
    """Test querying for source coordinates with empty package string."""
    # Create a temporary jar for testing
    test_jar = os.path.join(tmp_path, "test.jar")

    # Copy the bytecode-parser JAR to test location
    import shutil

    shutil.copy(bytecode_jar_path, test_jar)

    # Initialize with empty string (should be converted to "<default>")
    inspector = BytecodeInspector()
    inspector.init_mapping(pkg_list=[""], cp_list=[test_jar])

    # Query for coordinates in BytecodeInspector class
    coordinates = inspector.query("BytecodeInspector", 128)

    # Check if we got any coordinates
    assert coordinates is not None, "No coordinates returned"


def test_nonexistent_query():
    """Test querying for coordinates that don't exist."""
    inspector = BytecodeInspector()
    # Don't initialize with any jars

    # Query for coordinates that don't exist
    coordinate = inspector.query("NonExistentClass", 1)
    assert coordinate is None, "Expected None for non-existent coordinates"
