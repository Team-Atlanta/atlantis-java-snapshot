from pathlib import Path

from libDeepGen.tasks.harness_seedgen import JavaHarnessSeedGen
from libDeepGen.engine import DeepGenEngine
from libDeepGen.submit import LocalFSEnsemblerSubmit

def main():
    task = JavaHarnessSeedGen(
        cp_name="rdf4j",
        cp_src=Path("/data/workspace/libDeepGen/cps/repos/aixcc/jvm/rdf4j"),
        fuzz_tooling_src=Path("/data/workspace/libDeepGen/cps/fuzz-tooling"),
        harness_src=Path("/data/workspace/libDeepGen/cps/fuzz-tooling/projects/aixcc/jvm/rdf4j/fuzz/rdf4j-harness-one/src/main/java/com/aixcc/rdf4j/harnesses/one/Rdf4jOne.java"),
        harness_entrypoint_func="fuzzerTestOneInput",
    )
    
    with DeepGenEngine(core_ids=[0, 1], model="claude-3-7-sonnet-20250219", 
                      submit_class=LocalFSEnsemblerSubmit) as engine:
        engine.run(tasks=[task])

if __name__ == "__main__":
    main()
