import argparse
from pathlib import Path
# from flask import Flask, jsonify
from service import GraalService


parser = argparse.ArgumentParser(description="graal-concolic server")
parser.add_argument(
    "--work-dir", required=True, help="working dir for the concolic execution"
)
parser.add_argument(
    "--input-corpus-dir",
    required=True,
    help="corpus dir for the candidates for running concolic execution",
)
parser.add_argument(
    "--output-corpus-dir",
    required=True,
    help="corpus dir for the output blobs as results of concolic execution",
)
parser.add_argument(
    "--coverage-seed-dir",
    required=False,
    default='/',
    help="corpus dir for fuzzer coverage checking",
)
parser.add_argument(
    "--harness",
    required=True,
    help="target harness id",
)
parser.add_argument(
    "--cp-metadata",
    required=True,
    help="cp metadata file path",
)
parser.add_argument(
    "--executor-dir",
    required=False,
    help="(option) executor dir for concolic execution",
    default=Path(__file__).resolve().parent.parent.absolute(),
)
parser.add_argument(
    "--timeout",
    required=False,
    help="(option) timeout (default: 0 -- follow crs-java.config)",
    default=1200,
)
parser.add_argument(
    "--cpu-list",
    required=False,
    help="(option) timeout (default: 0-15)",
    default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15",
)
parser.add_argument(
    "--shared-cores",
    required=False,
    help="(option) timeout (default: "" (empty-string as no shared cores))",
    default="",
)
parser.add_argument(
    "--max-xms",
    required=False,
    help="(option) timeout (default: 0 -- follow crs-java.config)",
    default=8192,
)
parser.add_argument(
    "--max-mem",
    required=False,
    help="(option) timeout (default: 0 -- follow crs-java.config)",
    default=16384,
)
parser.add_argument(
    "--max-concurrency",
    required=False,
    help="(option) timeout (default: 0 -- follow crs-java.config)",
    default=1,
)

parser.add_argument(
    "--port",
    required=False,
    help="(option) port (default: 5005)",
    default=5005,
)
parser.add_argument(
    "--do-execution",
    required=False,
    action="store_true",
    help="(option) do-execution without flask",
    default=False,
)

parser.add_argument(
    "--disable-cgroup",
    required=False,
    action="store_true",
    help="(optional) disable cgroup resource jail (for testing)",
    default=False,
)

parser.add_argument(
    "--debug-logging",
    required=False,
    action="store_true",
    help="(optional) enable after jit logging for concolic executor",
    default=False,
)



args = parser.parse_args()

WORK_DIR = args.work_dir
INPUT_DIR = args.input_corpus_dir
OUTPUT_DIR = args.output_corpus_dir
COVERAGE_DIR = args.coverage_seed_dir
EXECUTOR_DIR = args.executor_dir
HARNESS_ID = args.harness
TIMEOUT = int(args.timeout)
PORT = int(args.port)
CP_METADATA = args.cp_metadata
CPU_LIST = args.cpu_list
SHARED_CORES = args.shared_cores
MAX_XMS = int(args.max_xms)
MAX_MEM = int(args.max_mem)
MAX_CONCURRENCY = int(args.max_concurrency)
DISABLE_CGROUP = args.disable_cgroup
DEBUG_LOGGING = args.debug_logging

class GraalServiceWithScheduler(GraalService):
    def __init__(self, *args, **kwargs):
        self.scheduler_path = Path(__file__).resolve().parent.parent.parent / "scheduler" / "scripts" / "seed_eval_service.py"

        # TODO: port should be reassigned before integration
        self.scheduler_port = PORT + 10000

        self.scheduler_base_dir = (Path(INPUT_DIR).parent / "seed_eval_service").resolve()
        super().__init__(*args, **kwargs)
        return

# app = Flask(__name__)
# service = GraalService(
service = GraalServiceWithScheduler(
    Path(WORK_DIR),
    Path(INPUT_DIR),
    Path(OUTPUT_DIR),
    Path(COVERAGE_DIR),
    HARNESS_ID,
    Path(CP_METADATA),
    TIMEOUT,
    CPU_LIST,
    SHARED_CORES,
    MAX_XMS,
    MAX_MEM,
    MAX_CONCURRENCY,
    PORT,
    DISABLE_CGROUP,
    DEBUG_LOGGING,
    Path(EXECUTOR_DIR)
)

"""
@app.route("/execution", methods=["GET"])
def execute_command():
    try:
        service.do_execution()
        result = "/execution was executed successfully."
        return jsonify({"status": "success", "result": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
"""

if __name__ == "__main__":
    ###########################################
    #### Execute the Graal Service
    #### NOTE: It will wait for the execution to finish.
    ###########################################
    #if args.do_execution:
    service.do_execution()
    #else:
    #    app.run(port=PORT, debug=True)
