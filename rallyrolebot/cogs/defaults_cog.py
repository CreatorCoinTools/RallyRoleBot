import json
import sys
import traceback
import asyncio

import discord
from discord.ext import commands, tasks
from discord.utils import get

import data
import rally_api
import validation
import errors

from cogs import update_cog

from constants import *
from utils import pretty_print


class DefaultsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_after_invoke(self, ctx):
        await pretty_print(
            ctx, "Command completed successfully!", title="Success", color=SUCCESS_COLOR
        )

    @errors.standard_error_handler
    async def cog_command_error(self, ctx, error):
        # All other Errors not returned come here. And we can just print the default TraceBack.
        print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

    @commands.command(
        name="set_default_coin",
        help=" <coin name> Set a default coin to be used across the server",
    )
    @validation.owner_or_permissions(administrator=True)
    async def set_default_coin(self, ctx, coin_name):
        await pretty_print(
            ctx,
            f"Are you sure you want to set {coin_name} as default coin?",
            caption="Give 👍 reaction to confirm",
            title="Warning",
            color=WARNING_COLOR,
        )

        def check(reaction, user):
            return user == ctx.message.author and str(reaction.emoji) == "👍"

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await pretty_print(
                ctx, "Set default coin timed out 👎", title="Timeout", color=ERROR_COLOR
            )
        else:
            data.add_default_coin(ctx.guild.id, coin_name)
            await pretty_print(
                ctx,
                f"{coin_name} is now the default coin 👍",
                title="Set",
                color=GREEN_COLOR,
            )

    @commands.command(
        name="change_prefix",
        help=" <prefix> Prefix for bot commands",
    )
    @validation.owner_or_permissions(administrator=True)
    async def set_prefix(self, ctx, prefix):
        data.add_prefix_mapping(ctx.guild.id, prefix)

    @commands.command(
        name="role_call",
        help=" <role> Display users who have access to a given role",
    )
    @validation.owner_or_permissions(administrator=True)
    async def role_call(self, ctx, role: discord.Role):
        usersStr = ""
        for member in ctx.guild.members:
            if role in member.roles:
                usersStr += f"{member}\n"
        await pretty_print(
            ctx,
            usersStr,
            title=f"Users with {role} role",
            color=GREEN_COLOR,
        )

    @commands.command(
        name="list_all_users",
        help="Display users who have been registered",
    )
    @validation.owner_or_permissions(administrator=True)
    async def list_all_users(self, ctx):
        usersStr = ""
        registered_users = data.get_all_users()
        for user in registered_users:
            member = await ctx.guild.fetch_member(user[DISCORD_ID_KEY])
            usersStr += f"{member}\nRallyId: {user[RALLY_ID_KEY]}\nDiscordId: {user[DISCORD_ID_KEY]}\n\n"
        await pretty_print(
            ctx,
            usersStr,
            title=f"All registered users",
            color=GREEN_COLOR,
        )

    @commands.command(
        name="change_bot_name",
        help="Change the bot's name on this server"
    )
    @validation.owner_or_permissions(administrator=True)
    async def set_bot_name(self, ctx, name):
        data.set_bot_name(ctx.guild.id, name)
        await update_cog.force_update(self.bot, ctx)