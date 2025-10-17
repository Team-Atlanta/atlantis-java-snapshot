import sys
import os
import re
import random
from pathlib import Path
from typing import List, Tuple, Callable

from utility.llm import LLM


from tree_sitter import Language, Parser
import tree_sitter_c as tsc
import tree_sitter_java as tsjava
import tree_sitter_python as tspython
import tree_sitter_go as tsgo


# ============================================================================
# SETUP: Build (once) and load the language library.
#
# You need to clone the tree-sitter grammars (e.g. tree-sitter-c and tree-sitter-java)
# and then build a shared library. For example, in your project directory run:
#
#     Language.build_library(
#         'build/my-languages.so',
#         [
#             'path/to/tree-sitter-c',
#             'path/to/tree-sitter-java'
#         ]
#     )
#
# Then adjust the paths below accordingly.
# ============================================================================

C_LANGUAGE = Language(tsc.language())
JAVA_LANGUAGE = Language(tsjava.language())
PY_LANGUAGE = Language(tspython.language())
GO_LANGUAGE = Language(tsgo.language())

# ============================================================================
# Helper functions
# ============================================================================


def get_node_text(node, source_code):
    """Return the source text corresponding to the node."""
    return source_code[node.start_byte : node.end_byte].decode("utf-8")


def find_identifier(node, source_code):
    """
    Recursively search for a child node of type 'identifier' and return its text.
    This is used in the C grammar to find the function name.
    """
    if node.type == "identifier":
        return get_node_text(node, source_code)
    for child in node.children:
        result = find_identifier(child, source_code)
        if result is not None:
            return result
    return None


def get_function_name_c(node, source_code):
    """
    Given a Tree-sitter node for a C function_definition,
    return the function’s name by searching in its 'declarator' subtree.
    """
    declarator = None
    for child in node.children:
        if child.type == "function_declarator" or child.type == "pointer_declarator":
            declarator = child
            break
    if declarator is None:
        return None
    return find_identifier(declarator, source_code)


def get_method_name_java(node, source_code):
    """
    Given a Tree-sitter node for a Java method_declaration or constructor_declaration,
    return its name.
    """
    # First try using the field name "name" (if the grammar sets it).
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return get_node_text(name_node, source_code)
    # Otherwise, scan the children for an identifier.
    for child in node.children:
        if child.type == "identifier":
            return get_node_text(child, source_code)
    return None


def get_function_name_go(node, source_code):
    """
    For Go, given a function_declaration node, return the function's name.
    (This works for both plain functions and methods.)
    """
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return get_node_text(name_node, source_code)
    return find_identifier(node, source_code)


def get_function_name_python(node, source_code):
    """
    For Python, given a function_definition node, return the function's name.
    """
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return get_node_text(name_node, source_code)
    return find_identifier(node, source_code)


