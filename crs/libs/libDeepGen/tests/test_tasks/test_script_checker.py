import pytest
from libDeepGen.tasks import ScriptChecker


@pytest.mark.asyncio
async def test_script_checker_fixes_runtime_errors():
    """Test that ScriptChecker can fix scripts with runtime errors using a real LLM."""
    
    # Create a script with runtime errors:
    # 1. NameError: 'random' is not defined
    # 2. TypeError: returns string instead of bytes
    # 3. AttributeError: trying to use undefined methods
    erroneous_script = """
def gen_one_seed():
    # Generate a random seed value
    seed_num = random.randint(1000, 9999)  # NameError: random not imported
    
    # Try to create some structure
    header = "FUZZ"
    body = str(seed_num)
    
    # This will cause TypeError when returned (should be bytes)
    return header + body
"""

    # Create ScriptChecker with a real model
    checker = ScriptChecker(
        model="gpt-4.1",  # Using real model as requested
        script_content=erroneous_script,
        max_iter=3  # Allow up to 3 iterations to fix the script
    )
    
    # Run the checker
    fixed_script = await checker.check()
    
    # Verify that a fixed script was returned
    assert fixed_script is not None, "ScriptChecker should have fixed the script"
    
    # Verify the fixed script contains necessary elements
    assert "import" in fixed_script, "Fixed script should include necessary imports"
    assert "def gen_one_seed()" in fixed_script, "Fixed script should have gen_one_seed function"
    assert "return" in fixed_script, "Fixed script should have a return statement"
    
    # Verify the fixed script actually works by executing it
    from libDeepGen.executor import InProcessExec
    
    try:
        executor = InProcessExec(script_content=fixed_script)
        
        # Run multiple times to ensure it works consistently
        results = []
        for i in range(5):
            result = executor.exec()
            
            # Check that execution was successful
            assert result.success, f"Fixed script should execute successfully on run {i+1}. Error: {result.error}"
            
            # Check that it returns bytes
            assert result.result is not None, "gen_one_seed should return a value"
            assert isinstance(result.result, bytes), \
                f"gen_one_seed should return bytes, got {type(result.result)}"
            
            results.append(result.result)
        
        # Verify that it generates different seeds (not all the same)
        unique_results = set(results)
        assert len(unique_results) > 1, "gen_one_seed should generate different seeds on each call"
            
    except Exception as e:
        pytest.fail(f"Fixed script failed to execute properly: {e}")
    
    print(f"Original script:\n{erroneous_script}")
    print(f"\nFixed script:\n{fixed_script}")
    print(f"\nGenerated seeds (first 3): {results[:3]}")


@pytest.mark.asyncio
async def test_script_checker_fixes_complex_runtime_error():
    """Test ScriptChecker with a more complex runtime error scenario."""
    
    # Script with multiple runtime issues:
    # 1. Missing imports (os, struct)
    # 2. FileNotFoundError: trying to read non-existent file
    # 3. Wrong data types and conversions
    complex_erroneous_script = """
def gen_one_seed():
    # Try to read from a template file that doesn't exist
    with open('template.bin', 'rb') as f:
        template = f.read()
    
    # Use struct without importing it
    seed_id = struct.pack('>I', os.getpid())
    
    # Concatenate without proper type handling
    result = template + seed_id + str(time.time())
    
    return result
"""
    
    checker = ScriptChecker(
        model="gpt-4.1",
        script_content=complex_erroneous_script,
        max_iter=4  # May need more iterations for complex errors
    )
    
    fixed_script = await checker.check()
    
    assert fixed_script is not None, "Should fix complex runtime errors"
    
    # Test the fixed script
    from libDeepGen.executor import InProcessExec
    
    executor = InProcessExec(script_content=fixed_script)
    result = executor.exec()
    
    assert result.success, f"Fixed script should run without errors: {result.error}"
    assert isinstance(result.result, bytes), "Should return bytes"
    assert len(result.result) > 0, "Should return non-empty bytes"
    
    print(f"\nComplex script fixed successfully!")
    print(f"Sample output: {result.result[:50]}...")  # Show first 50 bytes