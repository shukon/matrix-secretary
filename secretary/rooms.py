import json
import re

from mautrix.api import Method, Path
from mautrix.errors import MForbidden

from secretary.util import get_logger


async def create_room(client,
                      room_name,
                      invitees,
                      is_space=False,
                      topic=None,
                      encrypt=False,
                      logger=None,
                      ):
    if not logger:
        logger = get_logger()

    if (room_name == "help") or len(room_name) == 0:
        raise ValueError(f'Not a valid room name: \"{room_name}\"')

    if not topic:
        topic = "No topic set."
    if len(invitees) == 0:
        logger.warn('There are no invitees - this room will not be very useful like this.')

    pl_override = {"users": {client.mxid: 9001}}
    for u, pl in invitees.items():
        pl_override["users"][str(u)] = int(pl)

    logger.debug(f"creating room {room_name} with invitees {invitees} and power levels {pl_override}...")
    room_id = await client.create_room(name=room_name,
                                       topic=topic,
                                       invitees=[str(k) for k in invitees.keys()],
                                       power_level_override=pl_override,
                                       creation_content={'type': 'm.space'} if is_space else None,
                                       )
    return room_id


async def delete_room(client, room):
    # kick users, delete aliases, delete room
    await _delete_aliases(client, room)
    await _kick_all_users(client, room)
    await client.leave_room(room_id=room)
    await client.forget_room(room_id=room)


async def _kick_all_users(client, room_id):
    members = await client.get_joined_members(room_id)
    for user in [m for m in members.keys() if not m == client.mxid]:
        try:
            await client.kick_user(room_id=room_id, user_id=user, reason="Room deletion.")
        except MForbidden as err:
            raise MForbidden(err.http_status, f"Error while kicking user {user} from room {room_id}: {err.message}")


async def _delete_aliases(client, room):
    aliases = await client.api.request(Method.GET, Path.v3.rooms[room].aliases)
    for alias in aliases['aliases']:
        local_alias = re.sub(r"#(.*):.*", r'\1', alias)
        try:
            await client.remove_room_alias(alias_localpart=local_alias, raise_404=True)
        except MForbidden as err:
            raise MForbidden(err.http_status, f"Error while removing alias {alias} for room {room}: {err.message}")
