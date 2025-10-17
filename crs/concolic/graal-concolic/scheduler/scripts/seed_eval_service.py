"""
This script is used to evaluate the seed and get the partly visited branches.

Note:
    It's designed to be executed in the directory where this script is located.
"""

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
import struct
from typing import List
from os import makedirs, getenv, environ
from pathlib import Path

import argparse
import threading
from threading import Thread, Lock, RLock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

threading.stack_size(0x4000000)

logging.basicConfig(level=logging.INFO)

JACOCO_TIMEOUT = 10
PORT = 27664
HEADER = b"SEEDEVAL"

JACOCO_AGENT_PATH = None
JACOCO_CLI_PATH = None
JACOCO_CUSTOM_CLI_PATH = None

BASE_DIR = None

TEMP_MERGED_EXEC_PATH_FORMAT = "{0}/temp-merged-jacoco-exec-{1}.exec" # {0} is BASE_DIR, {1} is harness_id
MERGED_EXEC_PATH_FORMAT = "{0}/merged-jacoco-exec-{1}.exec" # {0} is BASE_DIR, {1} is harness_id
EXEC_PATH_FORMAT = "{0}/jacoco-exec-{1}-{2}.exec" # {0} is BASE_DIR, {1} is harness_id, {2} is index
JAR_PATH_FORMAT = "{0}/jar-unpacked-{1}" # {0} is BASE_DIR, {1} is harness_id
TRIED_BRANCHES_REQ_FORMAT = "tried-branches-{0}" # {0} is harness_id
LATEST_BRANCHES_REQ_FORMAT = "latest-branches-{0}" # {0} is harness_id

def ParseArg():
    global PORT
    global BASE_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=False, default=PORT)
    parser.add_argument("--base-dir", type=str, required=True, help="Base directory for the seed eval service (e.g. /tmp")

    args = parser.parse_args()
    PORT = args.port
    BASE_DIR = args.base_dir
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR, exist_ok=True)
    return args

class CommandHandler:
    def __init__(self):
        self.harness_id = None
        return
    
    def GetHarnessId(self):
        return self.harness_id

    def handle(self, json_data: dict):
        ret = {}
        self.harness_id = json_data["harness_id"]
        self.java_home = json_data["java_home"]
        return ret

#################################

class CommandPing(CommandHandler):
    NAME = "ping"

    def __init__(self):
        super().__init__()
        return
    
    def handle(self, json_data: dict):
        logging.info(f"Handling ping command")
        CommandHandler.handle(self, json_data)
        ret = {}
        try:
            ret = {"status": "ok"}
        except Exception as e:
            ret = {}
            logging.error(f"Error pinging: {e}")
        return ret
