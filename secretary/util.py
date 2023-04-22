import logging
from typing import Tuple, Any

from mautrix.util.async_db import UpgradeTable, Connection

from secretary.example_policies.minimal_policy import get_minimal_policy
from secretary.example_policies.nina import get_nina_policy

# Database
upgrade_table = UpgradeTable()


@upgrade_table.register(description="Initial revision")
async def upgrade_v1(conn: Connection) -> None:
    await conn.execute(
        """CREATE TABLE rooms (
            policy_key        TEXT,
            room_key  TEXT,
            matrix_room_id   TEXT,
            PRIMARY KEY (policy_key, room_key)
         )""")
    await conn.execute(
        """CREATE TABLE policies ( 
            policy_key        TEXT,
            policy_json       TEXT, 
            PRIMARY KEY (policy_key)
        )"""
    )


def get_upgrade_table():
    return upgrade_table


class PolicyNotFoundError(Exception):
    pass


class DatabaseEntryNotFoundException(Exception):
    pass


async def log_error(e):
    pass


def non_empty_string(x: str) -> Tuple[str, Any]:
    if not x:
        return x, None
    return "", x


def get_example_policies():
    policies = [get_nina_policy(small=True),
                get_nina_policy(small=False),
                get_minimal_policy()]
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
