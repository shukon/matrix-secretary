import json
import logging

from mautrix.api import Method
from mautrix.errors import MForbidden, MNotFound
from mautrix.types import RoomAvatarStateEventContent, Membership

from secretary import create_room
from secretary.rooms import delete_room
from secretary.util import get_example_policies, get_logger, DatabaseEntryNotFoundException, escape_as_alias, \
    is_matrix_room_id, is_matrix_room_alias, is_legal


class MatrixSecretary:

    def __init__(self, client, db):
        self.client = client
        self.database = db
        self.mxid = self.client.mxid
        self.verbose = 'debug'
        self.notice_room = None
        self.logger = get_logger(stream_level=logging.DEBUG if self.verbose == 'debug' else logging.INFO)

    async def set_notice_room(self, room_id) -> str:
        if self.notice_room == room_id:
            return f"This room is already set as maintenance room for this session ({room_id})."

        old_maintenance_room = self.notice_room
        self.notice_room = room_id
        reply = f"This room is now set as maintenance room for this session ({room_id})"
        if old_maintenance_room:
            reply += f" ... was {old_maintenance_room} before."

        return reply

    ####################################################################################################################
    # Policy management                                                                                                #
    ####################################################################################################################

    async def ensure_all_policies(self):
        policies = await self.get_available_policies()
        for p in policies:
            await self.ensure_policy(p)
        pass

    async def ensure_policy(self, policy_name):
        policy = await self.get_policy(policy_name)
        for room_key, room_policy in policy['rooms'].items():
            invitees = {}
            if 'invitees' in room_policy:
                for user, pl in room_policy['invitees'].items():
                    if user.startswith('@'):
                        invitees[user] = pl
                    else:
                        for u in policy['user_groups'][user]['users']:
                            invitees[u] = pl
            policy['rooms'][room_key]['invitees'] = invitees
            policy['rooms'][room_key]['tmp_matrix_room_id'] = await self._ensure_room_exists(policy['policy_key'],
                                                                                             room_key, room_policy)
        for room_key, room_policy in policy['rooms'].items():
            room_id = room_policy['tmp_matrix_room_id']
            await self._ensure_room_config(room_id, room_policy, policy['policy_key'],
                                           default_room_settings=policy['default_room_settings'] if
                                           'default_room_settings' in policy else None)
            await self._ensure_room_users(room_id, room_policy)
            await self._ensure_room_bot_actions(room_id, room_policy)

    async def ensure_policy_destroyed(self, policy_name):
        # Get all rooms related to this policy
        q = "SELECT matrix_room_id FROM rooms WHERE policy_key = $1"
        rooms = await self.database.fetch(q, policy_name)
        for room in rooms:
            await delete_room(self.client, room['matrix_room_id'])
        await self.forget_policy(policy_name)

    async def forget_policy(self, policy_name):
        self.logger.info(f"Removing policy {policy_name} from db")
        q = "DELETE FROM rooms WHERE policy_key = $1"
        await self.database.execute(q, policy_name)
        # q = "DELETE FROM policies WHERE policy_key = $1"
        # await self.database.execute(q, policy_name)

    async def add_policy(self, policy_as_json) -> str:
        # TODO validate against schema
        # TODO Add empty dicts for default_room_settings and user_groups if they don't exist
        await self._add_policy_to_db(policy_as_json)
        return policy_as_json['policy_key']

    async def get_policy(self, policy_key: str) -> json:
        return await self._get_policy_from_db(policy_key)

    async def get_available_policies(self):
        q = "SELECT policy_key FROM policies"
        result = await self.database.fetch(q)
        return [row[0] for row in result]

    async def load_example_policies(self):
        policies = get_example_policies()
        for policy in policies:
            await self.add_policy(policy)

    ####################################################################################################################
    # Room management                                                                                                  #
    ####################################################################################################################

    async def delete_all_rooms(self, only_abandoned=True, ignore_bots=True):
        async def room_not_in_db(room_id):
            q = "SELECT * FROM rooms WHERE matrix_room_id = $1"
            return await self.database.fetchval(q, room_id) is None

        # mostly for testing, destroy everything the bot is in
        joined_rooms = await self.client.get_joined_rooms()
        self.logger.info(f"I'm currently in these rooms:\n  " + '\n  '.join(joined_rooms))
        failed = []
        for room in joined_rooms:
            members = [m for m in await self.client.get_joined_members(room) if
                       not ignore_bots or not m.startswith('@bot.') or m == self.mxid]
            alone = len(members) == 1 and members[0] == self.mxid and await room_not_in_db(room)
            if room != self.notice_room and (not only_abandoned or alone):
                self.logger.info(f"Deleting room {room}")
                try:
                    await delete_room(self.client, room)
                except Exception as err:
                    failed.append((room, err))
        failed_str = ' \n... except for:\n  ' + '\n  '.join([f"{r}: {e}" for r, e in failed])
        msg = f"Done clearing old rooms!{failed_str if len(failed) > 0 else ''}"
        self.logger.info(msg)
        return msg

    async def _ensure_room_exists(self, policy_key, room_key, room_policy):
        try:
            room_id = await self._get_room_from_db(policy_key, room_key)
        except DatabaseEntryNotFoundException:
            self.logger.info(f"Room {policy_key}:{room_key} not found in db, creating it")
            room_id = await self._create_room(room_policy)
            await self._add_room_to_db(policy_key, room_key, room_id)
        return room_id

    async def _create_room(self, room_policy):
        room_id = await create_room(
            self.client,
            room_policy['room_name'] if 'room_name' in room_policy else 'Pretty Placeholder',
            room_policy['invitees'] if 'invitees' in room_policy else {},
            is_space=room_policy['is_space'] if 'is_space' in room_policy else False,
            topic=room_policy['topic'] if 'topic' in room_policy else '',
        )
        return room_id

    async def _ensure_room_config(self, room_id, room_policy, policy_key, default_room_settings=None):
        default_room_settings = {} if default_room_settings is None else default_room_settings
        parent_spaces = []
        parent_spaces_secret = []

        # todo get room state once and then use it to check if things are already set
        if 'room_name' in room_policy:
            await self._set_room_state(room_id, 'name', room_policy['room_name'])
        if 'alias' in room_policy:
            await self._set_room_alias(room_id, room_policy['alias'])
        if 'parent_spaces' in room_policy:
            for p in room_policy['parent_spaces']:
                if is_matrix_room_id(p):
                    parent_spaces.append(p)
                elif is_matrix_room_alias(p):
                    parent_spaces.append(self.client.api.request(Method.GET, f"/_matrix/client/r0/directory/room/{p}"))
                else:
                    parent_spaces.append(await self._get_room_from_db(policy_key, p))
            room_policy['parent_spaces'] = parent_spaces
            await self._ensure_parent_spaces(room_id, parent_spaces,
                                             room_policy['suggested'] if 'suggested' in room_policy else False)
        if 'parent_spaces_silent' in room_policy:
            for p in room_policy['parent_spaces_silent']:
                if is_matrix_room_id(p):
                    parent_spaces_secret.append(p)
                elif is_matrix_room_alias(p):
                    parent_spaces_secret.append(self.client.api.request(Method.GET, f"/_matrix/client/r0/directory/room/{p}"))
                else:
                    parent_spaces_secret.append(await self._get_room_from_db(policy_key, p))
            room_policy['parent_spaces_silent'] = parent_spaces_secret
            await self._ensure_parent_spaces(room_id, parent_spaces_secret,
                                             room_policy['suggested'] if 'suggested' in room_policy else False)

        if 'room_avatar' in room_policy:
            await self._set_room_avatar(room_id, room_policy['room_avatar'])
        if 'topic' in room_policy:
            await self._set_room_state(room_id, 'topic', room_policy['topic'])
        if 'encryption' in room_policy:
            await self._set_room_encryption(room_id, room_policy['encryption'])

        # values contained in default_room_settings will be overwritten by room_policy:
        if 'join_rule' in room_policy or 'join_rule' in default_room_settings:
            join_rules = room_policy['join_rule'] if 'join_rule' in room_policy else default_room_settings['join_rule']
        else:
            join_rules = 'restricted'
        await self._set_room_join_rules(room_id, join_rules, parent_spaces)
        if 'visibility' in room_policy or 'visibility' in default_room_settings:
            visibility = room_policy['visibility'] if 'visibility' in room_policy else default_room_settings[
                'visibility']
            await self._set_room_visibility(room_id, visibility)
        for key in ['history_visibility', 'guest_access', ]:
            if key in room_policy or key in default_room_settings:
                value = room_policy[key] if key in room_policy else default_room_settings[key]
                await self._set_room_state(room_id, key, value)

    async def _ensure_parent_spaces(self, room_id, parent_spaces, suggested=False):
        parent_event_content = json.dumps(
            {'auto_join': False, 'suggested': suggested, 'via': [self.client.mxid.split(':')[1]]})
        child_event_content = json.dumps(
            {'canonical': True, 'via': [self.client.mxid.split(':')[1]]})

        for ps in parent_spaces:
            self.logger.debug(f"Setting {ps} as parent of {room_id}")
            await self.client.send_state_event(ps, 'm.space.child', parent_event_content, state_key=room_id)
            await self.client.send_state_event(room_id, 'm.space.parent', child_event_content, state_key=ps)

    async def _set_room_join_rules(self, room_id, join_rule, parent_spaces=None):
        is_legal('join_rule', join_rule)
        join_rules_content = {'join_rule': join_rule}
        self.logger.debug(f"Setting join rule of {room_id} to {join_rule}")
        if parent_spaces:
            self.logger.debug(f"Adding parent spaces {parent_spaces} to join rule of {room_id}")
            join_rules_content['allow'] = [{'type': 'm.room_membership', 'room_id': ps} for ps in parent_spaces]
        join_rules_content = json.dumps(join_rules_content)
        await self.client.send_state_event(room_id, 'm.room.join_rules', join_rules_content, state_key="")

    async def _set_room_visibility(self, room_id, visibility):
        # Controls whether a room is published to public room directory.
        is_legal('visibility', visibility)
        api_link = f"/_matrix/client/r0/directory/list/room/{room_id}"
        current_value = await self.client.api.request(Method.GET, api_link)
        if current_value['visibility'] != visibility:
            self.logger.debug(f"Setting room visibility of {room_id} to {visibility}")
            await self.client.api.request(Method.PUT, api_link, {'visibility': visibility})
        else:
            self.logger.debug(f"Room visibility of {room_id} already set to {visibility}")

    async def _set_room_state(self, room_id, key, value):
        is_legal(key, value)
        api_link = f"/_matrix/client/r0/rooms/{room_id}/state/m.room.{key}"
        try:
            current_value = await self.client.api.request(Method.GET, api_link)
        except MNotFound:
            current_value = {key: None}
        if current_value[key] != value:
            self.logger.debug(f"Setting room {key} of {room_id} to {value}")
            await self.client.api.request(Method.PUT, api_link, content={key: value})
        else:
            self.logger.debug(f"Room {key} of {room_id} is already {value}")

    async def _set_room_avatar(self, room_id, avatar_url):
        try:
            try:
                room_info = await self.client.api.request(Method.GET, f"/_matrix/client/r0/rooms/{room_id}/state/m.room.avatar")
            except MNotFound:
                room_info = {}
            current_value = room_info['url'] if 'url' in room_info else None
            self.logger.debug(f"Room {room_id} has avatar {current_value}")
            if current_value != avatar_url:
                self.logger.debug(f"Setting avatar for room {room_id} to {avatar_url}")
                await self.client.send_state_event(room_id, 'm.room.avatar', RoomAvatarStateEventContent(url=avatar_url))
            else:
                self.logger.debug(f"Room {room_id} already has avatar {avatar_url}")
        except MForbidden as err:
            self.logger.exception(f"Failed to set room avatar for room {room_id}: {err}")

    async def _set_room_encryption(self, room_id, encrypt):
        raise NotImplementedError("Encryption is not yet implemented")
        room_encryption = await self.client.api.request(Method.GET, f"/_matrix/client/r0/rooms/{room_id}")
        if encrypt and 'encryption' not in room_encryption:
            encryption_content = json.dumps({"algorithm": "m.megolm.v1.aes-sha2"})
            await self.client.send_state_event(room_id, 'm.room.encryption', encryption_content, state_key="")
            self.logger.debug('encrypting room...')
        elif not encrypt and 'encryption' in room_encryption:
            self.logger.warn('disabling encryption is not supported')
        else:
            self.logger.debug('room is already encrypted')

    async def _set_room_alias(self, room_id, value, override=False):
        alias = escape_as_alias(value)
        try:
            room_aliases = await self.client.api.request(Method.GET, f"/_matrix/client/r0/rooms/{room_id}/aliases")
            self.logger.debug(f"Room {room_id} has aliases {room_aliases}")
            if f"#{alias}:{self.client.mxid.split(':')[1]}" not in room_aliases['aliases']:
                self.logger.debug(f"Setting alias for room {room_id} to {alias}")
                await self.client.add_room_alias(room_id, alias, override=override)
            else:
                self.logger.debug(f"Room {room_id} already has alias {alias}")
        except MForbidden as err:
            self.logger.exception(f"Failed to set alias for room {room_id}: {err}")

    async def _ensure_room_users(self, room_id, room_policy):
        self.logger.debug(f"Ensuring users in room {room_id}: {room_policy['invitees']}")
        # Get room member list
        for user in room_policy['invitees']:
            room_members = await self.client.get_joined_members(room_id)
            if user not in room_members or room_members[user]['membership'] not in [Membership.JOIN, Membership.INVITE]:
                self.logger.debug(f"Inviting user {user} to {room_id}")
                await self.client.invite_user(room_id, user)

    async def _ensure_room_bot_actions(self, room_id, room_policy):
        # if 'actions' in room_data:
        #     # Check if actions need to be run?!
        #     for room_action in room_data['actions']:
        #         for bot_id in policy['actions'][room_action['template']]['bots']:
        #             self.logger.debug(f"Inviting bot {bot_id} to {room_id}")
        #             await self.client.invite_user(room_id, bot_id)
        #         for cmd in policy['actions'][room_action['template']]['commands']:
        #             cmd = cmd.format(**room_action['format']) if 'format' in room_action else cmd
        #             self.logger.debug(f"Sending command {cmd} to {room_id}")
        #             await self.client.send_markdown(room_id, cmd, msgtype=MessageType.TEXT, allow_html=True)

        pass

    ####################################################################################################################
    # Database management                                                                                              #
    ####################################################################################################################

    async def _add_room_to_db(self, policy_key: str, room_key: str, matrix_room_id: str) -> None:
        self.logger.info(f"Adding room {policy_key}:{room_key} to db")
        q = "INSERT INTO rooms (policy_key, room_key, matrix_room_id) VALUES ($1, $2, $3)"
        await self.database.execute(q, policy_key, room_key, matrix_room_id)

    async def _get_room_from_db(self, policy_key: str, room_key: str) -> str:
        q = "SELECT policy_key, room_key, matrix_room_id FROM rooms WHERE policy_key=$1 AND room_key=$2"
        row = await self.database.fetchrow(q, policy_key, room_key)
        if not row:
            raise DatabaseEntryNotFoundException(f"Could not find {policy_key}:{room_key} in database")
        # am I in this room? is it accessible, e.g. in a space I'm in?
        try:
            if self.mxid not in await self.client.get_joined_members(row['matrix_room_id']):
                self.client.join_room(row['matrix_room_id'])
        except MForbidden:
            self.logger.exception(f"Room {row['matrix_room_id']} not accessible, removing from db to recreate")
            await self._remove_room_from_db(policy_key, room_key)
            raise DatabaseEntryNotFoundException(f"Could not access {policy_key}:{room_key}, dropped from db, recreate")
        return row['matrix_room_id']

    async def _remove_room_from_db(self, policy_key, room_key):
        self.logger.debug(f"Removing room {policy_key}:{room_key} from db")
        q = "DELETE FROM rooms WHERE policy_key=$1 AND room_key=$2"
        await self.database.execute(q, policy_key, room_key)

    async def _add_policy_to_db(self, policy) -> None:
        policy_key = policy['policy_key']
        self.logger.info(f"Adding policy {policy_key} to db")
        q = """
            INSERT INTO policies (policy_key, policy_json) VALUES ($1, $2)
            ON CONFLICT (policy_key) DO UPDATE SET policy_json = excluded.policy_json;
        """
        # TODO (here, though?!) validate_policy(policy, self.logger)
        await self.database.execute(q, policy_key, json.dumps(policy))

    async def _get_policy_from_db(self, policy_key: str) -> str:
        q = "SELECT policy_key, policy_json FROM policies WHERE policy_key=$1"
        row = await self.database.fetchrow(q, policy_key)
        if not row:
            raise DatabaseEntryNotFoundException(f"Could not find {policy_key} in database")
        json_policy = json.loads(row['policy_json'])
        self.logger.debug(f"Found policy {policy_key} in db!")
        return json_policy

