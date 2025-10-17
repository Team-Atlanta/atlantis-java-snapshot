import base64
import glob
import json
import logging
import os
import queue
import shutil
import socketserver
import subprocess
import struct
import time
import traceback
import uuid

from os import makedirs, getenv, environ
from pathlib import Path

import threading
from threading import Thread, Lock, RLock
#from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

from wrapper import Wrapper
from libCRS.otel import install_otel_logger

threading.stack_size(0x4000000)
LOGGER = None
GRAAL_SERVICE = None

CRS_JAVA_ERR = 'CRS-JAVA-ERR-concolic '
CRS_JAVA_WARN = 'CRS-JAVA-WARN-concolic '

def delete_file(path):
    str_path = str(path)
    try:
        if os.path.exists(str_path):
            return os.unlink(str_path)
    except Exception as e:
        LOGGER.error(CRS_JAVA_ERR + f"Failed to delete {str_path}: {e}")

    return "DELETE_FILE_ERROR"

def set_file_logger(work_dir: Path, harness_id: str, root_logger: logging.Logger):
    log_path = work_dir / f"concolic-log-{harness_id}.log"
    file_handler = logging.FileHandler(str(log_path))
    file_handler.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)


def set_console_logger(root_logger: logging.Logger):
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)


def get_logger(work_dir: Path, harness_id: str ):
    logger = logging.getLogger(f"concolic_log_{harness_id}")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    set_file_logger(work_dir, harness_id, logger)
    install_otel_logger(action_name=f"crs-java:concolic-{harness_id}")

    return logger


class ConditionalSemaphore(object):
    def __init__(self, max_count):
        self._count = 0
        self._max_count = max_count
        self._lock = threading.Condition()

    @property
    def count(self):
        with self._lock:
            return self._count

    def acquire(self):
        with self._lock:
            while self._count >= self._max_count:
                self._lock.wait()
            self._count += 1

    def release(self):
        with self._lock:
            self._count -= 1
            self._lock.notify()

class CorpusManager(FileSystemEventHandler):
    def __init__(self):
        self.mutex = Lock()
        self.corpus_list = queue.Queue()
        self.thread_dict = {}
        self.corpus_dict = {}
        self.eid = 0

    def set_graal_service(self, graal_service):
        self.graal_service = graal_service

    def get_eid(self):
        eid = -1
        with self.mutex:
            self.eid += 1
            eid = self.eid
        return eid

    def add_to_thread_queue(self, t, eid):
        with self.mutex:
            self.thread_dict[eid] = t

    def remove_from_thread_queue(self, eid):
        with self.mutex:
            del self.thread_dict[eid]

    def add_to_list(self, filename):
        filename = str(filename)
        if filename in self.corpus_dict:
            LOGGER.info(f'File {filename} already processed 1')
            # remove the file
            corpus_path = Path(filename)
            if filename in GRAAL_SERVICE.processed_filename_dict:
                res = delete_file(corpus_path)
                LOGGER.info(f'Removing {corpus_path} {res}')
            #corpus_path.unlink(missing_ok=True)
            return
        self.corpus_dict[filename] = True
        length = 0
        self.corpus_list.put(filename)
        length = self.corpus_list.qsize()
        self.graal_service.logger.info(f'Added {filename}, length {length}')

    def get_filename_from_list(self):
        return self.corpus_list.get(block=True)

    # override FileSystemEventHandler; use on_created
    def on_created(self, event):
        new_file_path_str = event.src_path
        new_file_path = Path(new_file_path_str)
        # ignore hidden files
        if str(new_file_path.name).startswith('.'):
            return
        self.add_to_list(new_file_path_str)

    def on_create_forced(self, path):
        str_path = str(path)
        if not str_path in self.corpus_dict:
            # ignore hidden files
            if str_path.startswith('.'):
                pass
            else:
                self.add_to_list(str_path)
        else:
            if str_path in GRAAL_SERVICE.processed_filename_dict:
                GRAAL_SERVICE.logger.info(f'File {str_path} already processed 2')
                res = delete_file(str_path)
                GRAAL_SERVICE.logger.info(f'Removing {str_path} {res}')

    def process_corpus(self, corpus_path):
        corpus = None

        with open(corpus_path, "rb") as f:
            data = f.read().decode("utf-8")
            while True:
                try:
                    corpus = json.loads(data)
                    break
                except json.decoder.JSONDecodeError as e:
                    self.graal_service.logger.error(CRS_JAVA_ERR + f"Error decoding json: {e}")
                    # log first 128 bytes
                    self.graal_service.logger.error(CRS_JAVA_ERR + f"Path: {corpus_path}")
                    self.graal_service.logger.error(CRS_JAVA_ERR + f"Data: {repr(data[:128])}")

                    # fix json data
                    d = {}
                    d["blob"] = base64.b64encode(bytes(data, "utf-8")).decode("utf-8")
                    d["class_name"] = ""
                    d["method_name"] = ""
                    d["method_desc"] = ""
                    data = json.dumps(d)


            f.close()

        if corpus == None:
            return None

        if 'blob' not in corpus:
            return None

        blob_bytes = base64.b64decode(corpus['blob'])
        blob_fn_prefix = f"{GRAAL_SERVICE.blob_dir}/blob-{corpus_path.name}-{uuid.uuid4()}"

        self.graal_service.logger.info(f'Sending {corpus_path} as {blob_fn_prefix}')
        corpus['blob_fn_prefix'] = blob_fn_prefix
        corpus['rid'] = self.get_eid()

        with open(f"{blob_fn_prefix}.blob", "wb") as f:
            f.write(blob_bytes)
            f.close()

        with open(f"{blob_fn_prefix}.json", "w") as f:
            f.write(json.dumps(corpus))

        return corpus