class CommandUpdateSeed(CommandHandler):
    NAME = "update_seed"

    def __init__(self):
        super().__init__()
        return
    
    def HandleJarFiles(self, harness_id: str, classes: List[str]):
        """
        Handle jar files
        """
        output_dir = JAR_PATH_FORMAT.format(BASE_DIR, harness_id)
        new_classes = []
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        for filepath in classes:
            if not filepath.endswith(".jar"):
                new_classes.append(filepath)
                continue
            if not os.path.exists(filepath):
                continue
            if not os.path.isfile(filepath):
                continue

            os.system(f"unzip -nq {filepath} -d {output_dir}")
        return new_classes + [output_dir]

    def UpdateSeed(self, harness_id: str, seed_path: str, classes: List[str]):
        """
        Update seed to redis
        Input json datas:
            String harness_id
            String seed_path
            List[String] classes
        Output json datas:
            None
        """
        ret = {}

        classpath = ":".join(classes)

        # Execute the target program with the seed and jacoco agent
        jacoco_options = [
            "destfile=" + EXEC_PATH_FORMAT.format(BASE_DIR, harness_id, 0),
            "append=false",
            "sessionid=default",
        ]
        jacoco_options = ",".join(jacoco_options)
        args = [
            os.path.join(self.java_home, "bin", "java"),
            "-javaagent:" + JACOCO_AGENT_PATH + "=" + jacoco_options,
            "-cp", classpath,
            "Runner",
            seed_path,
        ]
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=JACOCO_TIMEOUT)
        except subprocess.TimeoutExpired as e:
            ret = {}
            logging.error(f"Timeout updating seed: {e}")
            return ret
        # print(p.stdout)
        # print(p.stdout)

        # Merge jacoco exec files
        merged_exec_paths = []
        if os.path.exists(MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id)):
            merged_exec_paths.append(MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id))
        if os.path.exists(EXEC_PATH_FORMAT.format(BASE_DIR, harness_id, 0)):
            merged_exec_paths.append(EXEC_PATH_FORMAT.format(BASE_DIR, harness_id, 0))

        # Merge jacoco exec files
        try:
            os.remove(TEMP_MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id))
        except Exception as e:
            logging.error(f"Error removing temp merged exec file: {e}")
        args = [
            os.path.join(self.java_home, "bin", "java"),
            "-jar", JACOCO_CUSTOM_CLI_PATH,
            "merge", *merged_exec_paths,
            "--destfile", TEMP_MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id),
        ]
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=JACOCO_TIMEOUT)
        except subprocess.TimeoutExpired as e:
            ret = {}
            logging.error(f"Timeout merging jacoco exec files: {e}")
            return ret
        # print(p.stdout.strip())
        # print(p.stderr.strip())
        if os.path.exists(TEMP_MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id)):
            shutil.copy(
                TEMP_MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id),
                MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id),
            )
        else:
            logging.error(f"Temp merged exec file not found: {TEMP_MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id)}")
            return ret

        # Get latest branches
        new_classes = self.HandleJarFiles(harness_id, classes)
        prefixed_classfiles = []
        for classfile in new_classes:
            prefixed_classfiles += ["--classfiles", classfile]
        args = [
            os.path.join(self.java_home, "bin", "java"),
            "-jar", JACOCO_CUSTOM_CLI_PATH,
            "partly", MERGED_EXEC_PATH_FORMAT.format(BASE_DIR, harness_id),
            *prefixed_classfiles,
        ]
        # print(" ".join(args))
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=JACOCO_TIMEOUT)
            # print(p.stdout)
            # print(p.stderr)
        except subprocess.TimeoutExpired as e:
            ret = {}
            logging.error(f"Timeout getting latest branches: {e}")
            return ret
        ret = {}
        for line in p.stdout.split("\n"):
            line = line.strip()
            if not len(line):
                continue
            parts = line.split("|", 1)
            if len(parts) < 2:
                continue
            tp = parts[0]
            data = parts[1]
            if tp == "CLS":
                cur_classpath = data
            elif tp == "BCH":
                ret.setdefault(cur_classpath, []).append(data)
        # Save to file
        path = os.path.join(BASE_DIR, LATEST_BRANCHES_REQ_FORMAT.format(harness_id))
        with open(path, "w") as f:
            f.write(json.dumps(ret))
        return {}
    
    def handle(self, json_data: dict):
        """
        Input json datas:
            String harness_id
            String seed_path
            List[String] classes
        Output json datas:
            None
        """
        logging.info(f"Updating seed: {json_data}")
        CommandHandler.handle(self, json_data)
        ret = {}
        try:
            seed_path = json_data["seed_path"]
            classes = json_data["classes"]
            ret = self.UpdateSeed(self.harness_id, seed_path, classes)
        except Exception as e:
            ret = {}
            logging.error(f"Error updating seed: {e}")
        return ret

