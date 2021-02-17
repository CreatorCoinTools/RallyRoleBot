import discord
from discord.ext import commands
from cogs import *
import config
import data
import cogs


config.parse_args()
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
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

        data.delete_all_commands()
        for command in self.commands:
            data.add_command(command.name, command.help)

    async def close(self):
        await super().close()

    def run(self):
        super().run(config.CONFIG.secret_token, reconnect=True)


bot = RallyRoleBot()
if __name__ == "__main__":
    bot.run()
