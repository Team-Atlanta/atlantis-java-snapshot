from typing import Optional
import json
import tarfile
import io
import gzip
import uuid
from pathlib import Path
import tempfile
import shutil
import os

import grpc
from google.protobuf.json_format import MessageToJson

from . import browser_pb2, browser_pb2_grpc
from .utils import deterministic_tarball_hash

SHARED_CRS_SPACE = os.environ.get("SHARED_CRS_SPACE", "/shared-crs-fs")
DEFAULT_SHARED_DIR =  str(Path(SHARED_CRS_SPACE) / 'crs-userspace/code-browser')

class CodeBrowserError(Exception):
    def __init__(self, message):
        super().__init__(message)

class CodeBrowserClient:
    def __init__(self, server_address: str = '[::1]:50051'):
        self.address = server_address
        self.channel = grpc.insecure_channel(self.address)
        self.stub = browser_pb2_grpc.CodeBrowserStub(self.channel)

        # raise exception if not server not ready
        request = browser_pb2.CodeRequest(name="", kind=browser_pb2.QUERY_FUNCTION, project=None)
        _response = self.stub.CodeQuery(request)

    def __query(self, name: str, kind: browser_pb2.QueryKind, relative: bool, project: Optional[str]):
        request = browser_pb2.CodeRequest(name=name, kind=kind, project=project, relative=relative)
        response = self.stub.CodeQuery(request)
        # horrible documentation https://github.com/protocolbuffers/protobuf/releases/tag/v26.0-rc2
        response_json = json.loads(MessageToJson(response, always_print_fields_with_no_presence=True, preserving_proto_field_name=True))

        if response_json['error']:
            raise CodeBrowserError(response_json['error'])

        definitions = response_json['definitions']
        return json.dumps(definitions, indent=2)

    def get_function_definition(self, name: str, project: Optional[str]=None, relative=False):
        return self.__query(name, browser_pb2.QUERY_FUNCTION, relative, project)

    def get_function_cross_references(self, name: str, project: Optional[str]=None, relative=False):
        return self.__query(name, browser_pb2.QUERY_XREF, relative, project)

    def get_struct_definition(self, name: str, project: Optional[str]=None, relative=False):
        return self.__query(name, browser_pb2.QUERY_STRUCT, relative, project)

    def get_enum_definition(self, name: str, project: Optional[str]=None, relative=False):
        return self.__query(name, browser_pb2.QUERY_ENUM, relative, project)

    def get_union_definition(self, name: str, project: Optional[str]=None, relative=False):
        return self.__query(name, browser_pb2.QUERY_UNION, relative, project)

    def get_typedef_definition(self, name: str, project: Optional[str]=None, relative=False):
        return self.__query(name, browser_pb2.QUERY_TYPEDEF, relative, project)

    def get_any_type_definition(self, name: str, project: Optional[str]=None, relative=False):
        return self.__query(name, browser_pb2.QUERY_ANY_TYPE, relative, project)

    def build(
            self,
            project: str,
            force: bool = False,
            shared: str = DEFAULT_SHARED_DIR,
    ):
        repo_path = Path(project).resolve()
        top_level_dir = repo_path.name

        # Create temporary tarball
        temp_tarball = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.tar.gz"
        tar_buffer = io.BytesIO()

        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        # with tarfile.open(temp_tarball, "w:gz") as tar:
            tar.add(repo_path, arcname=top_level_dir)

        # compress deterministically
        tar_buffer.seek(0)
        with open(temp_tarball, "wb") as f_out:
            with gzip.GzipFile(fileobj=f_out, mode="wb", mtime=0) as gz:
                gz.write(tar_buffer.read())

        # Calculate hash of tarball
        tarball_hash = deterministic_tarball_hash(temp_tarball)

        # Move to shared directory with hash name
        tarball = f"{tarball_hash}.tar.gz"
        output_path = Path(shared) / tarball
        output_path.parent.mkdir(exist_ok=True, parents=True)

        if not output_path.is_file():
            shutil.move(temp_tarball, output_path)

        request = browser_pb2.BuildRequest(project=project, force=force, tarball=tarball)
        response = self.stub.Build(request)
        return response