class CommandGetPartlyVisitedBranches(CommandHandler):
    NAME = "get_partly_visited_branches"

    def __init__(self):
        super().__init__()
        return
    
    def GetTriedBranches(self, harness_id: str):
        """
        Get tried branches from redis
        """
        ret = []
        path = os.path.join(BASE_DIR, TRIED_BRANCHES_REQ_FORMAT.format(harness_id))
        try:
            with open(path, "r") as f:
                tried_branches = f.readlines()
        except FileNotFoundError:
            tried_branches = []
        tried_branches = [line.strip() for line in tried_branches]
        tried_branches = list(filter(lambda x: len(x) > 0, tried_branches))
        tried_branches = list(set(tried_branches))
        return tried_branches
    
    def GetLatestBranches(self, harness_id: str):
        """
        Get latest branches from jacoco exec file
        Input json datas:
            String harness_id
        Output json datas:
            Dict[String, List[String]] latest branches like:
            {
                "/a/b/Runner.class": ["testBytes([B)Z:24", "method2(desc):1235", ...],
                "/d/e/Runner.class": ["testBytes([B)Z:24", "method4(desc):1237", ...],
                ...
            }
        """
        path = os.path.join(BASE_DIR, LATEST_BRANCHES_REQ_FORMAT.format(harness_id))
        try:
            with open(path, "r") as f:
                ret = json.load(f)
        except FileNotFoundError:
            ret = {}
        return ret
    
    def GetPartlyVisitedBranches(self, harness_id: str):
        """
        Get partly visited branches with redis
        Input json datas:
            String harness_id
        Output json datas:
            List[String] partly covered FULL branches like [org/apache/commons/imaging/formats/jpeg/JpegImageParser.keepMarker(I[I)Z:31, ...]
        """
        # TODO: Use redis
        tried_branches = self.GetTriedBranches(harness_id)
        latest_branches = self.GetLatestBranches(harness_id)

        # Filter branches - the output formats are different
        ### tried_branches: ["org/apache/commons/imaging/formats/jpeg/JpegImageParser.keepMarker(I[I)Z:31", ...]
        ### latest_branches: {
        ###     "/a/b/Runner.class": ["testBytes([B)Z:24", "method2(desc):1235", ...],
        ###     "/d/e/Runner.class": ["testBytes([B)Z:24", "method4(desc):1237", ...],
        ###     ...
        ### }
        filtered_latest_branches = set()
        for classfile, branches in latest_branches.items():
            classfile = classfile.replace(".class", "")
            while classfile.startswith("/"):
                classfile = classfile[1:]
            for branch in branches:
                full_branch = f"{classfile}.{branch}".strip()
                duplicate = False
                for tried_branch in tried_branches:
                    tried_branch = tried_branch.strip()
                    if full_branch.endswith(tried_branch):
                        # Already tried. Skip
                        duplicate = True
                        break
                if not duplicate:
                    filtered_latest_branches.add(full_branch)
        
        return list(filtered_latest_branches)
    
    def handle(self, json_data: dict):
        """
        Input json datas:
            String harness_id
        Output json datas:
            List[String] partly covered branches like [c(desc):1234, ...]
                - Should be filtered from the tried branches
        """
        logging.info(f"Getting partly visited branches: {json_data}")
        CommandHandler.handle(self, json_data)
        ret = {}
        try:
            ret = self.GetPartlyVisitedBranches(self.harness_id)
        except Exception as e:
            ret = {}
            logging.error(f"Error getting partly visited branches: {e}")
        return ret

class CommandAddTriedBranches(CommandHandler):
    NAME = "add_tried_branches"

    def __init__(self):
        super().__init__()
        return
    
    def AddTriedBranches(self, harness_id: str, tried_branches: List[str]):
        # TODO: Use redis
        """
        Add tried branches to redis
        Input json datas:
            String harness_id
            List[String] tried_branches like [org/apache/commons/imaging/formats/jpeg/JpegImageParser.keepMarker(I[I)Z:31, ...]
        Output json datas:
            None
        """
        ret = {}
        path = os.path.join(BASE_DIR, TRIED_BRANCHES_REQ_FORMAT.format(harness_id))
        try:
            with open(path, "r") as f:
                previous_tried_branches = f.readlines()
        except FileNotFoundError:
            previous_tried_branches = []
        previous_tried_branches = [line.strip() for line in previous_tried_branches]
        previous_tried_branches = list(filter(lambda x: len(x) > 0, previous_tried_branches))
        previous_tried_branches = set(previous_tried_branches)

        for tried_branch in tried_branches:
            tried_branch = tried_branch.strip()
            if not len(tried_branch):
                continue
            previous_tried_branches.add(tried_branch)

        with open(path, "w") as f:
            for tried_branch in previous_tried_branches:
                f.write(tried_branch + "\n")
        return ret

    def handle(self, json_data: dict):
        """
        Input json datas:
            String harness_id
            List[String] tried_branches like [org/apache/commons/imaging/formats/jpeg/JpegImageParser.keepMarker(I[I)Z:31, ...]
        Output json datas:
            None
        """
        logging.info(f"Adding tried branches: {json_data}")
        CommandHandler.handle(self, json_data)
        ret = {}
        try:
            tried_branches = json_data["tried_branches"]
            ret = self.AddTriedBranches(self.harness_id, tried_branches)
        except Exception as e:
            ret = {}
            logging.error(f"Error adding tried branches: {e}")
        return ret

