import json
import traceback
from typing import Type

from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from secretary.rooms import create_room
from secretary.secretary import MatrixSecretary
from secretary.util import non_empty_string, PolicyNotFoundError


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("base_command")


class Secretary(Plugin):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.matrix_secretary = MatrixSecretary(self.client)

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

    @command.new(name=lambda self: self.config["base_command"],
                 require_subcommand=True, arg_fallthrough=False)
    async def sec(self, evt: MessageEvent) -> None:
        help_text = """
Hi, I'm here to help you manage your bots and create complex rooms settings for you.
"""
        await evt.reply(help_text)

    @sec.subcommand('maintenance', help="Set maintenance room")
    async def set_maintenance_room(self, evt: MessageEvent) -> None:
        reply = self.matrix_secretary.set_maintenance_room(evt.room_id)
        await evt.reply(reply)

    @sec.subcommand('show_policy', help="Show policy")
    @command.argument("policy_name", pass_raw=True, required=True, parser=non_empty_string)
    async def show_policy(self, evt: MessageEvent, policy_name: str) -> None:
        try:
            result = self.matrix_secretary.get_policy(policy_name)
            # convert dict to pretty printed json string
            result = json.dumps(result, indent=4)  # , sort_keys=True)
            await evt.reply(f"```\n{result}\n```", markdown=True)
        except PolicyNotFoundError as err:
            available_policies = '\n- '.join(self.matrix_secretary.get_available_policies())
            await evt.respond(f"Policy {policy_name} not available. Try one of:\n- {available_policies}")
        except Exception as err:
            await evt.respond(f"I tried, but something went wrong: \"{str(err)}\"")
            await evt.respond(f"```\n{traceback.format_exc()}\n```")

    @sec.subcommand('create', help="Create rooms as defined in passed json")
    @command.argument("policy_name", pass_raw=True, required=True, parser=non_empty_string)
    async def create_structure(self, evt: MessageEvent, policy_name: str) -> None:
        try:
            result = await self.matrix_secretary.create_from_policy(policy_name, evt.sender)
        except Exception as e:
            await evt.respond(f"I tried, but something went wrong: \"{e}\"")
            await evt.respond(f"```\n{traceback.format_exc()}\n```")
            return
        await evt.reply(result)

    @sec.subcommand('clear', help="Clear rooms that this is the only non-bot user in")
    async def clear(self, evt: MessageEvent) -> None:
        reply = await self.matrix_secretary.clear_rooms(only_abandoned=True)
        await evt.reply(reply, markdown=True)

    @sec.subcommand('clear_all', help="Clear ALL rooms")
    async def clear_all(self, evt: MessageEvent) -> None:
        reply = await self.matrix_secretary.clear_rooms(only_abandoned=False)
        await evt.reply(reply, markdown=True)
