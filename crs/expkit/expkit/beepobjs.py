#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
from typing import Any, Dict


class InsnCoordinate:
    """Unique coorindate of an insn in bytecode."""

    def __init__(
        self,
        class_name: str,
        method_name: str,
        method_desc: str,
        bytecode_offset: int,
        mark_desc: str,
        file_name: str,
        line_num: int,
    ):
        self.class_name = class_name
        self.method_name = method_name
        self.method_desc = method_desc
        self.bytecode_offset = bytecode_offset
        self.mark_desc = mark_desc
        self.file_name = file_name
        self.line_num = line_num

        has_src_info = self.mark_desc and self.file_name and self.line_num != -1
        has_bytecode_info = (
            self.mark_desc
            and self.class_name
            and self.method_name
            and self.method_desc
            and self.bytecode_offset != -1
        )
        if not has_src_info and not has_bytecode_info:
            raise ValueError(
                f"Incomplete info in InsnCoordinate: src_info {has_src_info}, bytecode_info {has_bytecode_info}, {self.__dict__}"
            )
        if self.class_name is not None:
            self.class_name = self.class_name.replace("/", ".")

    @classmethod
    def frm_dict(cls, coord_dict: Dict[str, Any]) -> "InsnCoordinate":
        return cls(
            class_name=coord_dict.get("class_name", None),
            method_name=coord_dict.get("method_name", None),
            method_desc=coord_dict.get("method_desc", None),
            bytecode_offset=int(coord_dict.get("bytecode_offset") or -1),
            mark_desc=coord_dict.get("mark_desc", None),
            file_name=coord_dict.get("file_name", None),
            line_num=int(coord_dict.get("line_num") or -1),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "method_name": self.method_name,
            "method_desc": self.method_desc,
            "bytecode_offset": self.bytecode_offset,
            "mark_desc": self.mark_desc,
            "file_name": self.file_name,
            "line_num": self.line_num,
        }

    def _is_in_stack_frame(self, frame: str) -> bool:
        return (f"{self.class_name}.{self.method_name}") in frame and (
            f"({self.file_name}:{self.line_num})"
        ) in frame

    def is_in_stack_frames(self, frames: list[str]) -> bool:
        for frame in frames:
            if self._is_in_stack_frame(frame):
                return True
        return False

    def redis_key(self) -> str:
        """Get a Redis key for the InsnCoordinate."""
        return f"coord#{self.class_name}#{self.method_name}#{self.method_desc}#{self.bytecode_offset}#{self.file_name}#{self.line_num}#{self.mark_desc}"

    def key_shasum(self) -> str:
        """Get a SHA1 hash of the key components."""
        key_str = (
            f"{self.class_name}#{self.method_name}#{self.method_desc}#"
            f"{self.bytecode_offset}#{self.file_name}#{self.line_num}#{self.mark_desc}"
        )
        return hashlib.sha1(key_str.encode("utf-8")).hexdigest()

    def __hash__(self):
        return hash(
            (
                self.class_name,
                self.method_name,
                self.method_desc,
                self.bytecode_offset,
                self.file_name,
                self.line_num,
            )
        )

    def __eq__(self, other: Any):
        try:
            return (
                self.class_name == other.class_name
                and self.method_name == other.method_name
                and self.method_desc == other.method_desc
                and self.bytecode_offset == other.bytecode_offset
                and self.file_name == other.file_name
                and self.line_num == other.line_num
            )
        except AttributeError:
            return False

    def __str__(self):
        return f"sink @ <{self.class_name} {self.method_name} {self.method_desc} {self.bytecode_offset} {self.file_name} {self.line_num} {self.mark_desc}>"

    def __repr__(self):
        return (
            f"InsnCoordinate(class_name='{self.class_name}', "
            f"method_name='{self.method_name}', "
            f"method_desc='{self.method_desc}', "
            f"bytecode_offset={self.bytecode_offset}, "
            f"mark_desc='{self.mark_desc}', "
            f"file_name='{self.file_name}', "
            f"line_num={self.line_num})"
        )


