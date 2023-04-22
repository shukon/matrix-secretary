from typing import Type, Union

from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.util.async_db import UpgradeTable
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from secretary.rooms import create_room
from secretary.secretary import MatrixSecretary
from secretary.translations import echo
from secretary.util import non_empty_string, PolicyNotFoundError, get_upgrade_table


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
        pass

    @sec.subcommand('set_maintenance_room', help="Set maintenance room")
    async def set_maintenance_room(self, evt: MessageEvent) -> None:
        pass

    @sec.subcommand('show_policy', help="Show policy")
    @command.argument("policy_key", pass_raw=True, required=True, parser=non_empty_string)
    async def show_policy(self, evt: MessageEvent, policy_name: str) -> None:
        pass

    @sec.subcommand('list_policies', help="Show all policies")
    async def list_policies(self, evt: MessageEvent) -> None:
        await self.matrix_secretary.load_example_policies()
        policies = await self.matrix_secretary.get_available_policies()
        await evt.respond("Available policies:\n  " + '\n  '.join(policies))

    @sec.subcommand('ensure_policy', help="Create rooms as defined in passed json")
    @command.argument("policy_name", pass_raw=True, required=True, parser=non_empty_string)
    async def ensure_policy(self, evt: MessageEvent, policy_name: str) -> None:
        await self.matrix_secretary.ensure_policy(policy_name)
        await evt.respond(f"Ensured policy {policy_name}")

    @sec.subcommand('add_policy', help="Create rooms as defined in passed json")
    @command.argument("policy_key", pass_raw=True, required=True, parser=non_empty_string)
    async def add_policy(self, evt: MessageEvent, policy_name: str) -> None:
        pass

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
