# Tests for DirectCallExecutor
from libDeepGen.executor.exec_direct_call import DirectCallExec


def test_script_content_direct():
    test_script = """
def gen_one_seed():
    return b"Hello, World!"
"""
    result = DirectCallExec(script_content=test_script).exec(verbose=True)
    assert result is not None
    assert result.result == b"Hello, World!"
    assert result.exec_time is not None

def test_non_verbose_direct():
    test_script = """
def gen_one_seed():
    return b"Hello, World!"
"""
    result = DirectCallExec(script_content=test_script).exec(verbose=False)
    assert result is not None
    assert result.result == b"Hello, World!"
    assert result.exec_time is None

def test_missing_gen_one_seed_function_direct():
    test_script = """
# Script with no gen_one_seed function
x = 42
"""
    import pytest
    with pytest.raises(NameError) as excinfo:
        DirectCallExec(script_content=test_script).exec(verbose=True)
    
    assert "Function 'gen_one_seed' not found in script" in str(excinfo.value)