import concurrent.futures
import glob
import json
import multiprocessing
import os
import subprocess
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

CRS_ERR = "CRS-JAVA-ERR-coordinates"
CRS_WARN = "CRS-JAVA-WARN-coordinates"


@dataclass(frozen=True)
class CodeCoordinate:
    jar_file: str
    class_file_path: str
    class_name: str
    file_name: str
    method_name: str
    method_desc: str
    bytecode_offset: int
    line_number: int


class BytecodeInspector:

    def __init__(self, workdir: Path = Path(".")):
        jar_dir = os.path.dirname(os.path.abspath(__file__))
        self.jar_path = os.path.join(jar_dir, "bytecode-parser.jar")
        if not os.path.exists(self.jar_path):
            print(f"{CRS_ERR} JAR file not found at {self.jar_path}")
            return
        self.mapping_data: Dict[str, Dict[str, List[CodeCoordinate]]] = {}
        workdir.mkdir(parents=True, exist_ok=True)
        self.workdir_str = str(workdir.resolve())

    def _enumerate_classpath(self, cp_list: list[str]) -> Set[str]:
        matched_files = set()

        for entry in cp_list:
            entry = entry.strip()
            if not entry:
                continue
            if "*" in entry:
                # wildcard -> * only match the jar/zip files in the current directory
                dir_part = os.path.dirname(entry)
                if not dir_part:
                    dir_part = "."
                pattern = os.path.join(dir_part, "*.jar")
                for match in glob.glob(pattern):
                    if os.path.isfile(match):
                        matched_files.add(os.path.abspath(match))
                pattern = os.path.join(dir_part, "*.zip")
                for match in glob.glob(pattern):
                    if os.path.isfile(match):
                        matched_files.add(os.path.abspath(match))
                continue

            if os.path.isdir(entry):
                # nestedly find all .class files
                for root, dirs, files in os.walk(entry):
                    for file in files:
                        if file.endswith(".class"):
                            matched_files.add(os.path.abspath(os.path.join(root, file)))
                continue

            if os.path.isfile(entry):
                if entry.endswith((".jar", ".zip", ".class")):
                    matched_files.add(os.path.abspath(entry))
                continue

        return matched_files

    def _single_process_init_mapping(
        self, pkg_list: List[str], jar_list: List[str]
    ) -> str:
        fd, output_json = tempfile.mkstemp(dir=self.workdir_str, suffix=".json")
        os.close(fd)  # Close the file descriptor but keep the file

        try:
            command_args = []
            command_args.append(output_json)
            command_args.extend(pkg_list)
            command_args.append("--")
            command_args.extend(jar_list)

            cmd = ["java", "-jar", self.jar_path] + command_args
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if not os.path.exists(output_json):
                raise FileNotFoundError(f"Output JSON '{output_json}' not found.")

            return output_json
        except Exception as e:
            # Clean up the temporary file if an error occurred
            """
            if os.path.exists(output_json):
                os.unlink(output_json)
            """
            print(
                f"{CRS_ERR} during running Java tool: {e} {traceback.format_exc()}",
                flush=True,
            )
            return None

    def _handle_default_package(self, pkg_list: List[str]) -> List[str]:
        processed_pkg_list = set()
        for pkg in pkg_list:
            _pkg = pkg.strip()
            if _pkg == "":
                processed_pkg_list.add("<default>")
            else:
                processed_pkg_list.add(_pkg)
        return list(set(processed_pkg_list))

    def init_mapping(self, pkg_list: List[str], cp_list: List[str]):
        """
        Initialize mapping by invoking Java tool with given classpath.

        Args:
            pkg_list (List[str]): Package prefixes to filter classes
            cp_list (List[str]): Classpath list to search for classes and JAR files
        """
        jar_set = self._enumerate_classpath(cp_list)
        if not jar_set:
            print(f"{CRS_ERR} No JAR files found in the classpath.")
            return

        # Convert the set to a list for slicing
        jar_list = list(jar_set)

        batch_size = 20  # NOTE: change this if needed
        jar_batches = [
            jar_list[i : i + batch_size] for i in range(0, len(jar_list), batch_size)
        ]

        num_threads = min(len(jar_batches), multiprocessing.cpu_count())
        json_files = []

        processed_pkg_list = self._handle_default_package(pkg_list)

        try:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = {
                    executor.submit(
                        self._single_process_init_mapping, processed_pkg_list, batch
                    ): batch
                    for batch in jar_batches
                }

                for future in concurrent.futures.as_completed(futures):
                    try:
                        json_path = future.result()
                        if json_path:
                            json_files.append(json_path)
                    except Exception as exc:
                        print(f"{CRS_ERR} Batch processing failed: {exc}", flush=True)
                        traceback.print_exc()

            for json_path in json_files:
                try:
                    with open(json_path, encoding="utf-8") as f:
                        print(f"Loading coordinate mapping from {json_path}")
                        data = json.load(f)
                        self._load_mapping(data)
                except Exception as exc:
                    print(
                        f"{CRS_ERR} Failed to load mapping from {json_path}: {exc}",
                        flush=True,
                    )
                    traceback.print_exc()

        finally:
            pass
            # NOTE: no need to delete the temp files
            """
            for json_path in json_files:
               try:
                   if os.path.exists(json_path):
                       os.unlink(json_path)
               except Exception as exc:
                   print(
                       f"Failed to delete temporary file {json_path}: {exc}",
                       flush=True,
                   )
            """

    def _load_mapping(self, data: Dict[str, Any]):
        """
        {
          "com.example.Class": {
            "42": [
              {
                "jarFile": "path/to/jar",
                "classFilePath": "com/example/Class.class",
                "className": "com.example.Class",
                "sourceFileName": "Class.java",
                "methodName": "method",
                "methodDesc": "()V",
                "bytecodeOffset": 10,
                "lineNumber": 42
              }
            ]
          }
        }
        """
        for class_name, lineno_dict in data.items():
            if class_name not in self.mapping_data:
                self.mapping_data[class_name] = {}

            for lineno_str, entries in lineno_dict.items():
                lineno = int(lineno_str)
                coordinates = {
                    CodeCoordinate(
                        jar_file=entry["jarFile"],
                        class_file_path=entry["classFilePath"],
                        class_name=entry["className"],
                        file_name=entry["sourceFileName"],
                        method_name=entry["methodName"],
                        method_desc=entry["methodDesc"],
                        bytecode_offset=entry["bytecodeOffset"],
                        line_number=entry["lineNumber"],
                    )
                    for entry in entries
                }

                if lineno in self.mapping_data[class_name]:
                    self.mapping_data[class_name][lineno].update(coordinates)
                else:
                    self.mapping_data[class_name][lineno] = coordinates

    def query(self, class_name: str, line_num: int) -> Optional[CodeCoordinate]:
        """Query the mapping data for a specific class full name and line number,
        returns the coordinate with the lowest bytecode offset for the given line number.
        NOTE: thread-safe, this is the only API and is read-only.
        """
        try:
            line_mappings = self.mapping_data.get(class_name.replace("/", "."), {})
            line_num = int(line_num)
            coordinates = line_mappings.get(line_num, [])
            if not coordinates:
                return None
            return min(coordinates, key=lambda c: c.bytecode_offset)
        except Exception as e:
            print(
                f"{CRS_ERR} Error querying mapping: {e} {traceback.format_exc()}",
                flush=True,
            )
            return None
