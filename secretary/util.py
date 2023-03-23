import logging
from typing import Tuple, Any

from secretary.example_policies.nina import get_nina_policy


class PolicyNotFoundError(Exception):
    pass


def non_empty_string(x: str) -> Tuple[str, Any]:
    if not x:
        return x, None
    return "", x


def get_example_policies():
    policies = {
        "nina_small": get_nina_policy(small=True),
        "nina_full": get_nina_policy(small=False),
    }
    return policies


def get_logger(stream_level=logging.INFO, file_level=logging.DEBUG, log_file_path=None):
    # Create a logger object
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Create a file handler and add it to the logger
    if log_file_path:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Create a stream handler and add it to the logger
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
