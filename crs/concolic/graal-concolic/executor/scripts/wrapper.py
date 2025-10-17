import glob
import subprocess
import os
from os import makedirs
from pathlib import Path


class Wrapper:
    SRCNAME = "Runner.java"
    CLSNAME = "Runner.class"

    def __init__(self, harness_info: dict, cp_metadata: dict, logger):
        self.cp_metadata = cp_metadata
        self.harness_full_classname = harness_info['target_class']
        self.harness_classname = self.harness_full_classname.split(".")[-1]

        system_java_home = os.environ['JAVA_HOME']
        if 'GRAALVM_ESPRESSO' in system_java_home:
            self.javac_path = Path(system_java_home) / "bin" / "javac"
        else:
            # in the container
            self.javac_path = Path(self._find_java_home('/graal-jdk/sdk/mxbuild/linux-amd64/')) / "bin" / "javac"
        self.logger = logger

    def _find_java_home(self, base_dir: str):
        try:
            espresso = list(glob.glob(f'{base_dir}/GRAALVM_ESPRESSO*'))[0]
            java_home = list(glob.glob(f'{espresso}/*jvm-ce*'))[0]
            return java_home
        except Exception as e:
            print("Cannot find java_home:", e)
            return "/usr"

    @staticmethod
    def exists(wrapper_dir: Path):
        return (wrapper_dir / Wrapper.CLSNAME).exists()

    def _save_wrapper_src(self, harness_path: Path, dst_srcpath: Path):
        def has_init(src) -> bool:
            return " void fuzzerInitialize()" in src

        def is_using_fdp(src) -> bool:
            return " void fuzzerTestOneInput(FuzzedDataProvider " in src

        def is_using_bytearr(src) -> bool:
            return " void fuzzerTestOneInput(byte[] " in src

        def get_header(src) -> str:
            if '.' in self.harness_full_classname:
                return f"""import java.util.*;
import java.io.*;
import java.nio.*;
import java.nio.file.Files;
import java.nio.file.Path;
{"import com.code_intelligence.jazzer.driver.FuzzedDataProviderImpl;" if is_using_fdp(src) else ""}
{"import com.code_intelligence.jazzer.api.FuzzedDataProvider;" if is_using_fdp(src) else ""}
import {self.harness_full_classname};
"""
            else:
                return f"""import java.util.*;
import java.io.*;
import java.nio.*;
import java.nio.file.Files;
import java.nio.file.Path;
{"import com.code_intelligence.jazzer.driver.FuzzedDataProviderImpl;" if is_using_fdp(src) else ""}
{"import com.code_intelligence.jazzer.api.FuzzedDataProvider;" if is_using_fdp(src) else ""}
"""


        def get_main(src) -> str:
            return f"""
    public static void main(String[] args) throws Throwable, Exception {{
        byte[] data = Files.readAllBytes(Path.of(args[0]));
{f"        {self.harness_classname}.fuzzerInitialize();" if has_init(src) else ""}
        startSymbolicExecutionBytes({"data" if is_using_bytearr(src) else "FuzzedDataProviderImpl.withJavaData(data)"});
    }}"""

        def get_entry(src):
            typ = "byte[]" if is_using_bytearr(src) else "FuzzedDataProvider"
            return f"""
    public static void startSymbolicExecutionBytes({typ} data) throws Throwable, Exception {{
        try {{
        System.out.println("=== CP START ===");
        {self.harness_classname}.fuzzerTestOneInput(data);
        System.out.println("=== CP FINISHED ===");
        }} catch (Throwable t) {{
            System.out.println("=== CP EXCEPTION ===");
            System.out.println("Exception: " + t.getMessage());
            t.printStackTrace(System.out);
        }}
    }}"""

        def get_runner(src):
            return f"public class Runner {{{get_main(src)}\n{get_entry(src)}\n}}\n"
        print(f"harness path {harness_path}")
        with open(harness_path) as f:
            src = f.read()

        print(f"dst path {dst_srcpath}")
        ret = f"{get_header(src)}\n{get_runner(src)}"
        with open(dst_srcpath, "w") as f:
            f.write(ret)

    def generate(self, classpath: str, harness_info: dict, dst_dir: Path):
        try:
            makedirs(dst_dir, exist_ok=True)
            print(f'Wrapper dst dir {dst_dir}')
            dst_srcpath = (dst_dir / self.SRCNAME).absolute()
            dst_clspath = (dst_dir / self.CLSNAME).absolute()

            print(f'Wrapper dst_srcpath {dst_srcpath}')
            print(f'Wrapper dst_clspath {dst_clspath}')

            cp_full_src_path = Path(self.cp_metadata['cp_full_src'])
            print(cp_full_src_path)
            print(harness_info['src_path'])
            harness_src_path = cp_full_src_path / harness_info['src_path']
            print(f'Harness src path {harness_src_path}')

            print("Generating wrapper src:", dst_srcpath)
            self._save_wrapper_src(harness_src_path, dst_srcpath)
            print("Compiling wrapper:", dst_clspath)
            cmd = [
                self.javac_path,
                "-cp",
                classpath,
                dst_srcpath,
            ]
            subprocess.run(cmd)
        except Exception as e:
            self.logger.error("Wrapper Error:", e)
