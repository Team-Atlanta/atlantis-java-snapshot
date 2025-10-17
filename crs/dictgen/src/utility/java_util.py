#!/usr/bin/env python3
import os
import re
import sys
from collections import defaultdict


def strip_java_comments(text):
    """
    Remove block comments (/* ... */) and line comments (// ...) from a Java source string.
    """
    text_no_block = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text_no_line = re.sub(r"//.*", "", text_no_block)
    return text_no_line


def build_repo_metadata(repo_root):
    """
    Walk through repo_root, find all .java files, extract their package declaration
    and class name to build:
      - fqn_to_path: FQN (e.g. 'com.example.Foo') --> absolute file path
      - package_to_classes: packageName --> [list of class names in that package]
    """
    fqn_to_path = {}
    package_to_classes = defaultdict(list)

    java_file_pattern = re.compile(r"\.java$")
    package_pattern = re.compile(r"^\s*package\s+([\w\.]+)\s*;")

    for root, dirs, files in os.walk(repo_root):
        for fname in files:
            if not java_file_pattern.search(fname):
                continue

            fullpath = os.path.join(root, fname)
            pkg_name = None
            try:
                with open(fullpath, "r", encoding="utf-8") as f:
                    for line in f:
                        m = package_pattern.match(line)
                        if m:
                            pkg_name = m.group(1)
                            break
            except (UnicodeDecodeError, IOError):
                continue

            class_name = fname[:-5]  # strip ".java"
            if pkg_name:
                fqn = f"{pkg_name}.{class_name}"
                package_to_classes[pkg_name].append(class_name)
            else:
                fqn = class_name
                package_to_classes[""].append(class_name)

            fqn_to_path[fqn] = fullpath

    return fqn_to_path, package_to_classes


def parse_imports_from_file(java_file_path):
    """
    Parse a Java file and extract all import statements. Returns a list of dicts.
    """
    imp_pattern = re.compile(
        r"^\s*import\s+" r"(static\s+)?" r"([\w\.]+)" r"(?:\.(\*|[\w]+))?" r"\s*;"
    )
    imports = []

    with open(java_file_path, "r", encoding="utf-8") as f:
        for line in f:
            m = imp_pattern.match(line)
            if not m:
                continue

            is_static = bool(m.group(1))
            base = m.group(2)
            suffix = m.group(3)

            if is_static:
                pkg_or_class = base
                member = suffix
                is_wild = suffix == "*"
            else:
                pkg_or_class = base
                member = None
                is_wild = suffix == "*"

            imports.append(
                {
                    "raw": line.strip(),
                    "is_static": is_static,
                    "package": pkg_or_class,
                    "member": member,
                    "is_wildcard": is_wild,
                }
            )

    return imports


def resolve_imported_classes(imports, fqn_to_path, package_to_classes):
    """
    From the parsed imports, build a set of all fully-qualified classes that are effectively imported,
    plus mappings for static imports.
    """
    imported_classes = set()
    static_member_map = {}
    static_wildcards = set()

    for imp in imports:
        pkg = imp["package"]
        is_wild = imp["is_wildcard"]
        is_static = imp["is_static"]
        member = imp["member"]

        if not is_static:
            if is_wild:
                pkg_name = pkg
                for cls_name in package_to_classes.get(pkg_name, []):
                    fqn = f"{pkg_name}.{cls_name}"
                    if fqn in fqn_to_path:
                        imported_classes.add(fqn)
            else:
                fqn = pkg
                if fqn in fqn_to_path:
                    imported_classes.add(fqn)
        else:
            if is_wild:
                class_fqn = pkg
                if class_fqn in fqn_to_path:
                    imported_classes.add(class_fqn)
                    static_wildcards.add(class_fqn)
            else:
                class_fqn = pkg
                const_name = member
                if class_fqn in fqn_to_path and const_name:
                    static_member_map[const_name] = (class_fqn, fqn_to_path[class_fqn])
                    imported_classes.add(class_fqn)

    return imported_classes, static_member_map, static_wildcards


