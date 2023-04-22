import json
import re
from typing import Tuple

from secretary.util import get_logger

async def create_room(client,
                      roomname,
                      invitees,
                      server,
                      is_space=False,
                      parent_spaces=None,
                      alias=None,
                      topic=None,
                      suggested=False,
                      join_rule='restricted',
                      encrypt=False,
                      logger=None,
                      ):
    pass

    async def delete_room(self, room):
        # kick users, delete aliases, delete room
        pass

    async def _kick_all_users(self, room_id):
        pass

    async def _delete_aliases(self, room):
        pass


    async def add_room_to_db(self, uid: str, matrix_room_id: str) -> None:
        pass

    async def get_room_from_db(self, uid: str) -> Tuple[str, str, str]:
        pass