# share across objects
CORPUS_MANAGER_INSTANCE = CorpusManager()

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def receive_sized_json(self):
        json_incoming_len_prefix = b''
        for i in range(4):
            json_incoming_len_prefix += self.request.recv(1)
        LOGGER.info('JSON LENGTH: ' + repr(json_incoming_len_prefix))
        json_incoming_len = struct.unpack('>I', json_incoming_len_prefix)[0]
        received = 0
        json_incoming = b''
        while received != json_incoming_len:
            recv_data = self.request.recv(json_incoming_len - received)
            json_incoming += recv_data
            received += len(recv_data)

        return json_incoming

    def handle(self):
        corpus_path = None
        try:
            header = self.request.recv(4)
            if header != b"SEED":
                LOGGER.info(f"Unknown request header from {self.client_address}: {header}")
                self.request.sendall(struct.pack('>I', 0))
                self.receive_sized_json()
                return

            LOGGER.info(f"Client {self.client_address} connected. Waiting for file...")

            while True:
                # might have duplicated files in the list
                filepath = CORPUS_MANAGER_INSTANCE.get_filename_from_list()
                corpus_path = Path(filepath)
                # fetch it until the file exists
                if corpus_path.exists():
                    file_size = 0
                    for i in range(2):
                        file_size = corpus_path.stat().st_size
                        if file_size != 0:
                            break
                        LOGGER.info(f"Retrying size 0 {corpus_path}")
                        time.sleep(0.3)

                    if file_size == 0:
                        LOGGER.info(f"File {corpus_path} size 0. skip it!")
                        self.request.sendall(struct.pack('>I', 0))
                        self.receive_sized_json()
                        GRAAL_SERVICE.processed_filename_dict[str(corpus_path)] = True
                        res = delete_file(corpus_path)
                        LOGGER.info(f"Deleting files {corpus_path} {res}")
                        #corpus_path.unlink(missing_ok=True)
                        return

                    break

                LOGGER.info(f"File {filepath} does not exist. skip it!")

            exception_triggered = False
            json_blob = None
            try:
                # get corpus json
                corpus_info_dict = CORPUS_MANAGER_INSTANCE.process_corpus(corpus_path)
                corpus_info_json = json.dumps(corpus_info_dict)
                json_blob = corpus_info_json.encode('utf-8')
                json_blob_len_prefix = struct.pack('>I', len(json_blob))

                # send
                self.request.sendall(json_blob_len_prefix)
                self.request.sendall(json_blob)

                # wait for the response
                json_incoming = self.receive_sized_json()
                json_incoming_dict = json.loads(json_incoming)

                log_dict = {}
                for key in json_incoming_dict:
                    if key != 'blob':
                        log_dict[key] = json_incoming_dict[key]
                    else:
                        log_dict['blob_size'] = len(json_incoming_dict[key])
                LOGGER.info(log_dict)
                res = delete_file(corpus_path)
                LOGGER.info(f"Deleting files {corpus_path} {res}")
                #corpus_path.unlink(missing_ok=True)
                #Path(f'{corpus_info_dict["blob_fn_prefix"]}.blob').unlink(missing_ok=True)
                res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.blob')
                LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.blob {res}')
                #Path(f'{corpus_info_dict["blob_fn_prefix"]}.json').unlink(missing_ok=True)
                res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.json')
                LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.json {res}')


            except Exception as e:
                LOGGER.error(CRS_JAVA_WARN + f"Error reading or sending file: {e}")
                stack_trace = traceback.format_exc()
                LOGGER.error(CRS_JAVA_WARN + f"[service.py] {stack_trace}")
                # send 0 size for the exception
                self.request.sendall(struct.pack('>I', 0))
                exception_triggered = True
            finally:
                if json_blob != None:
                    if exception_triggered:
                        (GRAAL_SERVICE.debug_exception_dir / corpus_path.name).write_bytes(json_blob)
                    else:
                        (GRAAL_SERVICE.debug_run_dir / corpus_path.name).write_bytes(json_blob)

                # delete the corpus file here
                #corpus_path.unlink(missing_ok=True)
                GRAAL_SERVICE.processed_filename_dict[str(corpus_path)] = True
                res = delete_file(corpus_path)
                LOGGER.info(f"Deleting files {corpus_path} {res}")
                #Path(f'{corpus_info_dict["blob_fn_prefix"]}.blob').unlink(missing_ok=True)
                res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.blob')
                LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.blob {res}')
                #Path(f'{corpus_info_dict["blob_fn_prefix"]}.json').unlink(missing_ok=True)
                res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.json')
                LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.json {res}')
                self.request.close()

        except Exception as e:
            LOGGER.error(CRS_JAVA_ERR + f"Connection error with {self.client_address}: {e}")
            stack_trace = traceback.format_exc()
            LOGGER.error(CRS_JAVA_ERR + f"[service.py] {stack_trace}")
            GRAAL_SERVICE.processed_filename_dict[str(corpus_path)] = True
            res = delete_file(corpus_path)
            LOGGER.info(f"Deleting files {corpus_path} {res}")
            res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.blob')
            LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.blob {res}')
            res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.json')
            LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.json {res}')
            self.request.close()
        finally:
            if corpus_path != None:
                GRAAL_SERVICE.processed_filename_dict[str(corpus_path)] = True
                res = delete_file(corpus_path)
                LOGGER.info(f"Deleting files {corpus_path} {res}")
                res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.blob')
                LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.blob {res}')
                res = delete_file(f'{corpus_info_dict["blob_fn_prefix"]}.json')
                LOGGER.info(f'Deleting files {corpus_info_dict["blob_fn_prefix"]}.json {res}')



