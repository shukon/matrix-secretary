import json
import traceback
from typing import Type, Union

from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.util.async_db import UpgradeTable
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from secretary.database import get_upgrade_table
from secretary.rooms import create_room
from secretary.secretary import MatrixSecretary
from secretary.translations import echo
from secretary.util import non_empty_string, PolicyNotFoundError, log_error


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("base_command")


class Secretary(Plugin):

    ############################
    # Basic plugin boilerplate #
    ############################

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.lang = "en"
        self.matrix_secretary = MatrixSecretary(self.client, self.database)

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

    ############################
    # Plugin specific commands #
    ############################

    @command.new(name=lambda self: self.config["base_command"],
                 require_subcommand=True, arg_fallthrough=False)
    async def sec(self, evt: MessageEvent) -> None:
        await evt.reply(echo("helptext", self.lang))

    @sec.subcommand('set_maintenance_room', help="Set maintenance room")
    async def set_maintenance_room(self, evt: MessageEvent) -> None:
        reply = await self.matrix_secretary.set_maintenance_room(evt.room_id)
        await evt.reply(reply)

    @sec.subcommand('show_policy', help="Show policy")
    @command.argument("policy_key", pass_raw=True, required=True, parser=non_empty_string)
    async def show_policy(self, evt: MessageEvent, policy_name: str) -> None:
        try:
            result = self.matrix_secretary.get_policy(policy_name)
            # convert dict to pretty printed json string
            result = json.dumps(result, indent=4)  # , sort_keys=True)
            await evt.reply(f"```\n{result}\n```", markdown=True)
        except PolicyNotFoundError as err:
            self.matrix_secretary.logger.exception(err)
            available_policies = '\n- '.join(await self.matrix_secretary.get_available_policies())
            await evt.respond(f"Policy {policy_name} not available. Try one of:\n- {available_policies}")
        except Exception as err:
            self.matrix_secretary.logger.exception(err)
            await evt.respond(f"{echo('generic_error', self.lang)}: \"{str(err)}\"")
            await evt.respond(f"```\n{traceback.format_exc()}\n```")

    @sec.subcommand('list_policies', help="Show all policies")
    async def list_policies(self, evt: MessageEvent) -> None:
        await self.matrix_secretary.load_example_policies()
        policies = await self.matrix_secretary.get_available_policies()
        await evt.respond("Available policies:\n  " + '\n  '.join(policies))

    @sec.subcommand('ensure_policy', help="Create rooms as defined in passed json")
    @command.argument("policy_name", pass_raw=True, required=True, parser=non_empty_string)
    async def ensure_policy(self, evt: MessageEvent, policy_name: str) -> None:
        try:
            await self.matrix_secretary.ensure_policy(policy_name)
            await evt.reply("Policy implemented")
        except Exception as e:
            await log_error(self.matrix_secretary.logger, e, evt=evt)

    @sec.subcommand('add_policy', help="Create rooms as defined in passed json")
    @command.argument("policy_as_json", pass_raw=True, required=True, parser=non_empty_string)
    async def add_policy(self, evt: MessageEvent, policy_as_json: str) -> None:
        try:
            policy_as_json = json.loads(policy_as_json)
            await self.matrix_secretary.add_policy(policy_as_json)
            await self.matrix_secretary.ensure_policy(policy_as_json['policy_key'])
        except Exception as err:
            await log_error(self.matrix_secretary.logger, err, evt=evt)
            return
        await evt.reply("Successfully added policy")

    @sec.subcommand('rm_policy', help="Remove policy and optionally delete rooms")
    @command.argument("policy_key", pass_raw=True, required=True, parser=non_empty_string)
    @command.argument("delete_rooms", required=False, parser=bool)
    async def rm_policy(self, evt: MessageEvent, policy_name: str, delete_rooms: Union[bool, None] = False) -> None:
        if delete_rooms:
            await self.matrix_secretary.ensure_policy_destroyed(policy_name)
        else:
            await self.matrix_secretary.forget_policy(policy_name)
        await evt.respond(f"Removed policy {policy_name}")

    @sec.subcommand('clear', help="Clear rooms that this is the only non-bot user in")
    async def clear(self, evt: MessageEvent) -> None:
        pass

    @sec.subcommand('clear_all', help="Clear ALL rooms")
    async def clear_all(self, evt: MessageEvent) -> None:
        await self.matrix_secretary.delete_all_rooms()
        await evt.respond("Cleared all rooms")

    @classmethod
    def get_db_upgrade_table(cls) -> UpgradeTable | None:
        return get_upgrade_table()