def find_constants_in_class_file(class_path):
    """
    Given a .java file path, return a dict of public static final fields:
      { "CONST_NAME": "valueExpression", ... }
    """
    try:
        with open(class_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except (IOError, UnicodeDecodeError):
        return {}

    text = strip_java_comments(raw)
    const_pattern = re.compile(
        r"\bpublic\s+static\s+final\s+[\w\<\>\[\]]+\s+" r"([A-Za-z_]\w*)\s*=\s*([^;]+);"
    )

    constants = {}
    for m in const_pattern.finditer(text):
        name = m.group(1)
        val = m.group(2).strip()
        constants[name] = val

    return constants


def find_constant_usages(
    target_text, imported_classes, static_member_map, static_wildcards, fqn_to_constants
):
    """
    Scan target_text for usages of constants from imported classes. Return a dict:
      { usage_key: (valueExpression, classFQN) }
    """
    usages = {}

    # 1) Build lookup for "ClassName.CONST"
    for class_fqn in imported_classes:
        const_map = fqn_to_constants.get(class_fqn, {})
        if not const_map:
            continue
        class_name = class_fqn.split(".")[-1]
        for const_name, const_val in const_map.items():
            key = f"{class_name}.{const_name}"
            usages[key] = (const_val, class_fqn)

    # 2) Member-specific static imports
    for const_name, (class_fqn, _) in static_member_map.items():
        const_map = fqn_to_constants.get(class_fqn, {})
        if const_name in const_map:
            usages[const_name] = (const_map[const_name], class_fqn)

    # 3) Static wildcard imports
    for class_fqn in static_wildcards:
        const_map = fqn_to_constants.get(class_fqn, {})
        for const_name, const_val in const_map.items():
            if const_name not in usages:
                usages[const_name] = (const_val, class_fqn)

    # Filter to only those that appear in target_text
    found = {}
    for key, (val, cls) in usages.items():
        if "." in key:
            pattern = r"\b" + re.escape(key) + r"\b"
        else:
            pattern = r"\b" + re.escape(key) + r"\b"

        if re.search(pattern, target_text):
            found[key] = (val, cls)

    return found


def find_imported_constants_in_file(
    repo_root, target_file, fqn_to_path, package_to_classes
):
    """
    Given repo metadata and a target Java file, find and print all used constants
    defined in imported classes.
    """
    # 1) Parse imports from the target file
    imports = parse_imports_from_file(target_file)
    if not imports:
        # print("No import statements found in the target file.")
        return None

    # 2) Resolve imported classes & static-import patterns
    imported_classes, static_member_map, static_wildcards = resolve_imported_classes(
        imports, fqn_to_path, package_to_classes
    )

    target_dir = os.path.dirname(target_file)
    for fqn, path in fqn_to_path.items():
        if path == target_file:
            continue
        if os.path.dirname(path) == target_dir:
            # treat as if "imported" (non-static)
            imported_classes.add(fqn)

    if not imported_classes:
        # print("No imported classes could be resolved in the repository tree.")
        return None

    # print(f"Found {len(imported_classes)} imported classes:")
    # for cls in sorted(imported_classes):
    #     print(f"  • {cls}")

    # 3) For each imported class, parse its .java to extract public static final constants
    fqn_to_constants = {}
    for class_fqn in imported_classes:
        class_path = fqn_to_path.get(class_fqn)
        if class_path:
            const_map = find_constants_in_class_file(class_path)
            if const_map:
                fqn_to_constants[class_fqn] = const_map

    if not fqn_to_constants:
        # print("No public static final constants found in any of the imported classes.")
        return None

    # 4) Load and strip comments from the target file, then scan for usages
    with open(target_file, "r", encoding="utf-8") as f:
        raw_target = f.read()
    stripped_target = strip_java_comments(raw_target)

    found_constants = find_constant_usages(
        stripped_target,
        imported_classes,
        static_member_map,
        static_wildcards,
        fqn_to_constants,
    )

    if not found_constants:
        # print("No imported constants are used in the target file.")
        return None

    # 5) Print the results
    return found_constants


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python find_imported_constants.py <path_to_repo> <path_to_target_java_file>"
        )
        sys.exit(1)

    repo_root = os.path.abspath(sys.argv[1])
    target_file = os.path.abspath(sys.argv[2])

    if not os.path.isdir(repo_root):
        print(f"Error: {repo_root} is not a directory.")
        sys.exit(1)
    if not os.path.isfile(target_file) or not target_file.endswith(".java"):
        print(f"Error: {target_file} is not a .java file.")
        sys.exit(1)

    fqn_to_path, package_to_classes = build_repo_metadata(repo_root)

    found_constants = find_imported_constants_in_file(
        repo_root, target_file, fqn_to_path, package_to_classes
    )
    if found_constants is None:
        sys.exit(0)
    print(f"Constants used in {target_file} (defined in imported classes):\n")
    for usage_key, (value_expr, class_fqn) in sorted(found_constants.items()):
        class_path = fqn_to_path[class_fqn]
        print(f"  • {usage_key}")
        print(f"      → value = {value_expr}")
        print(f"      → defined in: {class_fqn}  ( {class_path} )\n")
