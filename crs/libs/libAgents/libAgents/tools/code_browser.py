import os
import sys
import signal
import atexit
import threading
import time
import sqlite3
import socket
import subprocess
import psutil
import weakref
import tempfile
import filelock
import grpc
from pathlib import Path
from code_browser_client import CodeBrowserClient
import logging

DB_FILE = Path(tempfile.gettempdir()) / "code_browser_registry.db"
LOCK_FILE = Path(tempfile.gettempdir()) / "code_browser_registry.db.lock"
MAX_STALE_AGE = 300  # seconds

_db_lock = threading.Lock()
_file_lock = filelock.FileLock(str(LOCK_FILE))

logger = logging.getLogger(__name__)


def _init_db():
    conn = sqlite3.connect(str(DB_FILE), timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS servers (
            path TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            port INTEGER NOT NULL,
            pid INTEGER NOT NULL,
            last_seen REAL NOT NULL
        )
        """
    )
    return conn


def _allocate_port(address: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((address, 0))
        return sock.getsockname()[1]


def _is_alive(pid: int) -> bool:
    return psutil.pid_exists(pid) and psutil.Process(pid).is_running()


def _check_grpc(addr: str, port: int, retries: int = 200, delay: float = 1) -> bool:
    target = f"{addr}:{port}"
    last_exception = None
    for i in range(retries):
        try:
            CodeBrowserClient(target)
            logger.debug(f"GRPC check attempt {i + 1}/{retries} succeeded for {target}")
            return True
        except Exception as e:
            last_exception = e
            # traceback.print_exc(file=sys.stderr)
            time.sleep(delay)

    logger.error(
        f"GRPC check failed for {target} after {retries} attempts (interval: {delay}s)"
    )
    if last_exception:
        logger.error(f"Last error: {last_exception}")
    return False


def _cleanup_stale():
    now = time.time()
    conn = None
    try:
        with _file_lock:
            conn = _init_db()
            to_remove = []
            for path, address, port, pid, last_seen in conn.execute(
                "SELECT * FROM servers"
            ):  # type: ignore
                if not _is_alive(pid) or now - last_seen > MAX_STALE_AGE:
                    to_remove.append((path, pid))
            for path, pid in to_remove:
                try:
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
                conn.execute("DELETE FROM servers WHERE path = ?", (path,))
            conn.commit()
    finally:
        if conn:
            conn.close()


def _cleanup_all():
    conn = None
    try:
        with _file_lock:
            conn = _init_db()
            for path, address, port, pid, _ in conn.execute("SELECT * FROM servers"):  # type: ignore
                if _is_alive(pid):
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:
                        pass
            conn.execute("DELETE FROM servers")
            conn.commit()
    finally:
        if conn:
            conn.close()


# Register cleanup hooks
atexit.register(_cleanup_all)
for _sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(_sig, lambda s, f: (_cleanup_all(), sys.exit(0)))


class CodeBrowser:
    """
    Context-managed code-browser client.
    Ensures single server per src_path, with DB-backed registry.
    """

    def __init__(self, project_name: str, src_path: str):
        self.project_name = project_name
        self.src_path = os.path.realpath(src_path)  # make sure a real path
        self.daemon = os.environ.get("CODE_BROWSER_ADDRESS", None)
        self.server_port = None

        # self.db_client = CodeBrowserClient("127.0.0.1:8848")

        if self.daemon is None:
            _cleanup_stale()
            self._ensure_server()
            # register finalize to auto shutdown on GC
            weakref.finalize(self, self.shutdown)
            self._lock_acquired = False
            logger.info("Code browser client initialized with self-managed server")
        else:
            cnt = 0
            while cnt < 120:
                try:
                    self.db_client = CodeBrowserClient(f"{self.daemon}")
                    logger.info("start building code browser client with daemon")
                    self.db_client.build(self.src_path)
                except grpc.RpcError as e:
                    logger.error(f"Error initializing code browser client with daemon: {e} , retrying... {cnt}/120")
                    if e.code() == grpc.StatusCode.UNAVAILABLE:
                        time.sleep(1)
                        cnt += 1
                        continue
                    else:
                        raise
                except Exception as e:
                    logger.error(
                        "Error initializing code browser client with daemon: %s", e
                    )
                    time.sleep(1)
                    cnt += 1
                    continue
                break
            self.server_port = int(self.daemon.split(":")[1])
            logger.info("Code browser client initialized with daemon: %s", self.daemon)

    def _ensure_server(self):
        conn = None
        try:
            with _file_lock:
                self._lock_acquired = True
                with _db_lock:
                    conn = _init_db()
                    conn.execute("BEGIN IMMEDIATE;")
                    try:
                        row = conn.execute(
                            "SELECT address, port, pid FROM servers WHERE path = ?",
                            (self.src_path,),
                        ).fetchone()
                        if row:
                            addr, port, pid = row
                            if _is_alive(pid) and _check_grpc(addr, port, retries=3):
                                conn.execute(
                                    "UPDATE servers SET last_seen = ? WHERE path = ?",
                                    (time.time(), self.src_path),
                                )
                                conn.commit()
                                self._attach_client(addr, port, pid)
                                return
                            # stale entry: remove
                            conn.execute(
                                "DELETE FROM servers WHERE path = ?", (self.src_path,)
                            )
                            conn.commit()

                        # start new server
                        addr, port, pid = self._start_server()
                        conn.execute(
                            "INSERT OR REPLACE INTO servers(path, address, port, pid, last_seen) VALUES(?, ?, ?, ?, ?)",
                            (self.src_path, addr, port, pid, time.time()),
                        )
                        conn.commit()
                        self._attach_client(addr, port, pid)
                    except Exception:
                        conn.rollback()
                        raise
        finally:
            if conn:
                conn.close()
            if hasattr(self, "_lock_acquired") and self._lock_acquired:
                _file_lock.release()
                self._lock_acquired = False

    def _start_server(self):
        address = "127.0.0.1"
        port = _allocate_port(address)
        proc = subprocess.Popen(
            ["code-browser-server", "-p", self.src_path, "-a", f"{address}:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if not _check_grpc(address, port):
            proc.terminate()
            try:
                out, err = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
                raise RuntimeError(
                    f"Failed to start server: communicate timed out. stdout: '{out.strip()}', stderr: '{err.strip()}'"
                )
            raise RuntimeError(
                f"Failed to start server: stdout: '{out.strip()}', stderr: '{err.strip()}'"
            )
        return address, port, proc.pid

    def _attach_client(self, addr: str, port: int, pid: int):
        self.server_address = addr
        self.server_port = port
        self.server_pid = pid
        self.db_client = CodeBrowserClient(f"{addr}:{port}")

    def shutdown(self):
        """Terminate the server process and clean registry entry."""
        try:
            os.kill(self.server_pid, signal.SIGTERM)
        except Exception:
            pass

        conn = None
        try:
            if hasattr(self, "_lock_acquired") and _file_lock.is_locked:
                with _file_lock:
                    conn = _init_db()
                    conn.execute("DELETE FROM servers WHERE path = ?", (self.src_path,))
                    conn.commit()
        except Exception as e:
            print(f"Error during DB cleanup in shutdown: {e}", file=sys.stderr)
        finally:
            if conn:
                conn.close()
            if _file_lock.is_locked:
                try:
                    _file_lock.release()
                except filelock.NotLocked:
                    pass

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.daemon is None:
            self.shutdown()

    # Proxy methods
    def get_function_definition(self, function_name: str):
        if self.daemon is None:
            return self.db_client.get_function_definition(function_name)
        else:
            return self.db_client.get_function_definition(function_name, self.src_path)

    def get_any_type_definition(self, type_name: str):
        if self.daemon is None:
            return self.db_client.get_any_type_definition(type_name)
        else:
            return self.db_client.get_any_type_definition(type_name, self.src_path)

    def get_function_cross_references(self, function_name: str):
        if self.daemon is None:
            return self.db_client.get_function_cross_references(function_name)
        else:
            return self.db_client.get_function_cross_references(
                function_name, self.src_path
            )

    def get_struct_definition(self, struct_name: str):
        if self.daemon is None:
            return self.db_client.get_struct_definition(struct_name)
        else:
            return self.db_client.get_struct_definition(struct_name, self.src_path)
