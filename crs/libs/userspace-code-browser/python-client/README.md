# Python Client

Installing this package provides `code_browser_client.CodeBrowserClient`
```
pip3 install .
```

There's a provided sample `run.py` on how to use the client. This includes:
- setting up the CodeBrowserClient with optional address parameter
- usage of all the get_* methods
- common errors
  - RpcError: error from gRPC / protobuf construction
  - CodeBrowserError: error from the server logic
```
# gets the function definition of aout_volume_New
python3 run.py function aout_volume_New 
```
