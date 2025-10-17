from utility.workdir import Workdir

import logging
import os
import coloredlogs
from libCRS.otel import install_otel_logger


class ExcludeSpecificLogFilter(logging.Filter):
    def filter(self, record):
        if record.levelno == logging.DEBUG:
            return True
        return not (
            record.levelname == "INFO" and "HTTP Request:" in record.getMessage()
        )


def set_file_logger(workdir: Workdir | None, name: str, root_logger: logging.Logger):
    if workdir is None:
        return
    log_path = workdir.get_log_path(name)
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)


def set_console_logger(root_logger: logging.Logger):
    console_handler = logging.StreamHandler()
    console_handler.setLevel(
        logging.INFO if not os.environ.get("DEBUG") else logging.DEBUG
    )
    console_handler.addFilter(ExcludeSpecificLogFilter())
    root_logger.addHandler(console_handler)

    coloredlogs.install(
        level=console_handler.level,
        logger=root_logger,
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        level_styles={
            "debug": {"color": "cyan"},
            "warning": {"color": "yellow"},
            "error": {"color": "red"},
            "critical": {"bold": True, "color": "red"},
        },
    )


def get_logger(workdir: Workdir | None, name=""):
    logger = (
        logging.getLogger(f"{workdir.repo_name}_{name}")
        if name
        else logging.getLogger()
    )
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    set_file_logger(workdir, name, logger)
    set_console_logger(logger)
    install_otel_logger(action_name="dict-gen")

    return logger
