import argparse
import logging
from pathlib import Path
from jazzer_llm import llm_python_runner
from jazzer_llm.llm_invoker_loop import run_llm_invoker_loop
from jazzer_llm.stuck_reason import class_path_seperator


parser = argparse.ArgumentParser(
    description="javac and java must be present on the PATH"
)
parser.add_argument("-cp", "--cp", required=True, help="Classpath for the java program")
parser.add_argument(
    "--target_class",
    required=True,
    help="Fully qualified class name of the fuzzing target class",
)
parser.add_argument(
    "--source-directory",
    required=True,
    help="Directory containing source code of the project",
)
parser.add_argument(
    "--jazzer-directory",
    required=True,
    help="Working directory used for the jazzer fuzzer",
)

parser.add_argument('--use-docker', action=argparse.BooleanOptionalAction,
    default=True)
parser.add_argument(
    "--stuck-wait-time", type=int, default=5*60,
    help="The number of seconds to wait for jazzer to be considered stuck")
parser.add_argument(
    "--debug", default=False, action='store_true',
    help="Enable debug logging"
)
args, _ = parser.parse_known_args()

try:
    from libCRS.otel import install_otel_logger
    install_otel_logger(action_name="crs-java:llmfuzzaug")
except:
    pass

# Optionally enable debug logging.
if args.debug:
    logging.basicConfig(
        format='%(asctime)s %(levelname)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.DEBUG,
    )
    # Disable verbose logging for inotify
    logging.getLogger('watchdog.observers.inotify_buffer').setLevel(logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable docker if asked for...
if not args.use_docker:
    llm_python_runner.USE_DOCKER = False

# Covert classpath into absolutes so we don't have to worry about their relative
# locations.
class_path = []
for cp_dir in args.cp.split(":"):
    class_path.append(str(Path(cp_dir).resolve()))
class_path = class_path_seperator.join(class_path)

source_directory = Path(args.source_directory)
if not source_directory.is_dir():
    logging.warning("Source directory %s is not a directory", source_directory)

jazzer_directory = Path(args.jazzer_directory)
if not jazzer_directory.is_dir():
    logging.warning("Jazzer directory %s is not a directory", jazzer_directory)

run_llm_invoker_loop(
    class_path=class_path,
    target_class=args.target_class,
    source_directory=source_directory,
    jazzer_directory=jazzer_directory,
    stuck_wait_time=args.stuck_wait_time,
)