class RequestHandler(socketserver.BaseRequestHandler):
    # Class-level lock to ensure only one handler runs at a time
    _handle_lock = Lock()

    def __init__(self, request, client_address, server):
        self.handlers = {
            CommandPing.NAME: CommandPing(),
            CommandUpdateSeed.NAME: CommandUpdateSeed(),
            CommandGetPartlyVisitedBranches.NAME: CommandGetPartlyVisitedBranches(),
            CommandAddTriedBranches.NAME: CommandAddTriedBranches(),
        }
        super().__init__(request, client_address, server)
        return

    def handle(self):
        logging.info(f"Handling request: {self.client_address}")
        header = self.request.recv(len(HEADER))
        if header != HEADER:
            return
        
        json_data_len = struct.unpack(">Q", self.request.recv(8))[0]
        json_data = bytearray()
        while len(json_data) < json_data_len:
            json_data += self.request.recv(json_data_len - len(json_data))
        json_data = json.loads(json_data)

        # Lock this section to prevent simultaneous execution
        with RequestHandler._handle_lock:
            try:
                ret = self.handlers[json_data["command"]].handle(json_data)
            except Exception as e:
                ret = {}
                logging.error(f"Error handling command: {e}")
                logging.error(traceback.format_exc())
        ret_json = json.dumps(ret)
        ret_json = ret_json.encode("utf-8")

        self.request.sendall(HEADER + struct.pack(">Q", len(ret_json)))
        self.request.sendall(ret_json)
        return

class MyTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class SeedEvalService:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = None
        return
    
    def start(self):
        self.server = MyTCPServer((self.host, self.port), RequestHandler)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

if __name__ == "__main__":
    ParseArg()

    logging.info(f'[SEED_EVAL_SERVICE] Starting seed eval service at port {PORT} and base dir {BASE_DIR}')

    JACOCO_AGENT_PATH = os.path.join(os.path.dirname(__file__), "../jars/jacocoagent.jar")
    JACOCO_CLI_PATH = os.path.join(os.path.dirname(__file__), "../jars/jacococli.jar")
    JACOCO_CUSTOM_CLI_PATH = os.path.join(os.path.dirname(__file__), "../jars/org.jacoco.cli-custom.jar")

    # Get canonical path
    JACOCO_AGENT_PATH = os.path.abspath(JACOCO_AGENT_PATH)
    JACOCO_CLI_PATH = os.path.abspath(JACOCO_CLI_PATH)
    JACOCO_CUSTOM_CLI_PATH = os.path.abspath(JACOCO_CUSTOM_CLI_PATH)

    if not os.path.isfile(JACOCO_AGENT_PATH):
        raise FileNotFoundError(f"Jacoco agent path not found: {JACOCO_AGENT_PATH}")
    if not os.path.isfile(JACOCO_CLI_PATH):
        raise FileNotFoundError(f"Jacoco vanilla cli path not found: {JACOCO_CLI_PATH}")
    if not os.path.isfile(JACOCO_CUSTOM_CLI_PATH):
        raise FileNotFoundError(f"Jacoco custom cli path not found: {JACOCO_CUSTOM_CLI_PATH}")

    service = SeedEvalService("0.0.0.0", PORT)
    service.start()
    # service.stop()
