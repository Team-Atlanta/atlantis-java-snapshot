import sys

def trace_calls(frame, event, arg):
    if event == 'call':
        code = frame.f_code
        func_name = code.co_name
        func_filename = code.co_filename
        func_lineno = frame.f_lineno
        print(f"Calling {func_name} in {func_filename} at line {func_lineno}")
    return trace_calls

sys.settrace(trace_calls)
