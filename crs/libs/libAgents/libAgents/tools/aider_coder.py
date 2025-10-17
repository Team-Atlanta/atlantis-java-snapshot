import logging
import os
from aider.models import Model
from aider.coders import Coder
from aider.io import InputOutput
from aider.repo import GitRepo
from aider.main import setup_git

from typing import List, Optional

from libAgents.utils import cd

logger = logging.getLogger(__name__)


class AiderCoder:
    def __init__(
        self,
        main_model: Model,
        repo_path: str,
        fnames: List[str] = [],
        ro_fnames: List[str] = [],
        chat_history_file: Optional[str] = None,
        working_dir: Optional[str] = None,
        map_tokens: int = 1024,
    ):
        self.main_model = main_model
        self.repo_path = repo_path
        self.chat_history_file = chat_history_file
        self.working_dir = working_dir
        self.map_tokens = map_tokens
        self._coder = self._get_coder()  # init aider coder

        if fnames:
            self.add_files(fnames)

        if ro_fnames:
            self.add_ro_files(ro_fnames)

        self._coder.get_repo_map()

    def _get_coder(self) -> Coder:
        with cd(self.working_dir):
            io = InputOutput(yes=True, chat_history_file=self.chat_history_file)

            # create a git repo if not exists
            # I want to utilize the repo map feature
            git_root = setup_git(self.repo_path, io)

            if not git_root:
                # If setup_git didn't create a repo, initialize one manually
                import git

                try:
                    git.Repo.init(self.repo_path)
                    git_root = self.repo_path

                    # Configure git user info if needed
                    repo = git.Repo(git_root)
                    with repo.config_writer() as git_config:
                        git_config.set_value("user", "name", "Your Name")
                        git_config.set_value("user", "email", "you@example.com")

                    logger.info(f"Created git repository at {git_root}")
                except Exception as e:
                    logger.error(f"Failed to create git repository: {e}")
                    raise e

            repo = GitRepo(io=io, fnames=[], git_dname=self.repo_path)

            coder = Coder.create(
                main_model=self.main_model,
                io=io,
                repo=repo,
                fnames=[],
                auto_commits=False,
                dirty_commits=False,
                stream=False,
                auto_test=True,
                map_tokens=self.map_tokens,  # repo map tokens
                verbose=False,
                detect_urls=False,
            )
            # force a repo map
            # coder.get_repo_map()
        return coder

    def __getattr__(self, name):
        """
        Delegate property access to the _coder object if the attribute
        is not found in AiderCoder.

        This allows direct access to _coder properties through AiderCoder instance.
        """
        if hasattr(self._coder, name):
            return getattr(self._coder, name)
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def add_file(self, fname: str) -> None:
        with cd(self.working_dir):
            self._coder.add_rel_fname(fname)

    def add_ro_file(self, fname: str) -> None:
        with cd(self.working_dir):
            abs_fname = self._coder.abs_root_path(fname)
            if os.path.exists(abs_fname):
                self._coder.abs_read_only_fnames.add(abs_fname)

    def add_files(self, fnames: List[str]) -> None:
        with cd(self.working_dir):
            for fname in fnames:
                self._coder.add_rel_fname(fname)

    def add_ro_files(self, fnames: List[str]) -> None:
        with cd(self.working_dir):
            for fname in fnames:
                abs_fname = self._coder.abs_root_path(fname)
                if os.path.exists(abs_fname):
                    self._coder.abs_read_only_fnames.add(abs_fname)

    def run(self, instructions: str) -> str:
        with cd(self.working_dir):
            res = self._coder.run(instructions)
        return res
