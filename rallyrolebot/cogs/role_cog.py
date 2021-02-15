import json
import sys
import traceback

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


class RoleCommands(commands.Cog):
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
        name="set_role_mapping",
        help=" <coin name> <coin amount> <role name> "
        + "Set a mapping between coin and role. Roles will be constantly updated.",
    )
    @validation.owner_or_permissions(administrator=True)
    async def set_coin_for_role(
        self, ctx, coin_name, coin_amount: int, role: discord.Role
    ):
        data.add_role_coin_mapping(ctx.guild.id, coin_name, coin_amount, role.name)
        await update_cog.force_update(self.bot, ctx)

    @commands.command(
        name="one_time_role_mapping",
        help=" <coin name> <coin amount> <role name>"
        + " Set a mapping to be applied once instantly.",
    )
    @validation.owner_or_permissions(administrator=True)
    async def one_time_role_mapping(
        self, ctx, coin_name, coin_amount: int, role: discord.Role
    ):
        for member in ctx.guild.members:
            rally_id = data.get_rally_id(member.id)
            if rally_id:
                balances = rally_api.get_balances(rally_id)
                await update_cog.grant_deny_role_to_member(
                    {
                        data.GUILD_ID_KEY: ctx.guild.id,
                        data.COIN_KIND_KEY: coin_name,
                        data.REQUIRED_BALANCE_KEY: coin_amount,
                        data.ROLE_NAME_KEY: role.name,
                    },
                    member,
                    balances,
                )
        await update_cog.force_update(self.bot, ctx)

    @commands.command(
        name="unset_role_mapping",
        help=" <coin name> <coin amount> <role name> "
        + "Unset a mapping between coin and role",
    )
    @validation.owner_or_permissions(administrator=True)
    async def unset_coin_for_role(
        self, ctx, coin_name, coin_amount: int, role: discord.Role
    ):
        data.remove_role_mapping(ctx.guild.id, coin_name, coin_amount, role.name)

    # TODO: this command might run the risk of not printing due to character limit
    @commands.command(name="get_role_mappings", help="Get role mappings")
    @validation.owner_or_permissions(administrator=True)
    async def get_role_mappings(self, ctx):
        mappingsStr = "```Role   Coin   Amount\n\n"
        for mapping in data.get_role_mappings(ctx.guild.id):
            mappingsStr += f"{mapping[ROLE_NAME_KEY]}   {mapping[COIN_KIND_KEY]}   {mapping[REQUIRED_BALANCE_KEY]}\n"
        mappingsStr += "```"
        await pretty_print(
            ctx,
            mappingsStr,
            title=f"Role mappings",
            color=GREEN_COLOR,
        )
