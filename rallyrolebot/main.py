import discord
import config
import data
import os
import asyncio

from constants import *
from utils.timers import Timers
from discord.ext import commands

config.parse_args()
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
default_prefix = config.CONFIG.command_prefix

main_bot = None
running_bots = {}
running_bot_instances = []


def prefix(_, ctx):
    try:
        return data.get_prefix(ctx.guild.id) or default_prefix
    except:
        return default_prefix


class RallyRoleBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=prefix, case_insensitive=True, intents=intents,
            chunk_guilds_at_startup=True
        )

        # Load Cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and filename != '__init__.py':
                self.load_extension(f'cogs.{filename[:-3]}')

        data.delete_all_commands()
        for command in self.commands:
            data.add_command(command.name, command.help)

        self.timers = Timers(self)

    @staticmethod
    async def start_bot_instance(token: str) -> None:
        """
        Stats a bot instance.

        @param token: Bot token
        """
        new_bot = RallyRoleBot()
        try:
            # start up bot instance
            await new_bot.start(token)
        finally:
            # close if needed
            if not new_bot.is_closed():
                await new_bot.close()

        # remove bot from running bot instances
        if token in running_bot_instances:
            running_bot_instances.remove(token)

    async def run_bot_instances(self) -> None:
        """Start up all the bot instances."""
        # get all bot instances
        all_bot_instances = data.get_all_bot_instances()
        if all_bot_instances:
            for instance in all_bot_instances:
                # add bot token to list of running bot instances
                running_bot_instances.append(instance[BOT_TOKEN_KEY])
                # create task for bot start function
                asyncio.create_task(self.start_bot_instance(instance[BOT_TOKEN_KEY]))

    async def close(self):
        await super().close()

    def run(self):
        super().run(config.CONFIG.secret_token, reconnect=True)


if __name__ == "__main__":
    bot = RallyRoleBot()
    bot.run()
