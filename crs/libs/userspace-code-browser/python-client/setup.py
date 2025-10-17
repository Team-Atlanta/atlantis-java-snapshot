from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
import subprocess
import os
from pathlib import Path

class BuildProtos(build_py):
    def run(self):
        this_dir = Path(__file__).parent.resolve()
        root_dir = this_dir.parent
        out_dir = this_dir / Path("code_browser_client")
        proto_dir = root_dir / 'proto'
        if not out_dir.is_dir():
            os.makedirs(out_dir)

        subprocess.run([
            "python", "-m", "grpc_tools.protoc",
            f"-I{proto_dir}",
            "--python_out=.",
            "--grpc_python_out=.",
            f"{proto_dir}/browser.proto"
        ], check=True, cwd=out_dir)

        subprocess.run([
            "protol",
            "--create-package",
            "--in-place",
            "--python-out", ".",
            "protoc",
            f"--proto-path={proto_dir}",
            f"{proto_dir}/browser.proto"
        ], check=True, cwd=out_dir)

        super().run()

setup(
    packages=find_packages(),
    cmdclass={"build_py": BuildProtos},
)
