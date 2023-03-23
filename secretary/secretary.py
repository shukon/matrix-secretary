import logging
import re

from mautrix.api import Method, Path
from mautrix.errors import MForbidden
from mautrix.types import MessageType

from secretary import create_room
from secretary.util import get_example_policies, PolicyNotFoundError, get_logger


class MatrixSecretary:
    """
    Todos:
    - [ ] Define json format for config / policy file
    - [ ] Manage database + create database schema

    Scope:
    - Read config file

    - Create rooms
    - Create spaces
    - Create aliases
    - Create invites and manage power levels
    - Create and manage bots
    - Create and manage bridges
    """

    def __init__(self, client):
        self.client = client
        self.mxid = self.client.mxid
        self.verbose = 'debug'
        self.maintenance_room = None
        self.logger = get_logger(stream_level=logging.DEBUG if self.verbose == 'debug' else logging.INFO)
        self.policies = get_example_policies()

    def set_maintenance_room(self, room_id):
        if self.maintenance_room == room_id:
            reply = f"This room is already set as maintenance room for this session ({room_id})."
        else:
            old_maintenance_room = self.maintenance_room
            self.maintenance_room = room_id
            reply = f"This room is now set as maintenance room for this session ({room_id})"
            if old_maintenance_room:
                reply += f" ... was {old_maintenance_room} before."
        return reply

    def am_i_alone(self, members_list, ignore_bots=False):
        # Am I alone in this room?
        if ignore_bots:
            return all([m.startswith('@bot.') for m in members_list])
        else:
            return len(members_list) == 1 and members_list[1] == self.mxid

    async def clear_rooms(self, only_abandoned=True):
        joined_rooms = await self.client.get_joined_rooms()
        self.logger.info(f"I'm currently in these rooms:\n  " + '\n  '.join(joined_rooms))
        failed = []
        for room in joined_rooms:
            members = await self.client.get_joined_members(room)
            delete = False
            if only_abandoned and self.am_i_alone(members, ignore_bots=True):
                self.logger.info(f"Only bot members in {room} (members: {members}), schedule for deletion.")
                delete = True
            elif not only_abandoned and room != self.maintenance_room:
                self.logger.info(f"Deleting all rooms (except maintenance), so {room} is scheduled for deletion.")
                delete = True
            if delete:
                try:
                    # kick all users, leave room, forget room
                    await self._delete_aliases(room)
                    await self._kick_all_users(room)
                    await self.client.leave_room(room_id=room)
                    await self.client.forget_room(room_id=room)
                except Exception as e:
                    self.logger.error(f"Error while deleting room {room}: {e}")
                    failed.append((room, e))
                    if self.maintenance_room:
                        await self.client.send_markdown(self.maintenance_room,f"Error while deleting room {room}: {e}",msgtype=MessageType.TEXT)
        msg = f"Done clearing old rooms!"
        if failed:
            failed = '\n  '.join([f"{r}: {e}" for r, e in failed])
            msg += f"\n... except for:\n  " \
                   f"{failed}"
        self.logger.info(msg)
        return msg

    async def _kick_all_users(self, room_id):
        members = await self.client.get_joined_members(room_id)
        self.logger.debug(f"Kicking all members in room {room_id}.")
        for user in members.keys():
            if not user == self.client.mxid:
                self.logger.debug(f"-> Kick user {user} from {room_id}.")
                try:
                    await self.client.kick_user(room_id=room_id, user_id=user,
                                            reason="Clean up unused room.")
                except MForbidden as err:
                    self.logger.exception(f"Error while kicking user {user} from room {room_id}: {err}")
                    raise MForbidden(err.http_status, f"Error while kicking user {user} from room {room_id}: {err.message}")


    async def _delete_aliases(self, room):
        aliases = await self.client.api.request(Method.GET, Path.v3.rooms[room].aliases)
        for alias in aliases['aliases']:
            local_alias = re.sub(r"#(.*):.*", r'\1', alias)
            self.logger.debug(f"-> Remove alias: {alias} / {local_alias}")
            try:
                await self.client.remove_room_alias(alias_localpart=local_alias, raise_404=True)
            except MForbidden as err:
                self.logger.exception(f"Error while removing alias {alias} for room {room}: {err}")
                raise MForbidden(err.http_status, f"Error while removing alias {alias} for room {room}: {err.message}")

    def get_policy(self, policy_name):
        try:
            return self.policies[policy_name]
        except KeyError as err:
            self.logger.error(f"Policy {policy_name} not found. ({str(err)})")
            raise PolicyNotFoundError(f"Policy {policy_name} not found. ({str(err)})")

    def get_available_policies(self):
        return self.policies.keys()

    async def create_from_policy(self, policy_name, sender=None):
        try:
            self.logger.debug(f"Fetching policy {policy_name}...")
            policy = self.get_policy(policy_name)
        except PolicyNotFoundError as e:
            self.logger.error(f"Policy not found: {e}")
            available_policies = "\n- ".join(self.get_available_policies())
            return f"Policy not found: \"{e}\". Please define a policy with this name first.\nAvailable policies are:\n- {available_policies}"

        # TODO: USER-groups
        # TODO: check if policy is valid and does not exist yet (probably with database)
        self.logger.error(str(sender))
        default_invitees = {sender: 99} if sender else {}
        for key, room_data in policy['rooms'].items():
            self.logger.debug(f'Creating {room_data["id"]}')
            if 'id' not in room_data or not room_data['id']:
                self.policies[policy_name]['rooms'][key]['id'] = await create_room(
                    self.client,
                    room_data['room_name'] if 'room_name' in room_data else 'Pretty Placeholder',
                    room_data['invitees'] if 'invitees' in room_data else default_invitees,
                    self.client.mxid.split(':')[1],
                    is_space=room_data['is_space'] if 'is_space' in room_data else False,
                    parent_spaces=[self.policies[policy_name]['rooms'][ps_name]['id'] for ps_name in room_data['parent_spaces']] if 'parent_spaces' in room_data else [],
                    alias=room_data['alias'] if 'alias' in room_data else None,
                    topic=room_data['topic'] if 'topic' in room_data else '',
                    suggested=room_data['suggested'] if 'suggested' in room_data else False,
                    join_rule=room_data['join_rule'] if 'join_rule' in room_data else 'restricted',
                    encrypt=room_data['encrypted'] if 'encrypted' in room_data else False,
                )
            room_id = self.policies[policy_name]['rooms'][key]['id']
            if 'actions' in room_data:
                # Check if actions need to be run?!
                for room_action in room_data['actions']:
                    for bot_id in policy['actions'][room_action['template']]['bots']:
                        self.logger.debug(f"Inviting bot {bot_id} to {room_id}")
                        await self.client.invite_user(room_id, bot_id)
                    for cmd in policy['actions'][room_action['template']]['commands']:
                        cmd = cmd.format(**room_action['format']) if 'format' in room_action else cmd
                        self.logger.debug(f"Sending command {cmd} to {room_id}")
                        await self.client.send_markdown(room_id, cmd, msgtype=MessageType.TEXT, allow_html=True)
