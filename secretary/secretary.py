import logging
import os
import re
from typing import Tuple, List

from maubot import Plugin
from mautrix.api import Method, Path
from mautrix.errors import MForbidden
from mautrix.types import MessageType
from mautrix.util.async_db import UpgradeTable, Connection

from secretary import create_room
from secretary.util import get_example_policies, PolicyNotFoundError, get_logger, DatabaseEntryNotFoundException




class MatrixSecretary:

    def __init__(self, client, db):
        pass

    async def ensure_all_policies(self):
        # for p in policy:
        #     await self.ensure_policy(p)
        pass

    async def ensure_policy(self, policy_name, sender=None):
        # ensure specific policy is implemented and up to date
        pass

    async def ensure_policy_destroyed(self, policy_name):
        # ensure everything related to a policy is deleted (all rooms and users) and the policy itself is removed from db
        pass

    async def delete_all_rooms(self, only_abandoned=True):
        # mostly for testing, destroy everything the bot is in
        pass

    def get_policy(self, policy_name):
        pass

    def get_available_policies(self):
        pass

    async def _get_policies(self) -> List[str]:
        pass

    async def set_maintenance_room(self, room_id) -> str:
        pass

    async def _am_i_alone(self, room_id, ignore_bots=False):
        pass
