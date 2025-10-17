#!/usr/bin/env python3

import userspace_code_browser
import concurrent.futures
import subprocess
import time

# Query given an already created client connection
def query_from_client_obj(client):
    try:
        res = client.get_function_cross_references("aout_volume_New", False)
    except Exception as e:
        print(e)

# Standalone function which creates connection and queries
def query_standalone():
    try:
        res = userspace_code_browser.get_function_cross_references("aout_volume_New", False)
    except Exception as e:
        print(e)

# Execute the CLI binary
def query_from_binary():
    res = subprocess.run(["code-browser", "-c", "xref", "aout_volume_New"], capture_output=True)

# Create a client object
client = userspace_code_browser.CodeBrowser()

start_time = time.perf_counter()

NTHREADS = 100

# Query with existing client concurrently
with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = [executor.submit(query_from_client_obj, client) for _ in range(NTHREADS)]
    concurrent.futures.wait(futures)
query_from_client_obj_time = time.perf_counter()

# Query with standalone connections concurrently
with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = [executor.submit(query_standalone) for _ in range(NTHREADS)]
    concurrent.futures.wait(futures)
query_standalone_time = time.perf_counter()

# Query by executing the binary concurrently
with concurrent.futures.ProcessPoolExecutor() as executor:
    futures = [executor.submit(query_from_binary) for _ in range(NTHREADS)]
    concurrent.futures.wait(futures)
query_from_binary_time = time.perf_counter()

# Print the time taken for each query method
print(f"query_from_client_obj: {query_from_client_obj_time - start_time}")
print(f"query_standalone:      {query_standalone_time - query_from_client_obj_time}")
print(f"query_from_binary:     {query_from_binary_time - query_standalone_time}")
