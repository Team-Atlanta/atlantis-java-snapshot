import pytest
from unittest import mock
import subprocess
import json
import tempfile
import time
import grpc
from code_browser_client import CodeBrowserClient

# NOTE need to run with PYTHONPATH=$(pwd)/code_browser_client:$PYTHONPATH pytest

# TODO fixture that initializes the server on VLC

@pytest.fixture(scope="session")
def code_browser_client():
    repo_url = 'https://code.videolan.org/videolan/vlc.git'
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(["git", "clone", "--depth", "1", repo_url, f'{tmp_dir}/vlc'], check=True)
        try:
            server_process = subprocess.Popen(["code-browser-server", f"{tmp_dir}/vlc"])
            for _ in range(60):
                try:
                    test_client = CodeBrowserClient()
                    break
                except grpc.RpcError:
                    time.sleep(1)

            yield test_client
        finally:
            server_process.terminate()
            server_process.wait()

def test_get_function_definitions(code_browser_client):
    response = code_browser_client.get_function_definition("aout_volume_New")
    defs = json.loads(response)
    print(response)
    assert len(defs) == 2
    assert defs[0]['name'] == 'aout_volume_New'
    assert defs[1]['name'] == 'aout_volume_New'
    assert defs[0]['def_type'] == 'FUNCTION'
    assert defs[1]['def_type'] == 'PREPROC'

def test_get_function_cross_references(code_browser_client):
    response = code_browser_client.get_function_cross_references("vlc_custom_create")
    defs = json.loads(response)
    print(response)
    assert len(defs) == 56
    for d in defs:
        assert 'vlc_custom_create' in d['references']

def test_get_struct_definitions(code_browser_client):
    name = "aout_volume"
    response = code_browser_client.get_struct_definition(name)
    defs = json.loads(response)
    print(response)
    assert len(defs) == 1
    assert defs[0]['name'] == name

def test_get_enum_definitions(code_browser_client):
    name = "filter_resizer_e"
    response = code_browser_client.get_enum_definition(name)
    defs = json.loads(response)
    print(response)
    assert len(defs) == 1
    assert defs[0]['name'] == name

def test_get_union_definitions(code_browser_client):
    name = "vlc_preparser_cbs"
    response = code_browser_client.get_union_definition(name)
    defs = json.loads(response)
    print(response)
    assert len(defs) == 1
    assert defs[0]['name'] == name

def test_get_typedef_definitions(code_browser_client):
    name = "aout_volume_t"
    response = code_browser_client.get_typedef_definition(name)
    defs = json.loads(response)
    print(response)
    assert len(defs) == 1
    assert defs[0]['name'] == name

def test_get_any_type_definitions(code_browser_client):
    name = "aout_volume_t"
    response = code_browser_client.get_any_type_definition(name)
    defs = json.loads(response)
    print(response)
    assert len(defs) == 1
    assert defs[0]['name'] == name
