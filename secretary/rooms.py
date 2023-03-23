import json
import re

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