def merge_ranges(ranges):
    """
    Given a list of (start, end) tuples (byte ranges) possibly overlapping,
    merge them into a sorted list of non-overlapping ranges.
    """
    if not ranges:
        return []
    ranges.sort(key=lambda x: x[0])
    merged = [ranges[0]]
    for current in ranges[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    return merged


def remove_ranges(source_code, ranges):
    """
    Given the original source_code (as bytes) and a sorted list of ranges,
    return a new source (as bytes) with those ranges removed.
    """
    new_bytes = []
    last_index = 0
    for start, end in ranges:
        new_bytes.append(source_code[last_index:start])
        last_index = end
    new_bytes.append(source_code[last_index:])
    return b"".join(new_bytes)


def collect_function_nodes(node, source_code, target_function_name, language):
    """
    Recursively traverse the AST and collect the byte ranges of function (or method)
    nodes that do NOT match the target_function_name.

    For C, function nodes are of type "function_definition".
    For Java, we look for "method_declaration" and "constructor_declaration".
    """
    removal_ranges = []
    if language == "c":
        if node.type == "function_definition":
            fname = get_function_name_c(node, source_code)
            if fname != target_function_name:
                removal_ranges.append((node.start_byte, node.end_byte))
    elif language == "java":
        if node.type in ("method_declaration", "constructor_declaration"):
            fname = get_method_name_java(node, source_code)
            if fname != target_function_name:
                removal_ranges.append((node.start_byte, node.end_byte))
    elif language == "go":
        if node.type == "function_declaration":
            fname = get_function_name_go(node, source_code)
            if fname != target_function_name:
                removal_ranges.append((node.start_byte, node.end_byte))
    elif language == "python":
        if node.type == "function_definition":
            fname = get_function_name_python(node, source_code)
            if fname != target_function_name:
                removal_ranges.append((node.start_byte, node.end_byte))
    # Recurse into children
    for child in node.children:
        removal_ranges.extend(
            collect_function_nodes(child, source_code, target_function_name, language)
        )
    return removal_ranges


def collect_comment_nodes(node):
    """
    Recursively traverse the AST and collect the byte ranges of all comment nodes.
    This function checks for nodes whose type is 'comment', 'line_comment', or 'block_comment'.
    """
    comment_ranges = []
    if node.type in {"comment", "line_comment", "block_comment"}:
        comment_ranges.append((node.start_byte, node.end_byte))
    for child in node.children:
        comment_ranges.extend(collect_comment_nodes(child))
    return comment_ranges


# ============================================================================
# Main function
# ============================================================================


def extract_function_and_globals(file_path, target_function_name):
    """
    Given a C or Java source file and a target function name, return a new source string
    that has all functions (or methods) removed except the one whose name equals target_function_name.
    Global declarations (such as variable definitions or class/field definitions) are retained.

    In addition, all comments are removed from the output.
    """
    # Read the source file as bytes.
    with open(file_path, "rb") as f:
        source_code = f.read()

    # Choose language based on the file extension.
    if file_path.endswith((".c", ".h")):
        lang = "c"
        language = C_LANGUAGE
    elif file_path.endswith(".java"):
        lang = "java"
        language = JAVA_LANGUAGE
    elif file_path.endswith(".py"):
        lang = "python"
        language = PY_LANGUAGE
    elif file_path.endswith(".go"):
        lang = "go"
        language = GO_LANGUAGE
    elif file_path.endswith(".diff"):
        return source_code.decode("utf-8").splitlines()  # No processing for diff files
    else:
        raise ValueError(
            "Unsupported file type. Only C (.c, .h), Python (.py), Go (.go), and Java (.java) files are supported."
        )

    # Parse the file.
    parser = Parser(language)
    tree = parser.parse(source_code)
    root = tree.root_node

    # Collect ranges for all functions (or methods) that are not the target.
    removal_ranges = collect_function_nodes(
        root, source_code, target_function_name, lang
    )
    # Collect ranges for all comment nodes.
    comment_ranges = collect_comment_nodes(root)
    # Combine and merge ranges.
    all_removals = removal_ranges + comment_ranges
    merged_ranges = merge_ranges(all_removals)

    # Remove the unwanted ranges (functions and comments) from the source.
    new_source = remove_ranges(source_code, merged_ranges)

    return remove_consecutive_blank_lines(new_source.decode("utf-8"))


def remove_consecutive_blank_lines(text):
    # Split the text into lines
    lines = text.splitlines()
    result_lines = []

    # Loop through each line
    for line in lines:
        # Check if the current line is blank
        if line.strip() == "":
            # If result_lines is not empty and the last line is blank, skip it
            if result_lines and result_lines[-1].strip() == "":
                continue
        result_lines.append(line)

    return result_lines


def shrink_context(
    model_name: str, file_name: str, lines: List[str], function_name: str
) -> List[str]:
    if file_name.endswith((".c", ".h", ".cpp", ".cc")):
        return shrink_context_c(model_name, lines, function_name)
    elif file_name.endswith(".diff"):
        return lines
    else:
        # TODO: Java
        return lines


def shrink_context_c(
    model_name: str, lines: List[str], function_name: str
) -> List[str]:

    if not LLM.exceeds_limit("\n".join(lines), model_name, coeff=0.9):
        return lines

    lines = shrink_context_c_remove_unused_globals(lines, function_name)

    if not LLM.exceeds_limit("\n".join(lines), model_name, coeff=0.9):
        return lines

    return shrink_context_c_aggressive(model_name, lines, function_name)


def shrink_context_c_remove_unused_globals(
    lines: List[str], function_name: str
) -> List[str]:
    """
    Remove global #define macros and top-level variable declarations
    not referenced by the body of function_name.

    Args:
        source: the full C source as a list of lines
        function_name: the name of the function to analyze

    Returns:
        The source with unused globals/macros stripped out.
    """

    source = "\n".join(lines)

    # --- 1. Extract function body substring by matching braces ---
    pattern = re.compile(r"\b" + re.escape(function_name) + r"\s*\([^)]*\)\s*\{")
    match = pattern.search(source)
    if not match:
        # function not found; nothing to strip
        return source

    # find start index in characters
    body_start = match.end()  # position right after the '{'
    # now scan from body_start to find matching closing '}'
    depth = 1
    i = body_start
    while i < len(source) and depth > 0:
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
        i += 1
    body_end = i - 1  # position of the matching '}'

    body = source[body_start:body_end]

    # --- 2. Tokenize to find all identifiers used in the function ---
    tokens = set(re.findall(r"\b[A-Za-z_]\w*\b", body))

    # --- 3. Compute nesting depth of each line to isolate top-level defs ---
    depths: List[int] = []
    d = 0
    for line in lines:
        depths.append(d)
        for ch in line:
            if ch == "{":
                d += 1
            elif ch == "}":
                d -= 1

    # helper to record ranges
    to_remove: List[Tuple[int, int]] = []

    # --- 4a. Find global macros ---
    i = 0
    while i < len(lines):
        if depths[i] == 0:
            m = re.match(r"\s*#\s*define\s+([A-Za-z_]\w*)", lines[i])
            if m:
                name = m.group(1)
                # gather multi-line macro
                j = i + 1
                while j < len(lines) and lines[j - 1].rstrip().endswith("\\"):
                    j += 1
                # if unused, mark for removal
                if name not in tokens:
                    to_remove.append((i, j))
                i = j
                continue
        i += 1

    # --- 4b. Find global variable declarations ---
    var_decl_re = re.compile(
        r"^\s*(?:static|extern)?\s*[A-Za-z_][\w\s\*]*\s+([A-Za-z_]\w*)"  # type + name
        r"(?:\s*=\s*[^;]+)?\s*;"  # optional initializer
    )
    for idx, (line, dep) in enumerate(zip(lines, depths)):
        if dep == 0 and not line.lstrip().startswith("#"):
            m = var_decl_re.match(line)
            if m:
                name = m.group(1)
                if name not in tokens:
                    # remove only this line
                    to_remove.append((idx, idx + 1))

    # --- 5. Build new source without the marked ranges ---
    # flatten and coalesce removal ranges
    if not to_remove:
        return source
    to_remove.sort()
    merged: List[Tuple[int, int]] = []
    cur_start, cur_end = to_remove[0]
    for s, e in to_remove[1:]:
        if s <= cur_end:
            cur_end = max(cur_end, e)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = s, e
    merged.append((cur_start, cur_end))

    # now rebuild
    output_lines: List[str] = []
    prev = 0
    for s, e in merged:
        output_lines.extend(lines[prev:s])
        prev = e
    output_lines.extend(lines[prev:])

    return output_lines


def shrink_context_c_aggressive(lines: List[str], function_name: str) -> List[str]:
    return modify_c_source(
        lines,
        function_name,
        check=lambda fn_body: LLM.exceeds_limit(fn_body, model_name, coeff=0.9),
        removal_rate=0.7,
    )


def modify_c_source(
    source: list[str],
    function_name: str,
    check: Callable[[str], bool],
    removal_rate: float = 0.7,
) -> str:
    """
    1) Randomly strip out ~removal_rate of the top‐level (global) variable definitions.
    2) Truncate the back of `function_name`'s body one line at a time until check(fn_body) is True.

    Args:
        source: The C source as a list of lines.
        function_name: The name of the function whose tail you’ll truncate.
        check: A callable that takes the *current* function body (as one string) and returns True/False.
        removal_rate: Fraction of globals to drop (0.0–1.0).

    Returns:
        The modified source joined as a single string.
    """
    lines = source[:]  # copy to avoid mutating caller

    # --- 1) Compute brace‐depth for each line to find globals & the function ---
    depths = []
    d = 0
    for line in lines:
        depths.append(d)
        for ch in line:
            if ch == "{":
                d += 1
            elif ch == "}":
                d -= 1

    # --- 2) Randomly remove globals ---
    var_decl_re = re.compile(
        r"^\s*(?:static|extern)?\s*"  # optional storage
        r"[A-Za-z_][\w\s\*]*\s+"  # type (e.g. "int", "char *")
        r"([A-Za-z_]\w*)"  # variable name
        r"(?:\s*=\s*[^;]+)?\s*;"  # optional initializer
    )
    to_remove = {
        i
        for i, (ln, dep) in enumerate(zip(lines, depths))
        if dep == 0
        and not ln.lstrip().startswith("#")
        and var_decl_re.match(ln)
        and random.random() < removal_rate
    }

    filtered = [ln for i, ln in enumerate(lines) if i not in to_remove]

    # --- 3) Recompute depths & locate function ---
    depths = []
    d = 0
    for line in filtered:
        depths.append(d)
        for ch in line:
            if ch == "{":
                d += 1
            elif ch == "}":
                d -= 1

    sig_re = re.compile(r"\b" + re.escape(function_name) + r"\s*\([^)]*\)\s*\{")
    start_idx = next(
        (
            i
            for i, (ln, dep) in enumerate(zip(filtered, depths))
            if dep == 0 and sig_re.search(ln)
        ),
        None,
    )
    if start_idx is None:
        return "\n".join(filtered)

    # find matching closing brace
    local_depth = 0
    seen = False
    end_idx = None
    for i in range(start_idx, len(filtered)):
        for ch in filtered[i]:
            if ch == "{":
                local_depth += 1
                seen = True
            elif ch == "}":
                local_depth -= 1
        if seen and local_depth == 0:
            end_idx = i
            break
    if end_idx is None:
        return "\n".join(filtered)

    # --- 4) Truncate function body until check() passes ---
    fn_body = filtered[start_idx + 1 : end_idx]
    while fn_body:
        candidate = "\n".join(fn_body)
        if check(candidate):
            break
        fn_body.pop()

    # --- 5) Reassemble and return ---
    result_lines = filtered[: start_idx + 1] + fn_body + filtered[end_idx:]
    return result_lines


# ============================================================================
# Example usage
# ============================================================================

if __name__ == "__main__":
    # Example: extract only the function named 'my_function' from a C file.
    # (Replace 'example.c' with your file and adjust the target function name.)
    filtered_source = extract_function_and_globals(sys.argv[1], sys.argv[2])
    print("-- Filtered Source Code --")
    print("\n".join(filtered_source))

    print("-- Shrunked Source Code --")
    shrunked_source = shrink_context(
        "gpt-4o", sys.argv[1], filtered_source, sys.argv[2]
    )
    print("\n".join(shrunked_source))
