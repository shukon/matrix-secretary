import json
import traceback
from typing import Type

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

    @sec.subcommand('set-notice-room', help="Set notice room")
    async def set_notice_room(self, evt: MessageEvent) -> None:
        reply = await self.matrix_secretary.set_notice_room(evt.room_id)
        await evt.reply(reply)

    @sec.subcommand('show-policy', help="Show policy")
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
            await evt.respond(f"Policy {policy_name} not available. Try one of:")
            # send markdown message
            await self.client.send_markdown(evt.room_id, f"Try one of:\n- {available_policies})")
        except Exception as err:
            self.matrix_secretary.logger.exception(err)
            await evt.respond(f"{echo('generic_error', self.lang)}: \"{str(err)}\"")
            await evt.respond(f"```\n{traceback.format_exc()}\n```")

    @sec.subcommand('load-sample-policies', help="Load example policies")
    async def load_sample_policies(self, evt: MessageEvent) -> None:
        await self.matrix_secretary.load_example_policies()
        await evt.respond("Loaded example policies from secretary/example_policies.")
        await self.list_policies(evt)

    @sec.subcommand('list-policies', help="Show all policies")
    async def list_policies(self, evt: MessageEvent) -> None:
        policies = await self.matrix_secretary.get_available_policies()
        await evt.respond("Available policies:\n  " + '\n  '.join(policies))

    @sec.subcommand('ensure-policy', help="Create rooms as defined in passed json")
    @command.argument("policy_key", pass_raw=True, required=True, parser=non_empty_string)
    async def ensure_policy(self, evt: MessageEvent, policy_key: str) -> None:
        try:
            await self.matrix_secretary.ensure_policy(policy_key)
            await evt.reply("Policy implemented")
        except Exception as e:
            await log_error(self.matrix_secretary.logger, e, evt=evt)

    @sec.subcommand('add-policy', help="Create rooms as defined in passed json")
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

    @sec.subcommand('destroy-policy', help="Remove policy and delete rooms")
    @command.argument("policy_key", pass_raw=True, required=True, parser=non_empty_string)
    async def rm_policy(self, evt: MessageEvent, policy_key: str) -> None:
        await self.matrix_secretary.ensure_policy_destroyed(policy_key)
        await evt.respond(f"Removed policy {policy_key}")

    @sec.subcommand('clean-rooms', help="Clean up unused rooms")
    async def clean_rooms(self, evt: MessageEvent) -> None:
        await self.matrix_secretary.delete_all_rooms(only_abandoned=True)
        await evt.respond("Cleared all rooms")

    @classmethod
    def get_db_upgrade_table(cls) -> UpgradeTable | None:
        return get_upgrade_table()
