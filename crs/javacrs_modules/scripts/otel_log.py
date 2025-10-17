import logging
import sys

from libCRS.otel import install_otel_logger


def setup_console_logger(logger_name="echo_logger"):
    logger = logging.getLogger(logger_name)

    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.DEBUG)

    # formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    # console_handler.setFormatter(formatter)

    # logger.addHandler(console_handler)

    install_otel_logger(action_name="crs-java:echo-tool")

    return logger


def main():
    logger = setup_console_logger()
    args = sys.argv[1:]

    if not args:
        logger.warning("No arguments provided.")
        return

    msg = " ".join(args)
    logger.info(msg)


if __name__ == "__main__":
    main()
