import json
import re
from typing import Tuple

from mautrix.api import Method, Path
from mautrix.errors import MForbidden

from secretary.util import get_logger, log_error


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
    if not logger:
        logger = get_logger()

    if (roomname == "help") or len(roomname) == 0:
        raise ValueError(f'Not a valid roomname: \"{roomname}\"')

    # todo make constant / enum
    if join_rule not in ['public', 'invite', 'knock', 'restricted', 'knock_restricted', 'private']:
        raise ValueError(f'Not a valid join_rule: \"{join_rule}\"')

    if not alias:
        alias = roomname
    if not topic:
        topic = "No topic set."
    # todo: we want the alias to be sanitized as a function and probably not just here
    umlaut_map = {ord('ä'): 'ae', ord('ü'): 'ue', ord('ö'): 'oe', ord('ß'): 'ss',
                  ord('Ä'): 'Ae', ord('Ü'): 'Ue', ord('Ö'): 'Oe', ord(' '): '_'}
    alias = alias.translate(umlaut_map)
    alias = re.sub(r"[^a-zA-Z0-9_]", '', alias).lower()
    if len(invitees) == 0:
        logger.warn('There are no invitees - this room will not be very useful like this.')
    # server = self.client.whoami().domain
    pl_override = {"users": {client.mxid: 9001}}
    logger.warn(invitees)
    for u, pl in invitees.items():
        pl_override["users"][str(u)] = int(pl)
    # pl_json = json.dumps(pl_override)
    creation_content = None
    if is_space:
        creation_content = {'type': 'm.space'}

    # todo handle non critical errors such as already existing aliases
    logger.debug(
        f"creating room {roomname} with alias #{alias}:{server} and invitees {invitees} and power levels {pl_override}...")
    room_id = await client.create_room(alias_localpart=alias,
                                       name=roomname,
                                       topic=topic,
                                       invitees=[str(k) for k in invitees.keys()],
                                       power_level_override=pl_override,
                                       creation_content=creation_content,
                                       )

    logger.debug('updating room states...')
    parent_event_content = json.dumps({'auto_join': False, 'suggested': suggested, 'via': [server]})
    child_event_content = json.dumps({'canonical': True, 'via': [server]})
    join_rules_content = {'join_rule': join_rule}
    if parent_spaces:
        join_rules_content['allow'] = [{'type': 'm.room_membership', 'room_id': ps} for ps in parent_spaces]
    join_rules_content = json.dumps(join_rules_content)

    for ps in parent_spaces:
        await client.send_state_event(ps, 'm.space.child', parent_event_content, state_key=room_id)
        await client.send_state_event(room_id, 'm.space.parent', child_event_content, state_key=ps)

    await client.send_state_event(room_id, 'm.room.join_rules', join_rules_content, state_key="")

    if encrypt:
        encryption_content = json.dumps({"algorithm": "m.megolm.v1.aes-sha2"})

        await client.send_state_event(room_id, 'm.room.encryption', encryption_content, state_key="")
        logger.debug('encrypting room...')

    logger.debug(f"room created and updated, alias is #{alias}:{server}")
    return room_id


async def delete_room(client, room):
    # kick users, delete aliases, delete room
    try:
        await _delete_aliases(client, room)
        await _kick_all_users(client, room)
        await client.leave_room(room_id=room)
        await client.forget_room(room_id=room)
    except Exception as e:
        await log_error(e)
        raise


async def _kick_all_users(client, room_id):
    members = await client.get_joined_members(room_id)
    #self.logger.debug(f"Kicking all members in room {room_id}.")
    for user in [m for m in members.keys() if not m == client.mxid]:
        #self.logger.debug(f"-> Kick user {user} from {room_id}.")
        try:
            await client.kick_user(room_id=room_id, user_id=user, reason="Room deletion.")
        except MForbidden as err:
            #self.logger.exception(f"Error while kicking user {user} from room {room_id}: {err}")
            raise MForbidden(err.http_status, f"Error while kicking user {user} from room {room_id}: {err.message}")


async def _delete_aliases(client, room):
    aliases = await client.api.request(Method.GET, Path.v3.rooms[room].aliases)
    for alias in aliases['aliases']:
        local_alias = re.sub(r"#(.*):.*", r'\1', alias)
        #self.logger.debug(f"-> Remove alias: {alias} / {local_alias}")
        try:
            await client.remove_room_alias(alias_localpart=local_alias, raise_404=True)
        except MForbidden as err:
            #self.logger.exception(f"Error while removing alias {alias} for room {room}: {err}")
            raise MForbidden(err.http_status, f"Error while removing alias {alias} for room {room}: {err.message}")

