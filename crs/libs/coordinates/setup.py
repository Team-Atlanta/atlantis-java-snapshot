import os
import shutil
import subprocess

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py


class CustomBuildCommand(build_py):
    def run(self):
        # 1. build Java proj
        java_project_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "bytecode-parser")
        )
        print("Building Java project with Maven...")
        try:
            subprocess.run(
                ["mvn", "clean", "package", "assembly:single"],
                cwd=java_project_dir,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Java build failed: {e.stderr}") from e

        # 2. build Jar to Python package
        jar_source = os.path.join(
            java_project_dir,
            "target",
            "bytecode-parser-1.0-SNAPSHOT-jar-with-dependencies.jar",
        )
        if not os.path.exists(jar_source):
            raise FileNotFoundError(f"Built Jar file '{jar_source}' not found.")

        target_dir = os.path.join(os.path.dirname(__file__), "coordinates")
        jar_target = os.path.join(target_dir, "bytecode-parser.jar")
        shutil.copy(jar_source, jar_target)
        print(f"Copied Jar to Python package: {jar_target}")

        # 3. normal Python build process
        build_py.run(self)


setup(
    name="coordinates",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ],
    },
    author="Cen Zhang",
    description="Python wrapper for mapping between Java bytecode lvl and source code lvl coordinate.",
    python_requires=">=3.6",
    cmdclass={
        "build_py": CustomBuildCommand,
    },
    include_package_data=True,
    package_data={
        "coordinates": ["bytecode-parser.jar"],
    },
)
