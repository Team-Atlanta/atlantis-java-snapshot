import os
import re
import json
import hashlib
import shutil
from pathlib import Path
import logging
from tree_sitter import Language, Parser
import tree_sitter_c as tsc
import tree_sitter_java as tsjava
import tree_sitter_python as tspython
import tree_sitter_go as tsgo
from collections import defaultdict

C_LANGUAGE = Language(tsc.language())
JAVA_LANGUAGE = Language(tsjava.language())
PY_LANGUAGE = Language(tspython.language())
GO_LANGUAGE = Language(tsgo.language())

current_directory = Path(__file__).parent
library_path = current_directory / ".." / ".." / "lib" / "build" / "my-languages.so"
library_path = library_path.resolve()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workdir")


class Workdir:
    def __init__(
        self, workdir_path: None | str, repo_path: Path, refdiff_path: Path = None
    ):
        workdir_path = workdir_path or os.environ.get("WORKDIR")
        if workdir_path is None:
            raise ValueError("Workdir should not be None")

        self.workdir_path = Path(workdir_path) / "dictgen"
        self.constant_map_dir_path = self.workdir_path / "constant_map"
        self.constant_map_dir_path.mkdir(parents=True, exist_ok=True)

        self.repo_path = repo_path
        self.refdiff_path = refdiff_path if refdiff_path else None
        self.diff = open(refdiff_path, "r").read() if refdiff_path else None

        self.repo_name = os.path.basename(self.repo_path)

        self.repo_analysis_dir = self.workdir_path / self.repo_name
        self.repo_analysis_dir.mkdir(parents=True, exist_ok=True)
        self.lang_count = {}
        self.populate_workdir()
        self.funcs_in_diff = []
        self.language = self.inspect_language()
        return

    def get_repo(self):
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repo path {self.repo_path} does not exist.")
        return self.repo_path

    def parse_diff_file(self):
        EXT_TO_LANG = {".c": "C", ".h": "C", ".cpp": "C", ".java": "Java"}
        HUNK_REGEX = re.compile(
            r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
        )
        file_hunks = defaultdict(list)
        current_file = None

        if self.diff is None:
            return file_hunks

        for line in self.diff.splitlines():
            if line.startswith("+++ "):
                path = line[4:].strip()
                if path.startswith(("a/", "b/")):
                    path = path[2:]
                if path == "/dev/null":
                    current_file = None
                    current_lang = None
                    continue
                ext = os.path.splitext(path)[1]
                if ext in EXT_TO_LANG:
                    current_file = path
                    current_lang = EXT_TO_LANG[ext]
                else:
                    current_file = None
                    current_lang = None
                continue

            if current_file and line.startswith("@@ "):
                m = HUNK_REGEX.match(line)
                if not m:
                    continue
                new_start = int(m.group("new_start"))
                new_count = int(m.group("new_count") or "1")
                file_hunks[current_file].append(
                    {
                        "new_start": new_start,
                        "new_end": new_start + new_count - 1,
                        "language": current_lang,
                    }
                )

        return file_hunks

    def extract_functions_in_ref_diff(self):
        if not self.refdiff_path:
            return []

        touched = set()
        diff_per_file = self.parse_diff_file()

        for path, hunks in diff_per_file.items():
            src_path = os.path.join(self.repo_path, path)
            if not os.path.isfile(src_path):
                continue
            if not hunks:
                continue
            lang = hunks[0].get("language", "unknown")
            if lang == "unknown":
                continue
            funcs = (
                self.parse_functions_c(src_path)
                if lang == "C"
                else self.parse_functions_java(src_path)
            )
            for h in hunks:
                for func in funcs:
                    if not (
                        h["new_end"] < func["start"] or h["new_start"] > func["end"]
                    ):
                        touched.add(func["name"])
        return list(touched)

    def parse_functions_c(self, file_path):
        HUNK_REGEX = re.compile(
            r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
        )

        NAME_EXTRACT_REGEX = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\s*\(")

        funcs = []
        with open(os.path.join(self.repo_path, file_path), "r") as sf:
            lines = sf.readlines()

        i = 0
        while i < len(lines):
            if "(" in lines[i] and not lines[i].strip().startswith("#"):
                sig_lines = [lines[i].rstrip()]
                j = i + 1
                while j < len(lines) and ")" not in lines[j] and j - i < 10:
                    sig_lines.append(lines[j].rstrip())
                    j += 1
                if j < len(lines) and ")" in lines[j]:
                    sig_lines.append(lines[j].rstrip())
                    signature = " ".join(l.strip() for l in sig_lines)
                    if signature.strip().endswith(";"):
                        i += 1
                        continue
                    k = j + 1
                    while k < len(lines) and "{" not in lines[k] and k - j < 10:
                        k += 1
                    if k < len(lines) and "{" in lines[k]:
                        m = NAME_EXTRACT_REGEX.search(signature)
                        if m:
                            name = m.group("name")
                            start_line = i + 1
                            brace_count = lines[k].count("{") - lines[k].count("}")
                            l = k + 1
                            while l < len(lines) and brace_count > 0:
                                brace_count += lines[l].count("{") - lines[l].count("}")
                                l += 1
                            end_line = l
                            funcs.append(
                                {"name": name, "start": start_line, "end": end_line}
                            )
                            i = l
                            continue
            i += 1
        return funcs

    def parse_functions_java(self, src_path):
        JAVA_METHOD_REGEX = re.compile(
            r"""^
                \s*
                (?:public|protected|private|static|final|synchronized|abstract|\s)+   # modifiers
                (?:<[^>]+>\s*)?                                                         # optional generic <T>
                (?:[\w\[\]<>]+\s+)+                                                     # return type (with [] or <>)
                (?P<name>\w+)                                                           # method name
                \s*\(.*\)\s*                                                            # parameter list
                (?:throws\s+[\w\.,\s]+)?                                                # optional throws
                \s*\{                                                                   # opening brace
            """,
            re.VERBOSE,
        )
        funcs = []
        with open(src_path) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            m = JAVA_METHOD_REGEX.match(line)
            if not m:
                continue
            # find opening “{” at end of this line; set brace_count = 1
            brace_count = 1
            j = i
            while j < len(lines) and brace_count > 0:
                j += 1
                brace_count += lines[j - 1].count("{") - lines[j - 1].count("}")
                funcs.append({"name": m.group("name"), "start": i, "end": j})
        return funcs

    def write_tokens_from_diff(self, func, tokens):
        with open(
            self.repo_analysis_dir / f"tokens-{func}.txt", "w", encoding="utf-8"
        ) as f:
            for token in tokens:
                f.write(token + "\n")

    def write_cost(self, input_token_cost, output_token_cost, model):
        total_token_cost = input_token_cost + output_token_cost
        with open(self.repo_analysis_dir / f"cost-{model}.txt", "w") as f:
            f.write(f"Input token cost (USD): {input_token_cost}\n")
            f.write(f"Output token cost (USD): {output_token_cost}\n")
            f.write(f"Total token cost (USD): {total_token_cost}\n")

    def get_log_path(self, func_name):
        return (
            self.repo_analysis_dir / f"{func_name}.log"
            if func_name
            else self.workdir_path / "logs"
        )

    def populate_workdir(self) -> None:
        self.traverse_repo()
        self.make_inverse_index()

        return

    def get_language_for_extension(self, ext):
        """
        Return the language key for a given file extension.
        Note: For ".h" files, this default mapping assumes C; if you need C++ headers, adjust as needed.
        """
        ext = ext.lower()
        mapping = {
            ".c": "c",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".cc": "cpp",
            ".h": "c",  # Ambiguous: could also be C++ if desired.
            ".hpp": "cpp",
            ".hh": "cpp",
            ".java": "java",
            ".py": "python",
            ".go": "go",
        }
        return mapping.get(ext)

    def get_files_from_repo(self):
        """
        Recursively traverse the given directory and return a list of file paths that have
        an extension corresponding to C, C++, Java, Python, or Go source code.
        """
        allowed_exts = {
            ".c",
            ".cpp",
            ".cxx",
            ".cc",
            ".h",
            ".hpp",
            ".hh",
            ".java",
            ".py",
            ".go",
        }
        file_list = []

        if os.path.isdir(self.repo_path):
            # If it's a directory, walk through it
            for root, _, files in os.walk(self.repo_path):
                for fname in files:
                    ext = os.path.splitext(fname)[1]
                    if ext.lower() in allowed_exts:
                        file_list.append(os.path.join(root, fname))
        elif os.path.isfile(self.repo_path):
            # If it's a file, check its extension
            ext = os.path.splitext(self.repo_path)[1]
            if ext.lower() in allowed_exts:
                file_list.append(self.repo_path)

        return file_list

    def find_first_child_of_type(self, node, target_type):
        """
        Recursively search for the first node of the given target_type in the subtree.
        Returns the text (decoded as UTF-8) if found, or None.
        """
        if node.type == target_type:
            return node.text.decode("utf8")
        for child in node.children:
            if child.type == "modifiers":
                continue
            result = self.find_first_child_of_type(child, target_type)
            if result:
                return result
        return None

    def find_ancestor(self, node, target_types):
        """
        Walk up the parent chain and return the first ancestor node whose type is in target_types.
        target_types should be a set of node type strings.
        """
        current = node.parent
        while current:
            if current.type in target_types:
                return current
            current = current.parent
        return None

    def extract_functions_c(self, tree, source_code):
        """
        For C: Extract functions by finding nodes of type "function_definition".
        There is no member function concept in plain C.
        """
        functions = []

        def visitor(node):
            if node.type == "function_definition":
                func_name = self.find_first_child_of_type(node, "identifier")
                if func_name:
                    functions.append(func_name)
            for child in node.children:
                visitor(child)

        visitor(tree.root_node)
        return functions

    def extract_functions_cpp(self, tree, source_code):
        """
        For C++: Extract free and member functions from nodes of type "function_definition".
        If a function node is nested within a class or struct, prefix its name with the enclosing
        class/struct name (separated by "::").
        """
        functions = []

        def visitor(node):
            if node.type == "function_definition":
                func_name = self.find_first_child_of_type(node, "identifier")
                if func_name:
                    # Look for an ancestor that is a class/struct.
                    # Tree-sitter-cpp may use "class_specifier", "struct_specifier", or "class_declaration".
                    ancestor = self.find_ancestor(
                        node,
                        {"class_specifier", "struct_specifier", "class_declaration"},
                    )
                    if ancestor:
                        # In a class, the name is often stored as "type_identifier" or "identifier"
                        class_name = self.find_first_child_of_type(
                            ancestor, "type_identifier"
                        )
                        if not class_name:
                            class_name = self.find_first_child_of_type(
                                ancestor, "identifier"
                            )
                        if class_name:
                            qualified_name = f"{class_name}::{func_name}"
                        else:
                            qualified_name = func_name
                    else:
                        qualified_name = func_name
                    functions.append(qualified_name)
            for child in node.children:
                visitor(child)

        visitor(tree.root_node)
        return functions

    def extract_functions_java(self, tree, source_code):
        """
        For Java: Extract methods and constructors (nodes of type "method_declaration" or
        "constructor_declaration"). The enclosing class (or interface) name is prepended to the
        method name.
        """
        functions = []

        def visitor(node):
            if node.type in ("method_declaration", "constructor_declaration"):
                func_name = self.find_first_child_of_type(node, "identifier")
                if func_name:
                    # Look for an enclosing class or interface.
                    ancestor = self.find_ancestor(
                        node, {"class_declaration", "interface_declaration"}
                    )
                    if ancestor:
                        class_name = self.find_first_child_of_type(
                            ancestor, "identifier"
                        )
                        if class_name:
                            qualified_name = f"{class_name}::{func_name}"
                        else:
                            qualified_name = func_name
                    else:
                        qualified_name = func_name
                    functions.append(qualified_name)
            for child in node.children:
                visitor(child)

        visitor(tree.root_node)
        return functions

    def extract_functions_from_file(self, filepath, language):
        """
        Given a filepath, open the file, parse its content with Tree-sitter using the grammar
        for the specified language, and return a list of function names (qualified if needed).
        """
        with open(filepath, "rb") as f:
            source_code = f.read()

        if language == "c":
            parser = Parser(C_LANGUAGE)
            tree = parser.parse(source_code)
            return self.extract_functions_c(tree, source_code)
        elif language == "java":
            parser = Parser(JAVA_LANGUAGE)
            tree = parser.parse(source_code)
            return self.extract_functions_java(tree, source_code)
        elif language == "python":
            parser = Parser(PY_LANGUAGE)
            tree = parser.parse(source_code)
            return self.extract_functions_python(tree, source_code)
        elif language == "go":
            parser = Parser(GO_LANGUAGE)
            tree = parser.parse(source_code)
            return self.extract_functions_go(tree, source_code)
        else:
            return []

    def extract_functions_python(self, tree, source_code):
        """
        For Python: Extract functions and methods (nodes of type "function_definition").
        If a function node is nested within a class, prefix its name with the enclosing class name.
        """
        functions = []

        def visitor(node):
            if node.type == "function_definition":
                func_name = self.find_first_child_of_type(node, "identifier")
                if func_name:
                    # Look for an ancestor that is a class.
                    ancestor = self.find_ancestor(node, {"class_definition"})
                    if ancestor:
                        class_name = self.find_first_child_of_type(
                            ancestor, "identifier"
                        )
                        if class_name:
                            qualified_name = f"{class_name}.{func_name}"
                        else:
                            qualified_name = func_name
                    else:
                        qualified_name = func_name
                    functions.append(qualified_name)
            for child in node.children:
                visitor(child)

        visitor(tree.root_node)
        return functions

    def extract_functions_go(self, tree, source_code):
        """
        For Go: Extract functions and methods (nodes of type "function_declaration").
        If a function node is a method, prefix its name with the receiver type.
        """

        functions = []

        def visitor(node):
            if node.type == "function_declaration":
                func_name = self.find_first_child_of_type(node, "identifier")
                if func_name:
                    # Check if the function is a method by looking for a receiver.
                    receiver_node = self.find_first_child_of_type(node, "receiver")
                    if receiver_node:
                        # The receiver type is usually found as a child of the receiver node.
                        receiver_type = self.find_first_child_of_type(
                            receiver_node, "type_identifier"
                        )
                        if not receiver_type:
                            receiver_type = self.find_first_child_of_type(
                                receiver_node, "identifier"
                            )
                        if receiver_type:
                            qualified_name = f"{receiver_type}.{func_name}"
                        else:
                            qualified_name = func_name
                    else:
                        qualified_name = func_name
                    functions.append(qualified_name)
            for child in node.children:
                visitor(child)

        visitor(tree.root_node)
        return functions

    def traverse_repo(self) -> None:
        self.repo_summary = {}

        files = self.get_files_from_repo()
        if len(files) == 0:
            return

        for fpath in files:
            ext = os.path.splitext(fpath)[1]
            lang = self.get_language_for_extension(ext)
            if not lang:
                continue
            self.lang_count[lang] = self.lang_count.get(lang, 0) + 1
            try:
                functions = self.extract_functions_from_file(fpath, lang)
                self.repo_summary[fpath] = functions
            except Exception as e:
                logger.error(f"Error processing file '{fpath}': {e}")

    def inspect_language(self) -> str:
        return max(self.lang_count, key=self.lang_count.get, default=None)

    def make_inverse_index(self) -> None:
        self.inverse_index = {}
        for fpath, functions in self.repo_summary.items():
            for func in functions:
                if func not in self.inverse_index:
                    self.inverse_index[func] = []
                self.inverse_index[func].append(fpath)

    def find_fname(self, func_name: str, _exact_match: bool):
        # _exact_match is no longer used
        if self.language == "java":
            return self.find_fname_java(func_name)
        else:  # treat all as C
            return self.find_fname_c(func_name)

    def find_fname_c(self, func_name: str):
        func_name = Workdir.canonicalize_function_name(func_name)

        fname_annotation = None
        if ":" in func_name:
            fname_annotation, func_name = func_name.split(":")

        return [
            fname
            for fname, functions in self.repo_summary.items()
            if any(func_name in f for f in functions)
            and (fname_annotation is None or func_name.endswith(fname_annotation))
        ]

    def find_fname_java(self, func_name: str):
        if not ("(" in func_name and "." in func_name.split("(", 1)[0]):
            return self.find_fname_c(func_name)

        signature = func_name

        def parse_sig(sig):
            klass_and_method, rest = sig.split("(", 1)
            class_fqn, method = klass_and_method.rsplit(".", 1)
            params, _ = rest.split(")", 1)
            param_types = [
                p.strip("L;").replace("/", ".")
                for p in re.findall(r"(?:\[*)L[^;]+;", params)
            ]
            return class_fqn, method, param_types

        class_fqn, _method, _params = parse_sig(signature)
        rel_path = class_fqn.replace(".", os.sep) + ".java"

        fnames = [
            fname for fname, _ in self.repo_summary.items() if fname.endswith(rel_path)
        ]
        return fnames if fnames else self.find_fname_c(func_name)

    def canonicalize_function_name(func_name: str) -> str:
        canonical_name = func_name

        last_dot_pos = canonical_name.rfind(".")
        if last_dot_pos != -1:
            canonical_name = canonical_name[last_dot_pos + 1 :]

        last_colon_pos = canonical_name.rfind(":")
        if last_colon_pos != -1:
            canonical_name = canonical_name[last_colon_pos + 1 :]

        first_paren_pos = canonical_name.find("(")
        if first_paren_pos != -1:
            canonical_name = canonical_name[:first_paren_pos]

        return canonical_name

    def get_output_file(self):
        return self.repo_analysis_dir / "output.dict"

    def need_inter_file_analysis(self) -> bool:
        return self.language == "java"

    def get_constant_map_path(self, source_file):
        if not source_file:
            raise ValueError("Source file cannot be None or empty.")
        hash_object = hashlib.sha256(source_file.encode())
        encoded_path = hash_object.hexdigest()
        return self.constant_map_dir_path / (encoded_path + ".constant_map")

    def check_constant_map(self, source_file):
        return self.get_constant_map_path(source_file).exists()

    def load_constant_map(self, source_file):
        try:
            with open(self.get_constant_map_path(source_file), "r") as f:
                constant_map = json.load(f)
                return constant_map
        except:
            return None

    def store_constant_map(self, constant_map, source_file):
        if not source_file:
            # XXX: this shouldn't happen
            return

        with open(self.get_constant_map_path(source_file), "w") as f:
            if isinstance(constant_map, dict):
                json.dump(constant_map, f, indent=4)


# For testing
if __name__ == "__main__":
    import sys

    workdir = Workdir(
        sys.argv[1],
        sys.argv[2],
        Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None,
    )

    if len(sys.argv) > 3:
        print(workdir.extract_functions_in_ref_diff())

    # print(workdir.repo_summary)
    # print(workdir.inverse_index)
