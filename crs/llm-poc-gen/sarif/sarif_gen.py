import json
import sys
from pathlib import Path

from jinja2 import Template

SARIF_RULES_JAVA = [
    {
        "id": "FuzzerSecurityIssueCritical: OS Command Injection",
        "shortDescription": {"text": "OS Command Injection."},
        "helpUri": "https://cwe.mitre.org/data/definitions/78.html",
    },
    {
        "id": "FuzzerSecurityIssueCritical: Integer Overflow",
        "shortDescription": {"text": "Integer Overflow."},
        "helpUri": "https://cwe.mitre.org/data/definitions/190.html",
    },
    {
        "id": "FuzzerSecurityIssueMedium: Server Side Request Forgery (SSRF)",
        "shortDescription": {"text": "Server Side Request Forgery (SSRF)."},
        "helpUri": "https://cwe.mitre.org/data/definitions/918.html",
    },
    {
        "id": "FuzzerSecurityIssueHigh: Remote Code Execution",
        "shortDescription": {"text": "Remote Code Execution."},
        # TODO: map to CWE (CWE-94???)
        "helpUri": "https://cwe.mitre.org/data/definitions/94.html",
    },
    {
        "id": "FuzzerSecurityIssueHigh: SQL Injection",
        "shortDescription": {"text": "SQL Injection."},
        "helpUri": "https://cwe.mitre.org/data/definitions/89.html",
    },
    {
        "id": "FuzzerSecurityIssueCritical: Remote JNDI Lookup",
        "shortDescription": {"text": "Remote JNDI Lookup."},
        # TODO: map to CWE (CWE-502???)
        "helpUri": "https://cwe.mitre.org/data/definitions/502.html",
    },
    {
        "id": "FuzzerSecurityIssueCritical: LDAP Injection",
        "shortDescription": {"text": "LDAP Injection."},
        "helpUri": "https://cwe.mitre.org/data/definitions/90.html",
    },
    {
        "id": "FuzzerSecurityIssueHigh: XPath Injection",
        "shortDescription": {"text": "XPath Injection."},
        "helpUri": "https://cwe.mitre.org/data/definitions/643.html",
    },
    {
        "id": "FuzzerSecurityIssueHigh: load arbitrary library",
        "shortDescription": {"text": "load arbitrary library."},
        # TODO: map to CWE (No idea)
        "helpUri": "https://cwe.mitre.org/data/definitions/",
    },
    {
        "id": "FuzzerSecurityIssueLow: Regular Expression Injection",
        "shortDescription": {"text": "Regular Expression Injection."},
        # TODO: map to CWE (CWE-777????)
        "helpUri": "https://cwe.mitre.org/data/definitions/777.html",
    },
    {
        "id": "FuzzerSecurityIssueCritical: Script Engine Injection",
        "shortDescription": {"text": "Script Engine Injection."},
        # TODO: map to CWE (CWE-94???)
        "helpUri": "https://cwe.mitre.org/data/definitions/94.html",
    },
    {
        "id": "FuzzerSecurityIssueCritical: File read/write hook path",
        "shortDescription": {"text": "File read/write hook path."},
        # TODO: map to CWE (CWE-22???)
        "helpUri": "https://cwe.mitre.org/data/definitions/22.html",
    },
]


def to_jazzer_sanitizer(v_type: str) -> str:
    return next(
        (rule["id"] for rule in SARIF_RULES_JAVA if rule["id"].endswith(v_type)), ""
    )


def read_json(filepath: Path) -> dict:
    try:
        with filepath.open("r") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading {filepath}: {e}")
        return {}


def load_template(template_path: Path) -> Template:
    return Template(template_path.read_text())


def load_blackboard(base_dir: Path) -> dict:
    return {file.parent.name: read_json(file) for file in base_dir.rglob("blackboard")}


def process_tasks(data: dict) -> dict:
    code_flows = {}
    for task in data.get("tasks", []):
        locations = [
            {
                "uri": path["path"],
                "fullyQualifiedName": path["method"],
                "startLine": path["line"],
                "startColumn": path["column"],
            }
            for path in task["paths"]
        ]
        sink = task["paths"][-1]
        key = (task["sanitizer"], sink["path"], sink["line"], sink["column"])
        code_flows.setdefault(key, []).append({"locations": locations})
    return code_flows


def process_sinks(code_flows: dict, data: dict) -> list:
    results = []
    for v_type, locations in data.get("sinks", {}).items():
        for loc in locations:
            key = (v_type, loc["path"], loc["line"], loc["column"])
            result = {
                "ruleId": to_jazzer_sanitizer(v_type),
                "message": v_type,
                "locations": [
                    {
                        "uri": loc["path"],
                        "startLine": loc["line"],
                        "startColumn": loc["column"],
                    }
                ],
                "flow": key in code_flows,
                "codeFlows": code_flows.get(key, []),
            }
            results.append(result)
    return results


def render_template(template: Template, **kwargs) -> str:
    return json.dumps(json.loads(template.render(**kwargs)), indent=4)


def save_output(cp: str, output: str):
    output_path = Path(f"generated/{cp}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output)


def create_sarif(sarif_template: Template, cp: str, blackboard: dict):
    code_flows = process_tasks(blackboard)
    results = process_sinks(code_flows, blackboard)
    output = render_template(
        sarif_template, results=results, rules=json.dumps(SARIF_RULES_JAVA)
    )
    save_output(cp, output)


if __name__ == "__main__":
    base_dir, tmpl_dir = map(Path, sys.argv[1:3])
    template = load_template(tmpl_dir / "template.jinja")
    blackboards = load_blackboard(base_dir)

    for cp, blackboard in blackboards.items():
        create_sarif(template, cp, blackboard)