class BeepSeed:
    """beepseed is an input reaching a marked code point."""

    def __init__(
        self,
        target_cp: str,
        target_harness: str,
        data_sha1: str,
        data_hex_str: str | None,
        data_len: int,
        coord: InsnCoordinate,
        stack_hash: str,
        stack_trace: list | None,
        json_obj: Dict[str, Any],
    ):
        self.target_cp = target_cp
        self.target_harness = target_harness
        self.data_sha1 = data_sha1
        self.data_hex_str = data_hex_str
        self.data_len = data_len
        self.coord = coord
        # NOTE: stack_hash is about beepseed exec stacks
        self.stack_hash = stack_hash
        self.stack_trace = stack_trace
        self.json_obj = json_obj

    @classmethod
    def frm_dict(cls, dict_obj: Dict[str, Any]) -> "BeepSeed":
        """Create a BeepSeed object from a dictionary."""
        return cls(
            target_cp=dict_obj["target_cp"],
            target_harness=dict_obj["target_harness"],
            data_sha1=dict_obj["data_sha1"],
            data_hex_str=dict_obj.get("data", None),
            data_len=dict_obj["data_len"],
            coord=InsnCoordinate.frm_dict(dict_obj["coordinate"]),
            stack_hash=dict_obj["stack_hash"],
            stack_trace=dict_obj.get("stack_trace", None),
            json_obj=dict_obj,
        )

    @classmethod
    def frm_beep_file(cls, json_path: Path) -> "BeepSeed":
        """Create a BeepSeed object from a JSON file path."""
        with open(json_path) as f:
            json_obj = json.loads(f.read(-1))

        json_obj["data_len"] = len(json_obj["data"]) // 2 if "data" in json_obj else 0
        return cls.frm_dict(json_obj)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the BeepSeed object to a JSON-serializable dictionary."""
        return {
            "target_cp": self.target_cp,
            "target_harness": self.target_harness,
            "data_sha1": self.data_sha1,
            "data": self.data_hex_str,
            "data_len": self.data_len,
            "coordinate": self.coord.to_dict(),
            "stack_hash": self.stack_hash,
            "stack_trace": self.stack_trace,
        }

    def is_empty_data(self) -> bool:
        return self.data_len == 0

    def filter_frames_from_codemarker(self, stack_frames=None):
        """Filter strategy: Remove frames starting from codemarker report function."""
        if stack_frames is None:
            stack_frames = self.stack_trace

        if not stack_frames:
            return []

        filtered_frames = []
        for frame in stack_frames[::-1]:
            frame_str = frame.get("frame_str", "")

            # Stop when we find the codemarker instrumentation frame
            if (
                "com.code_intelligence.jazzer.api.Jazzer.reportCodeMarkerHit(Jazzer.java:229)"
                in frame_str
            ):
                break

            filtered_frames.append(frame_str)
        filtered_frames.reverse()
        return filtered_frames

    def get_bytes(self) -> bytes:
        """Get the data bytes from the hex string."""
        if self.data_hex_str:
            return bytes.fromhex(self.data_hex_str)
        return b""

    def redis_key(self) -> str:
        """Get a unique ID for the BeepSeed."""
        return f"beep#{self.data_sha1}#{self.coord.redis_key()}"

    def __hash__(self):
        return hash((self.coord, self.data_sha1))

    def __eq__(self, other):
        try:
            return self.coord == other.coord and self.data_sha1 == other.data_sha1
        except AttributeError:
            return False

    def __str__(self):
        return f"beep <{self.coord}, {self.stack_hash}, {self.data_sha1}, {self.data_len} bytes>"

    def __repr__(self):
        return (
            f"BeepSeed(target_cp='{self.target_cp}', "
            f"target_harness='{self.target_harness}', "
            f"data_sha1='{self.data_sha1}', "
            f"data_hex_str={self.data_hex_str}, "
            f"data_len={self.data_len}, "
            f"coord={self.coord}, "
            f"stack_hash='{self.stack_hash}', "
            f"stack_trace={self.stack_trace})"
        )
