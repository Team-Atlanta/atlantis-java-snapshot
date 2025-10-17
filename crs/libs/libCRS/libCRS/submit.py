import time
import json
import argparse
from base64 import b64encode
import glob
import hashlib
import logging
import os
from pathlib import Path
import re
import sqlite3
from tabulate import tabulate
import traceback

import requests

from .util import get_env, rm

WORKDIR = Path(get_env("CRS_WORKDIR", must_have=True, default="/crs-workdir/"))


def get_sanitizer():
    return get_env("SANITIZER", must_have=True)


def file_hash(path: Path) -> str:
    data = b""
    if path.exists():
        with open(path, "rb") as f:
            data += f.read()
    return hashlib.sha1(data).hexdigest()


class Status:
    PENDING = "pending"
    ACCEPT = "accepted"
    REJECT = "rejected"
    DUPLICATED = "duplicated"


class VAPI:
    def __init__(self):
        self.host = get_env("VAPI_HOST")

    def log(self, msg):
        logging.info(f"[VAPI] {msg}")

    def __request(self, action, body=None):
        if self.host is None:
            self.log(f"Skip {action}: VAPI_HOST is not set")
            return
        res = requests.post(
            f"{self.host}/{action}",
            json=body,
        )
        try:
            return res.json()
        except Exception:
            raise ValueError(res.text)

    def submit_vd(self, harness: str, pov: Path, finder: str) -> str:
        body = {
            "sanitizer": get_sanitizer(),
            "finder": finder,
            "fuzzer_name": harness,
            "testcase": b64encode(pov.read_bytes()).decode("ascii"),
        }
        result = self.__request("submit/pov/", body)
        if result is None:
            return ""
        if result.get("status", "") != "accepted" or "pov_id" not in result:
            raise RuntimeError(f"Unexpected response from submit/pov: {result}")
        return result["pov_id"]


class SubmitDB:
    def __init__(self, workdir: Path | None = None):
        self.vapi = VAPI()
        if workdir:
            self.workdir = workdir
        else:
            self.workdir = WORKDIR / "submit"
        os.makedirs(str(self.workdir), exist_ok=True)
        self.db_path = self.workdir / "submit.db"
        self.db = sqlite3.connect(str(self.db_path))
        self.__create_db()

    def __get_time(self):
        start_time = int(get_env("START_TIME", must_have=True))
        return int(time.time()) - start_time

    def __create_db(self):
        try:
            self.db.cursor().execute(
                "CREATE TABLE vd(uuid, harness, pov, status, sanitizer_output, finder, time)"
            )
        except Exception:
            pass

    def __add_vd(self, data):
        q = "insert into vd(uuid, harness, pov, status, sanitizer_output, finder, time) values(?,?,?,?,?,?,?)"
        data = tuple(list(data) + [self.__get_time()])
        self.db.cursor().execute(q, tuple(map(str, data)))
        self.db.commit()

    def __update_vd_status(self, uuid, status):
        query = "update vd set status = ? where uuid = ?"
        self.db.cursor().execute(query, (status, uuid))
        self.db.commit()

    def __submitted_vd(
        self, harness: str, pov: Path, sanitizer_output: str, finder: str
    ) -> bool:
        res = self.db.cursor().execute(
            "SELECT * from vd where sanitizer_output = ? and harness = ?",
            (sanitizer_output, harness),
        )
        res = list(res.fetchall())
        if len(res) == 0:
            return False
        finders = [x[5] for x in res]
        if finder not in finders:
            self.__add_vd(
                ("", harness, pov, Status.DUPLICATED, sanitizer_output, finder)
            )
        return True

    def submit_vd(
        self,
        harness: str,
        pov_path: Path,
        sanitizer_output: str,
        finder: str,
    ):
        if sanitizer_output == "":
            sanitizer_output = file_hash(pov_path)
        if self.__submitted_vd(harness, pov_path, sanitizer_output, finder):
            return
        uuid = self.vapi.submit_vd(harness, pov_path, finder)
        self.__add_vd(
            (uuid, harness, pov_path, Status.PENDING, sanitizer_output, finder)
        )

    def __show_vds(self, target_harness, fmt, for_vd_eval=False):
        headers = [
            "Status",
            "Finder",
            "Harness",
            "PoV",
            "UUID",
            "Sanitizer Output",
            "Time (s)",
        ]
        res = self.db.cursor().execute("SELECT * from vd")
        data = []
        for item in res.fetchall():
            (uuid, harness, pov, status, sanitizer_output, finder, time) = item
            if for_vd_eval:
                pov = pov.split("/")[-1]
            if target_harness == "" or target_harness == harness:
                data.append(
                    (status, finder, harness, pov, uuid, sanitizer_output, time)
                )
        if fmt == "json":
            table = []
            for d in data:
                tmp = {}
                for i in range(len(headers)):
                    tmp[headers[i]] = d[i]
                table.append(tmp)
            table = json.dumps(table)
        else:
            table = tabulate(data, headers=headers, tablefmt=fmt)
        print(table)

    def show(self, harness, fmt, for_vd_eval=False):
        if for_vd_eval:
            self.__show_vds(harness, fmt, True)
        else:
            print(f"\n[DB] {self.db_path}")
            self.__show_vds(harness, fmt)


def main_submit_vd(args: argparse.Namespace) -> None:
    SubmitDB().submit_vd(
        args.harness,
        args.pov,
        args.sanitizer_output,
        args.finder,
    )


def main_show(args: argparse.Namespace) -> None:
    for cand in [str(WORKDIR / "submit")] + glob.glob(f"{WORKDIR}/*/submit"):
        cand = Path(cand)
        if cand.exists():
            SubmitDB(cand).show(args.harness, args.format, args.for_vd_eval)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(title="commands", required=True)

    # Submit VD
    parser_vd = subparsers.add_parser(
        "submit_vd",
        help="submit a vulnerability discovery to the verifier API"
        " (which in turn submits it to the competition API if appropriate)",
    )
    parser_vd.set_defaults(func=main_submit_vd)
    parser_vd.add_argument(
        "--harness",
        required=True,
        help='harness name ("harnesses" key from project.yaml, e.g., "id_1")',
    )
    parser_vd.add_argument(
        "--pov",
        type=Path,
        required=True,
        help="path to the proof-of-vulnerability blob, aka the input data to the harness",
    )
    parser_vd.add_argument(
        "--finder",
        type=str,
        default="",
        help="finder (module) name of the provided pov",
    )
    parser_vd.add_argument(
        "--sanitizer-output",
        type=str,
        default="",
        help="sanitizer output representing the uniqueness of pov",
    )

    # Show Status
    parser_show = subparsers.add_parser("show", help="show the current status")
    parser_show.add_argument(
        "--harness",
        help='harness name ("harnesses" key from project.yaml, e.g., "id_1")',
        default="",
    )
    parser_show.add_argument("--format", help="output format", default="grid")
    parser_show.add_argument(
        "--for-vd-eval", help="for_vd_eval", default=False, action="store_true"
    )
    parser_show.set_defaults(func=main_show)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
