import json
import logging

from mautrix.api import Method
from mautrix.errors import MForbidden

from secretary import create_room
from secretary.rooms import delete_room
from secretary.util import get_example_policies, get_logger, DatabaseEntryNotFoundException


class MatrixSecretary:

    def __init__(self, client, db):
        self.client = client
        self.database = db
        self.mxid = self.client.mxid
        self.verbose = 'debug'
        self.notice_room = None
        self.logger = get_logger(stream_level=logging.DEBUG if self.verbose == 'debug' else logging.INFO)

    async def load_example_policies(self):
        policies = get_example_policies()
        for policy in policies:
            await self._add_policy_to_db(policy)
        pass

    async def ensure_all_policies(self):
        policies = await self.get_available_policies()
        for p in policies:
            await self.ensure_policy(p)
        pass

    async def ensure_policy(self, policy_name):
        policy = await self.get_policy(policy_name)
        for room_key, room_policy in policy['rooms'].items():
            invitees = {}
            for user, pl in room_policy['invitees'].items():
                if user.startswith('@'):
                    invitees[user] = pl
                else:
                    for u in policy['user_groups'][user]:
                        invitees[u] = pl
            room_policy['invitees'] = invitees
            room_id = await self._ensure_room_exists(policy['policy_key'], room_key, room_policy)
            await self._ensure_room_config(room_id, room_policy)
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
        #q = "DELETE FROM policies WHERE policy_key = $1"
        #await self.database.execute(q, policy_name)

    async def delete_all_rooms(self, only_abandoned=True):
        # mostly for testing, destroy everything the bot is in
        joined_rooms = await self.client.get_joined_rooms()
        self.logger.info(f"I'm currently in these rooms:\n  " + '\n  '.join(joined_rooms))
        failed = []
        for room in joined_rooms:
            alone = await self._am_i_alone(room, ignore_bots=True)
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

    async def get_policy(self, policy_key: str) -> json:
        return await self._get_policy_from_db(policy_key)

    async def get_available_policies(self):
        q = "SELECT policy_key FROM policies"
        result = await self.database.fetch(q)
        return [row[0] for row in result]

    async def set_notice_room(self, room_id) -> str:
        if self.notice_room == room_id:
            return f"This room is already set as maintenance room for this session ({room_id})."

        old_maintenance_room = self.notice_room
        self.notice_room = room_id
        reply = f"This room is now set as maintenance room for this session ({room_id})"
        if old_maintenance_room:
            reply += f" ... was {old_maintenance_room} before."

        return reply

    async def _am_i_alone(self, room_id, ignore_bots=False):
        # Am I alone in this room?
        members = await self.client.get_joined_members(room_id)
        members = [m for m in members if not ignore_bots or not m.startswith('@bot.') or m == self.mxid]
        return len(members) == 1 and members[0] == self.mxid

    async def _ensure_room_exists(self, policy_key, room_key, room_policy):
        # check if room exists in db
        try:
            room_id = await self._get_room_from_db(policy_key, room_key)
        except DatabaseEntryNotFoundException:
            # if not, create it
            room_id = await self._create_room(room_policy)
            # add room to db
            await self._add_room_to_db(policy_key, room_key, room_id)
        return room_id

    async def _add_room_to_db(self, policy_key: str, room_key: str, matrix_room_id: str) -> None:
        q = """
            INSERT INTO rooms (policy_key, room_key, matrix_room_id) VALUES ($1, $2, $3)
        """
        self.logger.info(f"Adding room {policy_key}:{room_key} to db")
        await self.database.execute(q, policy_key, room_key, matrix_room_id)

    async def _get_room_from_db(self, policy_key: str, room_key: str) -> str:
        q = "SELECT policy_key, room_key, matrix_room_id FROM rooms WHERE policy_key=$1 AND room_key=$2"
        row = await self.database.fetchrow(q, policy_key, room_key)
        if not row:
            raise DatabaseEntryNotFoundException(f"Could not find {policy_key}:{room_key} in database")
        # am I in this room?
        try:
            await self.client.get_room_state(row['matrix_room_id'])
        except MForbidden as err:
            if err.code == 403:
                self.logger.error(f"Room {row['matrix_room_id']} not found, removing from db")
                await self._remove_room_from_db(policy_key, room_key)
                raise DatabaseEntryNotFoundException(f"Could not find {policy_key}:{room_key} in database")
            else:
                raise err
        return row['matrix_room_id']

    async def _remove_room_from_db(self, policy_key, room_key):
        self.logger.debug(f"Removing room {policy_key}:{room_key} from db")
        q = "DELETE FROM rooms WHERE policy_key=$1 AND room_key=$2"
        await self.database.execute(q, policy_key, room_key)

    async def _add_policy_to_db(self, policy) -> None:
        q = """
            INSERT INTO policies (policy_key, policy_json) VALUES ($1, $2)
            ON CONFLICT (policy_key) DO UPDATE SET policy_json = excluded.policy_json;
        """
        policy_key = policy['policy_key']
        #validate_policy(policy, self.logger)
        self.logger.info(f"Adding policy {policy_key} to db")
        await self.database.execute(q, policy_key, json.dumps(policy))

    async def _get_policy_from_db(self, policy_key: str) -> str:
        q = "SELECT policy_key, policy_json FROM policies WHERE policy_key=$1"
        row = await self.database.fetchrow(q, policy_key)
        if not row:
            raise DatabaseEntryNotFoundException(f"Could not find {policy_key} in database")
        json_policy = json.loads(row['policy_json'])
        self.logger.info(f"Found policy {policy_key} in db: {json_policy}")
        return json_policy

    async def _create_room(self, room_policy):
        room_id = await create_room(
            self.client,
            room_policy['room_name'] if 'room_name' in room_policy else 'Pretty Placeholder',
            room_policy['invitees'] if 'invitees' in room_policy else {},
            self.client.mxid.split(':')[1],
            is_space=room_policy['is_space'] if 'is_space' in room_policy else False,
            parent_spaces=[],
            # parent_spaces = [self.policies[policy_key]['rooms'][ps_name]['id'] for ps_name in
            #                                room_policy['parent_spaces']] if 'parent_spaces' in room_policy else [],
            alias=room_policy['alias'] if 'alias' in room_policy else None,
            topic=room_policy['topic'] if 'topic' in room_policy else '',
            suggested=room_policy['suggested'] if 'suggested' in room_policy else False,
            join_rule=room_policy['join_rule'] if 'join_rule' in room_policy else 'restricted',
            encrypt=room_policy['encrypted'] if 'encrypted' in room_policy else False,
        )
        return room_id

    async def _ensure_room_config(self, room_id, room_policy):
        for key, value in room_policy.items():
            if key == 'room_name':
                await self._set_room_name(room_id, value)
            elif key == 'avatar_url':
                await self._set_room_avatar(room_id, value)
            elif key == 'topic':
                await self._set_room_topic(room_id, value)
            elif key == 'join_rule':
                await self._set_room_join_rule(room_id, value)
            elif key == 'history_visibility':
                await self._set_room_history_visibility(room_id, value)
            elif key == 'guest_access':
                await self._set_room_guest_access(room_id, value)
            elif key == 'encryption':
                await self._set_room_encryption(room_id, value)
            elif key == 'alias':
                await self._set_room_alias(room_id, value)

    async def _set_room_name(self, room_id, value):
        # get name of room with custom api request
        req = f"/_matrix/client/r0/rooms/{room_id}/state/m.room.name"
        self.logger.info(req)
        room_name = await self.client.api.request(Method.GET, req)
        if not room_name == value:
            self.logger.debug(f"Setting room name of {room_id} to {value}")
            req = f"/_matrix/client/r0/rooms/{room_id}/state/m.room.name"
            self.logger.info(req)
            await self.client.api.request(Method.PUT, req, content={'name': value})

    async def _set_room_avatar(self, room_id, value):
        pass

    async def _set_room_topic(self, room_id, value):
        pass

    async def _set_room_join_rule(self, room_id, value):
        pass

    async def _set_room_history_visibility(self, room_id, value):
        pass

    async def _set_room_guest_access(self, room_id, value):
        pass

    async def _set_room_encryption(self, room_id, value):
        pass

    async def _set_room_alias(self, room_id, value):
        pass

    async def _ensure_room_users(self, room_id, room_policy):
        for user in room_policy['invitees']:
            self.client.invite_user(room_id, user)

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

    async def add_policy(self, policy_as_json):
        # TODO validate against schema
        await self._add_policy_to_db(policy_as_json)
        return policy_as_json['policy_key']
