from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import random
import time
import logging
from pathlib import Path
from typing import override, List


logger = logging.getLogger(__name__)

# How long between new files where we consider coverage to have stopped increasing.
DEFAULT_TIME_BETWEEN_ENTRIES = 3


class JazzerCorpusObserver(FileSystemEventHandler):
    """Watches the corpus folder to see if coverage has stopped increasing.

    Implements a context-manager that needs to be started to actually start
    monitoring the folder.
    """

    def __init__(
        self,
        corpus_folder: Path,
        time_between_entries: int = DEFAULT_TIME_BETWEEN_ENTRIES,
    ):
        self.corpus_folder = corpus_folder
        self.time_between_entries = time_between_entries
        self.last_corpus_file = None

    def __enter__(self):
        self.reset_stuck_coverage_time()
        self.observer = Observer()
        self.observer.schedule(self, str(self.corpus_folder), recursive=False)
        self.observer.start()

    def __exit__(self, _type, _value, _traceback):
        self.observer.stop()
        self.observer.join()

    def reset_stuck_coverage_time(self):
        self.last_corpus_file_created = time.time()

    def is_jazzer_gen_seed(self, name) -> bool:
        if len(name) != 16 and len(name) != 40:
            return False
        return all(c in "0123456789abcdefABCDEF" for c in name)

    @override
    def on_closed(self, event):
        new_file = Path(event.src_path)
        if not self.is_jazzer_gen_seed(new_file.name):
            return
        logger.info(f"New file {new_file} made in corpus folder")
        self.last_corpus_file = new_file
        self.reset_stuck_coverage_time()

    def is_coverage_stuck(self) -> bool:
        time_since_last_new_corpus = time.time() - self.last_corpus_file_created
        return time_since_last_new_corpus > self.time_between_entries

    def get_stuck_corpus(self) -> Path:
        """Return a corpus that is stuck, prefer most recently made corpora."""
        corpus, corpus_mtime = None, 0

        for file in self.corpus_folder.iterdir():
            if not file.is_file():
                continue
            mtime = file.stat().st_mtime
            if mtime > corpus_mtime:
                corpus, corpus_mtime = file, mtime

        return corpus

    def get_random_corpora(self, n=4) -> List[Path]:
        """Get n random corpora from libfuzzer."""
        candidates = []

        for file in self.corpus_folder.iterdir():
            if not file.is_file():
                continue
            if not self.is_jazzer_gen_seed(file.name):
                continue
            candidates.append(file)
        return random.choices(candidates, k=min(len(candidates), n))
