import json
import logging
import traceback
import re
from typing import Tuple, Any

import aiohttp

from secretary.example_policies.corner_cases import get_corner_cases_policy
from secretary.example_policies.minimal_policy import get_minimal_policy
from secretary.example_policies.nina import get_nina_policy
from secretary.example_policies.policy_schema import get_schema


class PolicyNotFoundError(Exception):
    pass


class DatabaseEntryNotFoundException(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class WrongContentTypeError(Exception):
    pass


async def log_error(logger, err, evt):
    logger.exception(err)
    await evt.respond(f"I tried, but something went wrong: \"{err}\"")
    await evt.respond(f"```\n{traceback.format_exc()}\n```")


def non_empty_string(x: str) -> Tuple[str, Any]:
    if not x:
        return x, None
    return "", x


async def download_file(url):
    max_file_size_mb = 10
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ) as response:
            if response.status == 200:
                content_type = response.headers.get('content-type', '').lower()
                content_length = response.headers.get('content-length')

                # Check if the content length is within the limit
                if content_length and int(content_length) / (1024 * 1024) > max_file_size_mb:
                    file_size = int(content_length) / (1024 * 1024)
                    raise FileTooLargeError(
                        f"File size of {file_size} exceeds the maximum allowed size of {max_file_size_mb} MB.")

                # Check if the content type is JSON
                if 'json' in content_type:
                    return await response.json(loads=json.loads)
                else:
                    raise WrongContentTypeError(f"Content type {content_type} is not JSON.")


def get_example_policies():
    policies = [get_nina_policy(small=True),
                get_nina_policy(small=False),
                get_minimal_policy(),
                get_corner_cases_policy(),
                ]
    return policies


def escape_as_alias(alias: str) -> str:
    umlaut_map = {ord('ä'): 'ae', ord('ü'): 'ue', ord('ö'): 'oe', ord('ß'): 'ss',
                  ord('Ä'): 'Ae', ord('Ü'): 'Ue', ord('Ö'): 'Oe', ord(' '): '_'}
    alias = alias.translate(umlaut_map)
    alias = re.sub(r"[^a-zA-Z0-9_]", '', alias).lower()

    return alias


def is_legal(key, value):
    legal_dict = {
        'guest_access': ['can_join', 'forbidden'],
        'history_visibility': ['shared', 'invited', 'joined', 'world_readable'],
        'join_rule': ['public', 'knock', 'invite', 'private', 'restricted', 'knock_restricted'],
        'visibility': ['public', 'private'],
    }
    if key in legal_dict and value not in legal_dict[key]:
        raise ValueError(f'Not a valid {key}: \"{value}\"')


def is_matrix_room_id(string):
    return re.compile(r"^!.*:.*$").match(string)


def is_matrix_room_alias(string):
    return re.compile(r"^#.*:.*$").match(string)


def is_legal_http_url(string):
    return re.compile(r"^https?://.*$").match(string)


def is_legal_mxc_url(string):
    return re.compile(r"^mxc://.*$").match(string)


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
