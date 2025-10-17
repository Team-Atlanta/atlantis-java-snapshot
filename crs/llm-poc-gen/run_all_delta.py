import os
import subprocess
import sys
from pathlib import Path

projects = [
    # "aixcc/jvm/geonetwork",
    # "aixcc/jvm/beanutils",
    # "aixcc/jvm/batik",
    # "aixcc/jvm/oripa",
    # "aixcc/jvm/widoco",
    # "aixcc/jvm/pac4j",
    # "aixcc/jvm/imaging",
    # "aixcc/jvm/ztzip",
    # "aixcc/jvm/jakarta-mail-api",
    # "aixcc/jvm/bcel",
    # "aixcc/jvm/jackson-databind",
    # "aixcc/jvm/fuzzy",
    # "aixcc/jvm/zookeeper",
    # "aixcc/jvm/aerospike",
    # "aixcc/jvm/htmlunit",
    # "aixcc/jvm/kylin",
    # "aixcc/jvm/olingo",
    # "aixcc/jvm/tika",
    "aixcc/jvm/activemq"
]

root_dir: Path = Path(__file__).parent
out_dir: Path = root_dir / "eval_delta"

for project in projects:
    print(f"Start {project}")
    project_dir: Path = out_dir / project
    os.makedirs(project_dir, exist_ok=True)
    calltree: Path = project_dir / "calltree.db"
    if calltree.exists():
        calltree.unlink()
    cmd = [
        sys.executable,
        "-m",
        "run_delta",
        "--cp_meta",
        f"/crs-workdir/worker-0/metadata/{project}/cpmeta.json",
        "--joern_dir",
        os.getenv("JOERN_DIR"),
        "--log_level",
        "DEBUG",
        "--output_dir",
        str(project_dir),
        "--model_cache",
        "cache",
    ]
    print(f"A1: {" ".join(cmd)}")
    log_file = project_dir / "log.txt"
    with open(log_file, "w") as f:
        subprocess.run(cmd, stdout=f, stderr=f)
