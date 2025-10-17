import json
import sys
import traceback

from javacrs_modules.base_objs import SarifAnalysisResult


def test_parse():
    if len(sys.argv) <= 1:
        print("Usage: python test.py <json_string>")
        return

    sample_json = ""
    with open(sys.argv[1]) as f:
        sample_json = f.read()
    data = json.loads(sample_json)
    try:
        result = SarifAnalysisResult(**data)
        print("Parsed Successfully!")
        print("sarif_id:", result.sarif_id)
        print("reachable_harness:", result.reachable_harness)
        for idx, r in enumerate(result.reachability_results):
            print(f"Result #{idx}:")
            print("  File:", r.code_location.file)
            print("  Function:", r.code_location.function)
            print("  Start Line:", r.code_location.start_line)
            print("  End Line:", r.code_location.end_line)
            print("  Start Column:", r.code_location.start_column)
            print("  End Column:", r.code_location.end_column)

    except Exception as e:
        print("Parse fail:", e)
        print(traceback.format_exc())


if __name__ == "__main__":
    test_parse()
