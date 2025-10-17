from libDeepGen.executor.exec_direct_call import DirectCallExec
from libDeepGen.executor.exec_inprocess import InProcessExec
import os # Added for path manipulation


# Define arguments for each run (example)
script_filename = 'seeds_generator.txt' # Or 'sample_script.py' if using that
script_dir = os.path.dirname(__file__) # Get directory of the current example script
script_to_run = os.path.join(script_dir, "data", script_filename)
script_content = open(script_to_run, 'r').read()

try:
    executor = InProcessExec(script_content=script_content) 

    total_time = 0
    for i in range(10000):
        res = executor.exec(verbose=True)
        total_time += res.exec_time
    print(f"[InProcessExec] total time for 10000 runs: {total_time}")
    print(f"Rate: {10000 / total_time} seeds/second")
    
    input("Press Enter to continue the DirectCallExec...")

    executor = DirectCallExec(script_content=script_content) 
    total_time = 0
    for i in range(10000):
        res = executor.exec(verbose=True)
        total_time += res.exec_time
    print(f"[DirectCallExec] total time for 10000 runs: {total_time}")
    print(f"Rate: {10000 / total_time} seeds/second")
    # clean up seeds directory after execution
    import shutil
    if os.path.exists('seeds'):
        shutil.rmtree('seeds')
except Exception as e:
    print(f"Error: {e}")