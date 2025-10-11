import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
