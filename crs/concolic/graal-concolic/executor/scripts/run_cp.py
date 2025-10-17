import subprocess
import sys
import os
import glob

os.environ["LD_DEBUG"] = "unused"

if len(sys.argv) != 4:
    print("Usage: python run_cp.py <graal-home-path> <cp_directory_path which have Makefile> <input_path>")
    sys.exit(1)

graal_home = os.path.realpath(sys.argv[1])
cp_path = os.path.realpath(sys.argv[2])
input_path = os.path.realpath(sys.argv[3])

classpath_info = None
for line in open(os.path.join(cp_path, "Makefile")):
    line = line.strip()
    classpath_prefix = "CLASSPATH:="
    if line.startswith(classpath_prefix):
        classpath_info = line.split(":=")[1].strip()
        break
    if " -cp " in line:
        classpath_info = line.split(" -cp ")[1].strip()
        classpath_info = classpath_info.strip("\"")
        if "\"" in classpath_info:
            classpath_info = classpath_info[:classpath_info.index("\"")]

classpath_info = classpath_info.strip("\"'")
classpath_info = classpath_info.strip()

result_list = []
classpath_list = classpath_info.split(":")
for single_classpath in classpath_list:
    single_classpath = single_classpath.strip()
    for each_filepath in glob.glob(os.path.join(cp_path, single_classpath)):
        each_filepath = os.path.realpath(each_filepath)
        # print(each_filepath)
        result_list.append(each_filepath)

converted_classpath = ":".join(result_list)

main_args = [
    "--server", "0",
    "--concolic-classpath", converted_classpath,
    "--concolic-target", "Runner",
    "--concolic-args", input_path,
    "--outdir", "/tmp",
]

#./gradlew run -Dorg.gradle.java.home=<path-to-graal-jdk-17> --args="../../tests/Simple HelloWorld 1234
gradle_args = [
    "./gradlew",
    "build",
    "-Dorg.gradle.java.home=" + graal_home,
    # "--args=\"{0}\"".format(" ".join(main_args))
]

# print(classpath_info)
subprocess.run(" ".join(gradle_args), shell=True)
# print(" ".join(gradle_args))


run_args = [
    os.path.join(graal_home, "bin/java"),
    "-cp", "app/build/libs/app.jar",
    # "-XX:-CompactStrings",
    "executor.App",
    *main_args,
]

subprocess.run(" ".join(run_args), shell=True)
# print(" ".join(gradle_args))