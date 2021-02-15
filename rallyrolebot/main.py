import discord
from discord.ext import commands
from cogs import *
import asyncio
import config
import data
import cogs
import functools
import app
import signal


config.parse_args()
intents = discord.Intents.all()
default_prefix = config.CONFIG.command_prefix


def prefix(bot, ctx):
    try:
        guildId = ctx.guild.id
        return data.get_prefix(guildId) or default_prefix
    except:
        return default_prefix


class RallyRoleBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix, case_insensitive=True, intents=intents,
                         chunk_guilds_at_startup=True)

        self.add_cog(cogs.role_cog.RoleCommands(self))
        self.add_cog(cogs.channel_cog.ChannelCommands(self))
        self.add_cog(cogs.rally_cog.RallyCommands(self))
        self.add_cog(cogs.defaults_cog.DefaultsCommands(self))
        self.add_cog(cogs.update_cog.UpdateTask(self))

        for command in self.commands:
            data.add_command(command.name, command.help)

    def run(self, *args, **kwargs):
        loop = asyncio.get_event_loop()

        async def _stop(*a):
            # shutdown api
            if app.server.should_exit:
                app.server.force_exit = True
            else:
                app.server.should_exit = True

            await asyncio.wait_for(app.server.shutdown(), timeout=1000)

            # close loop and shutdown discord bot
            loop.stop()

        try:
            func = functools.partial(asyncio.create_task, _stop())
            loop.add_signal_handler(signal.SIGINT, func)
            loop.add_signal_handler(signal.SIGTERM, func)
        except NotImplementedError:
            pass

        async def runner():
            asyncio.create_task(app.run(loop))
            try:
                await self.start(*args, **kwargs)
            finally:
                if not self.is_closed():
                    await self.close()

        def stop_loop_on_completion(f):
            loop.stop()

        future = asyncio.ensure_future(runner(), loop=loop)
        future.add_done_callback(stop_loop_on_completion)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            future.remove_done_callback(stop_loop_on_completion)
            discord.client._cleanup_loop(loop)

        if not future.cancelled():
            try:
                return future.result()
            except KeyboardInterrupt:
                # I am unsure why this gets raised here but suppress it anyway
                return None


bot = RallyRoleBot()
if __name__ == '__main__':
    bot.run(config.CONFIG.secret_token)