class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class GraalService:
    def __init__(
        self,
        work_dir: Path,
        corpus_in_dir: Path,
        corpus_out_dir: Path,
        coverage_seed_dir: Path,
        harness_id: str,
        cp_metadata_path: str,
        timeout: int,
        cpu_list: str,
        shared_cpu_list: str,
        max_xms: int,
        max_mem: int,
        max_concurrency: int,
        port: int,
        disable_cgroup: bool,
        debug_logging: bool,
        executor_dir: Path = Path(__file__).resolve().parent.parent.absolute(),
    ):
        global LOGGER
        global GRAAL_SERVICE
        GRAAL_SERVICE = self
        self.debug_logging = debug_logging
        self.corpus_manager = CORPUS_MANAGER_INSTANCE
        self.corpus_manager.set_graal_service(self)
        self.processed_filename_dict = {}

        self.work_dir = work_dir.absolute()
        self.corpus_in_dir = corpus_in_dir.absolute()
        self.corpus_out_dir = corpus_out_dir.absolute()
        self.coverage_seed_dir = coverage_seed_dir.absolute()

        # create corpus debug dirs
        self.debug_dir = self.corpus_in_dir.parent / "debug-seeds"
        self.debug_exception_dir = self.debug_dir / "exceptions"
        self.debug_run_dir = self.debug_dir / "runs"
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        self.debug_exception_dir.mkdir(parents=True, exist_ok=True)
        self.debug_run_dir.mkdir(parents=True, exist_ok=True)
        self.blob_dir = self.corpus_in_dir.parent / "blobs"
        self.blob_dir.mkdir(parents=True, exist_ok=True)

        self.harness_id = harness_id
        self.cp_metadata_path = cp_metadata_path
        self.crs_config_path = Path(getenv("JAVA_CRS_SRC")) / 'crs-java.config'

        self.logger = get_logger(self.work_dir, self.harness_id)
        LOGGER = self.logger

        if not self.crs_config_path.exists():
            raise RuntimeError(f"CRS CONFIG file not found: {self.crs_config_path}")
        with self.crs_config_path.open("r") as f:
            self.crs_config = json.loads(f.read())

        self.concolic_config = self.crs_config['modules']['concolic']
        self.timeout = timeout

        # set mem/cpu limit
        self.max_xms = max_xms
        self.max_mem = max_mem
        self.max_concurrency = max_concurrency
        self._build_cpu_dict(cpu_list, shared_cpu_list) # set self.cpu_dict

        self.semaphore = ConditionalSemaphore(self.max_concurrency)
        system_java_home = os.getenv("JAVA_HOME")
        if ('GRAALVM_ESPRESSO' in system_java_home):
            self.java_home = system_java_home
        else:
            self.java_home = self._find_java_home('/graal-jdk/sdk/mxbuild/linux-amd64/')
        self.java_path = f"{self.java_home}/bin/java"
        self.java_opt = f"-Xmx{self.max_xms}m -Xms{self.max_xms}m"

        self.logger.info("======= Concolic Executor Config =======")
        self.logger.info(f"\tTimeout {self.timeout}")
        self.logger.info(f"\tMax java XMS memory {self.max_xms}MB")
        self.logger.info(f"\tMax cgroup memory {self.max_mem}MB")
        self.logger.info(f"\tMax concurrency {self.max_concurrency} processes")
        self.logger.info(f"Main CPU: {self.main_cpu}")
        self.logger.info(f"PRIVATE CPU LIST: {repr(self.cpu_list)}")
        self.logger.info(f"SHARED CPU LIST: {repr(self.shared_cpu_list)}")
        self.logger.info("CPU DICT:")
        self.logger.info(repr(self.cpu_dict))
        self.logger.info(f"JAVA_HOME: {self.java_home}")
        self.logger.info(f"JAVA_OPT: {self.java_opt}")
        self.logger.info(f"Executor dir: {executor_dir}")
        self.logger.info(f"Coverage seed dir: {self.coverage_seed_dir}")
        self.logger.info("============== Config End ==============")

        # load cp metadata
        if not self.cp_metadata_path.exists():
            raise RuntimeError(f"CP metadata file not found: {self.cp_metadata_path}")

        with self.cp_metadata_path.open("r") as f:
            self.cp_metadata = json.loads(f.read())

        # set runtime path information
        self.executor_dir = executor_dir
        self.wrapper_dir = self.work_dir / "wrappers"
        self.jazzer_jar_path = Path(__file__).absolute().parent.parent / "app" / "lib" / "jars" / "jazzer" / "jazzer_standalone.jar"
        self.unsafe_jar_path = Path(__file__).absolute().parent.parent / "app" / "lib" / "jars" / "jazzer" / "libunsafe_provider.jar"
        #self.objenesis_jar_path = Path(__file__).absolute().parent.parent / "app" / "lib" / "jars" / "objenesis-3.3.jar"
        self.app_path = Path(__file__).absolute().parent.parent / "app"
        self.app_jar_path = Path(__file__).absolute().parent.parent / "app" / "build" / "libs" / "app.jar"
        self.logger.info(f"jazzer jar path {self.jazzer_jar_path}")
        self.logger.info(f"libunsafe jar path {self.unsafe_jar_path}")
        #self.logger.info(f"Objenesis jar path {self.objenesis_jar_path}")
        makedirs(corpus_in_dir, exist_ok=True)
        makedirs(corpus_out_dir, exist_ok=True)
        makedirs(self.wrapper_dir, exist_ok=True)

        # setup harness and corpus manager
        self.setup_harness_and_corpus_manager()

        self.disable_cgroup = disable_cgroup
        # set cgroup
        if not self.disable_cgroup:
            self.create_cgroup()

        # set port
        self.port = port
        t = Thread(target=self.spawn_event_server)
        t.start()

        self.spawn_concolic_executor_service()

        self.spawn_scheduler_service()
        return

    def create_cgroup(self):
        self.cgroup_list = []
        max_mem_in_bytes = self.max_mem * 1024 * 1024
        for i in range(self.max_concurrency):
            group_name = f"concolic-cgroup-{self.harness_id}-{i}"
            # pin cpus
            #cpu_list = ','.join([str(x) for x in self.cpu_dict[i]])
            # do not pin cpus among executors
            cpu_list = ','.join([str(x) for x in self.cpu_list])    # this excludes the first cpu as main
            self.logger.info(f"node {i} : cpu {cpu_list}")
            os.system(f'cgcreate -g "memory,cpu:{group_name}"')
            makedirs(f"/sys/fs/cgroup/{group_name}", exist_ok=True)
            with open(f"/sys/fs/cgroup/{group_name}/memory.max", "w") as f:
                f.write(f"{max_mem_in_bytes}")
                f.close()
            with open(f"/sys/fs/cgroup/{group_name}/cpuset.cpus", "w") as f:
                f.write(cpu_list)
                f.close()
            self.cgroup_list.append(group_name)

    def _build_cpu_dict(self, cpu_list: str, shared_cpu_list: str):
        if cpu_list[0] == '"':
            cpu_list = cpu_list[1:]
        if cpu_list[-1] == '"':
            cpu_list = cpu_list[:-1]

        #s, e = [int(i) for i in cpu_list.split('-')]
        #self.cpu_list = [i for i in range(s, e+1, 1)]
        self.cpu_list = sorted([int(x) for x in cpu_list.split(',')])
        if len(shared_cpu_list) == 0:
            self.shared_cpu_list = []
        else:
            self.shared_cpu_list = sorted([int(x) for x in shared_cpu_list.split(',')])

        # don't have to reserve main cpu;
        # it will be running among 1 core from private/shared core well
        self.main_cpu = self.cpu_list[0]

        cpu_set_size = len(self.cpu_list) // self.max_concurrency
        self.cpu_dict = {}
        for i in range(self.max_concurrency):
            if (i+1) == self.max_concurrency:   # get all remaining cpus
                self.cpu_dict[i] = self.cpu_list[cpu_set_size*i:] + self.shared_cpu_list
            else:                               # get cpu_set_size cpus
                self.cpu_dict[i] = self.cpu_list[cpu_set_size*i:cpu_set_size*(i+1)] + self.shared_cpu_list

        self.cpu_set_queue = list(range(self.max_concurrency))
        self.mutex = Lock()

    def _find_java_home(self, base_dir: str):
        espresso = list(glob.glob(f'{base_dir}/GRAALVM_ESPRESSO*'))[0]
        java_home = list(glob.glob(f'{espresso}/*jvm-ce*'))[0]
        return java_home

    def get_cpu_set(self):
        with self.mutex:
            assert len(self.cpu_set_queue) > 0
            return self.cpu_set_queue.pop(0)

    def return_cpu_set(self, set_number):
        with self.mutex:
            assert not set_number in self.cpu_set_queue
            self.cpu_set_queue.append(set_number)

    def generate_wrapper(self, harness_info: dict, classpath: str, dst_dir: Path):
        if Wrapper.exists(dst_dir):
            return
        wrapper = Wrapper(harness_info, self.cp_metadata, self.logger)
        wrapper.generate(classpath, harness_info, dst_dir)

    def spawn_event_server(self):
        with ThreadedTCPServer(("0.0.0.0", self.port), ThreadedTCPRequestHandler) as server:
            LOGGER.info(f"Server listening on port {self.port}")
            server.serve_forever()

    def spawn_scheduler_service(self):
        if self.get_scheduler_path() is not None:
            t = Thread(target=self.run_scheduler_service)
            t.start()

    def run_scheduler_service(self):
        scheduler_path = self.get_scheduler_path()
        scheduler_port = self.get_scheduler_port()
        scheduler_base_dir = self.get_scheduler_base_dir()
        if scheduler_path is not None and scheduler_port is not None and scheduler_base_dir is not None:
            self.logger.info(f"Spawning scheduler service at {scheduler_path} with port {scheduler_port} and base dir {scheduler_base_dir}")
            try:
                subprocess.run(
                    ["python3", scheduler_path, "--port", str(scheduler_port), "--base-dir", str(scheduler_base_dir)],
                    cwd=str(self.executor_dir),
                    check=True,
                    env=environ.copy(),
                    stdout=subprocess.PIPE, # To avoid printing the output
                    stderr=subprocess.PIPE, # To avoid printing the output
                )
            except Exception as e:
                LOGGER.error(CRS_JAVA_ERR + f"[ERROR] Failed to spawn scheduler service: {e}")
                LOGGER.error(CRS_JAVA_ERR + f"{e}", exc_info=True)
                LOGGER.error(CRS_JAVA_ERR + f"{traceback.format_exc()}")

    def spawn_concolic_executor_service(self):
        for i in range(self.max_concurrency):
            t = Thread(target=self.run_concolic_executor_service, args=(i,))
            t.start()

    def run_concolic_executor_service(self, cpu_set_id):
        # loop for running executor service
        try:
            while True:
                self.run_executor_as_service(self.classpath, self.target_class, self.corpus_in_dir, self.corpus_out_dir, cpu_set_id, cpu_set_id)
                LOGGER.error(CRS_JAVA_ERR + f"Executor service for cpu_set_id {cpu_set_id} exited")

                # wait 3 seconds before re-spawning the executor
                time.sleep(3)
        except Exception as e:
            LOGGER.error(CRS_JAVA_ERR + f"[ERROR] {e}")
            LOGGER.error(traceback.format_exc())


    def run_execution_in_thread(self, corpus_filename, pid):
        corpus_path = Path(corpus_filename)
        corpus_info_dict = self.corpus_manager.process_corpus(corpus_path)
        blob_fn_prefix = corpus_info_dict['blob_fn_prefix']
        blob_info_json_fn = f"{blob_fn_prefix}.json"
        cpu_set_id = -1
        try:
            start = end = None
            try:
                self.semaphore.acquire()
                start = time.time()
                cpu_set_id = self.get_cpu_set()
                self.logger.info(f"Executing on {corpus_filename} with pid {pid} cpu_set_id {cpu_set_id}")
                self.run_executor(self.classpath, self.target_class, blob_info_json_fn, self.corpus_out_dir, cpu_set_id, pid)
            except subprocess.TimeoutExpired as e:
                self.logger.warn(CRS_JAVA_WARN + f"[TIMEOUT] pid {pid} cpu_set_id {cpu_set_id} corpus_path {corpus_path}")
                self.logger.warn(CRS_JAVA_WARN + f"{e}", exc_info=True)
            except Exception as e:
                self.logger.error(CRS_JAVA_ERR + f"[ERROR] pid {pid} cpu_set_id {cpu_set_id}, corpus_path {corpus_path}")
                self.logger.error(CRS_JAVA_ERR + f"{e}", exc_info=True)
                #traceback.print_exc()
            finally:
                # delete corpus files
                corpus_path.unlink(missing_ok=True)
                Path(f'{blob_fn_prefix}.blob').unlink(missing_ok=True)
                Path(f'{blob_fn_prefix}.json').unlink(missing_ok=True)
                self.semaphore.release()
                assert cpu_set_id != -1
                self.return_cpu_set(cpu_set_id)
                end = time.time()
                self.logger.info(f"Finished {corpus_filename} with pid {pid} cpu_set_id {cpu_set_id} in {end - start} seconds")
        except Exception as e:
            self.logger.error(CRS_JAVA_ERR + f"[ERROR] {e}")
            self.logger.error(CRS_JAVA_ERR + f"{e}", exc_info=True)
            #traceback.print_exc()

    def setup_harness_and_corpus_manager(self):
        harness_info = self.cp_metadata['harnesses'][self.harness_id]

        wrapper_harness_dir = self.wrapper_dir / self.harness_id
        classpath_array = harness_info['classpath']
        # jazzer jar path
        classpath_array.append(str(self.jazzer_jar_path))
        classpath_array.append(str(self.unsafe_jar_path))
        # objenesis jar path
        #classpath_array.append(str(self.objenesis_jar_path))
        # wrapper harness path
        classpath_array.append(str(wrapper_harness_dir))
        # executor app path
        classpath_array.append(str(self.app_path))

        self.classpath = ":".join(classpath_array)
        self.target_class = str(harness_info['target_class'])
        self.logger.info(f"Wrapper generation: skip")
        # self.generate_wrapper(harness_info, self.classpath, wrapper_harness_dir)

        # spawn a file list watchdog
        #self.observer = Observer()
        #self.observer = PollingObserver()
        #self.observer.schedule(self.corpus_manager, self.corpus_in_dir, recursive=False)
        #self.observer.start()

        # add all existing files to corpus_manager
        for corpus_file in self.corpus_in_dir.iterdir():
            if (corpus_file.is_file() and not corpus_file.name.startswith(".")):
                self.corpus_manager.add_to_list(corpus_file)

        self.logger.info(f"Registered corpus manager at {self.corpus_in_dir}")

    def input_dir_observer(self):
        try:
            files_list = list(glob.glob(f"{str(self.corpus_in_dir)}/*"))
            for corpus_fn in files_list:
                try:
                    p = Path(corpus_fn).resolve().absolute()
                    filename = str(p)
                    if filename in self.processed_filename_dict:
                        time.sleep(0.1)
                        res = delete_file(filename)
                        self.logger.info(f"File {filename} already processed, deleted {res} 3")
                    else:
                        CORPUS_MANAGER_INSTANCE.on_create_forced(p)
                except Exception as e:
                    self.logger.error(CRS_JAVA_ERR + f"[ERROR] {e}")
                    self.logger.error(traceback.format_exc())
        except Exception as e:
            self.logger.error(CRS_JAVA_ERR + f"[ERROR] {e}")
            self.logger.error(traceback.format_exc())

    def get_scheduler_port(self):
        if hasattr(self, "scheduler_port"):
            return self.scheduler_port
        return None

    def get_scheduler_base_dir(self):
        if hasattr(self, "scheduler_base_dir"):
            return self.scheduler_base_dir
        return None

    def get_scheduler_path(self):
        if hasattr(self, "scheduler_path"):
            return self.scheduler_path
        return None

    def do_execution(self):
        while True:
            self.input_dir_observer()
            time.sleep(1)


    def run_executor(
        self, classpath: str, classname: str, corpus_path: Path, out_path: Path, cpu_set_id, pid: int
    ):
        graal_env = {
            "JAVA_HOME": self.java_home,
            "JAVA_OPT": f'{self.java_opt}',
            "LD_DEBUG": "unused",
            # "LOG_LEVEL": "DEBUG",
        }

        env = environ.copy()
        env.update(graal_env)

        if not self.disable_cgroup:
            cgroup_name = self.cgroup_list[cpu_set_id]
            self.logger.info(f"pid {pid} cpu_set_id {cpu_set_id} running on cgroup {cgroup_name}")

            cmd = ["cgexec",
                "-g",
                f"memory,cpu:{self.cgroup_list[cpu_set_id]}",
                "--sticky"
                ]
        else:
            self.logger.info(f"pid {pid} cpu_set_id {cpu_set_id} running")
            cmd = []

        cmd += [
            str(self.java_path),
            f"-Xmx{self.max_xms}m",
            f"-Xms{self.max_xms}m",
            f"-jar",
            str(self.app_jar_path),
            "--concolic-classpath",
            f"{classpath}",
            "--concolic-target",
            f"{classname}",
            "--concolic-args",
            f"{corpus_path}",
            "--outdir",
            f"{out_path}",
            "--pid",
            f"{pid}",
            "--server",
            f"{self.port}"             # always runs as a server!
        ]

        scheduler_port = self.get_scheduler_port()
        if scheduler_port is not None:
            cmd += ["--scheduler-port", f"{scheduler_port}"]

        self.logger.info(f"{' '.join(cmd)}")

        try:
            subprocess.run(
                cmd,
                cwd=str(self.executor_dir),
                check=True,
                env=env,
                timeout=self.timeout,
                stderr=subprocess.PIPE,
                #stdout=subprocess.DEVNULL # give me output!
            )
        except subprocess.TimeoutExpired as e:
            self.logger.info(CRS_JAVA_WARN + f"[Timeout] Timeout: pid {pid} cpu_set_id {cpu_set_id} corpus_path {corpus_path}")
            self.logger.info(CRS_JAVA_WARN + f"{e}", exc_info=True)
        except Exception as e:
            self.logger.error(CRS_JAVA_ERR + f"[ERROR] pid {pid} cpu_set_id {cpu_set_id}, corpus_path {corpus_path}")
            self.logger.error(CRS_JAVA_ERR + f"{e}", exc_info=True)
            for line in e.stderr.split(b'\n'):
                self.logger.error(CRS_JAVA_ERR + f"[JAVA EXCEPTION] {line}")

    def run_executor_as_service(
        self, classpath: str, classname: str, corpus_path: Path, out_path: Path, cpu_set_id, pid: int
    ):
        harness_info = self.cp_metadata['harnesses'][self.harness_id]
        harness_id = harness_info['target_class']
        graal_env = {
            "JAVA_HOME": self.java_home,
            "JAVA_OPT": f'{self.java_opt}',
            "LD_DEBUG": "unused",
            # "LOG_LEVEL": "DEBUG",
        }

        env = environ.copy()
        env.update(graal_env)

        cpu_set = self.cpu_dict[cpu_set_id]

        if not self.disable_cgroup:
            cgroup_name = self.cgroup_list[cpu_set_id]
            self.logger.info(f"pid {pid} cpu_set_id {cpu_set_id} running on cgroup {cgroup_name} on cpus {','.join([str(x) for x in cpu_set])}")
            cmd = ["cgexec",
                "-g",
                f"memory,cpu:{self.cgroup_list[cpu_set_id]}",
                "--sticky"
                ]
        else:
            self.logger.info(f"pid {pid} cpu_set_id {cpu_set_id} on cpus {','.join([str(x) for x in cpu_set])} running!")
            cmd = []

        n_cores = len(cpu_set)
        cmd += [
            str(self.java_path),
            f"-Xmx{self.max_xms}m",
            f"-Xms{self.max_xms}m",
            f"-jar",
            str(self.app_jar_path),
            "--concolic-classpath",
            f"{classpath}",
            "--concolic-target",
            f"{classname}",
            "--concolic-args",
            f"{corpus_path}",
            "--harness-id",
            f"{harness_id}",
            "--java-home",
            f"{self.java_home}",
            "--outdir",
            f"{out_path}",
            "--pid",
            f"{pid}",
            "--timeout",
            f"{self.timeout}",
            "--server",
            f"{self.port}",            # always runs as a server!
            "--ncores",
            f"{n_cores}"
        ]

        scheduler_port = self.get_scheduler_port()
        if scheduler_port is not None:
            cmd += ["--scheduler-port", f"{scheduler_port}"]

        if self.debug_logging:
            cmd += ["--logging"]

        self.logger.info(f"{' '.join(cmd)}")

        try:
            subprocess.run(
                cmd,
                cwd=str(self.executor_dir),
                check=True,
                env=env,
                stderr=subprocess.PIPE,
                #stdout=subprocess.DEVNULL # give me output!
            )
        except Exception as e:
            self.logger.error(CRS_JAVA_ERR + f"[ERROR] pid {pid} cpu_set_id {cpu_set_id}, corpus_path {corpus_path}")
            self.logger.error(CRS_JAVA_ERR + str(e), exc_info=True)
            for line in e.stderr.split(b'\n'):
                self.logger.error(CRS_JAVA_ERR + f"[JAVA EXCEPTION] {line}")
