from libDeepGen.executor.exec_inprocess import InProcessExec


def test_script_content():
    test_script = """
def gen_one_seed():
    return b"Hello, World!"
"""
    executor = InProcessExec(script_content=test_script)
    result = executor.exec(verbose=True)
    assert result is not None
    assert result.result == b"Hello, World!"
    assert result.exec_time is not None

def test_non_verbose():
    test_script = """
def gen_one_seed():
    return b"Hello, World!"
"""
    executor = InProcessExec(script_content=test_script)
    result = executor.exec(verbose=False)
    assert result is not None
    assert result.result == b"Hello, World!"
    assert result.exec_time is None

def test_missing_gen_one_seed_function():
    test_script = """
# Script with no gen_one_seed function
x = 42
"""
    import pytest
    with pytest.raises(NameError) as excinfo:
        executor = InProcessExec(script_content=test_script)
        executor.exec(verbose=True)
    
    assert "Function 'gen_one_seed' not found in script" in str(excinfo.value)

