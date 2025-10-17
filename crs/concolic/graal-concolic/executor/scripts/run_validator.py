import subprocess
import sys
import os
import glob

os.environ["LD_DEBUG"] = "unused"

if len(sys.argv) != 4:
    print("Usage: python run_validator.py <graal-home-path> <cp-path> <class-name>")
    sys.exit(1)

graal_home = os.path.realpath(sys.argv[1])
cp_path = os.path.realpath(sys.argv[2])
class_name = sys.argv[3]

# Build the project
gradle_args = [
    "./gradlew",
    "build",
    "-Dorg.gradle.java.home=" + graal_home,
]
subprocess.run(" ".join(gradle_args), shell=True)

main_args = [
    "-c", cp_path,
    "-T", class_name,
]
run_args = [
    os.path.join(graal_home, "bin/java"),
    "-cp", "app/build/libs/app.jar",
    "executor.Validator",
    *main_args,
]

subprocess.run(" ".join(run_args), shell=True)
