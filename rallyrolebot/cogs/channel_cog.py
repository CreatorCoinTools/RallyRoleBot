import json
import sys
import traceback

import discord
from discord.ext import commands, tasks
from discord.utils import get

import errors
import data
import validation
import rally_api

from cogs import update_cog

from utils import pretty_print
from constants import *


class ChannelCommands(commands.Cog):

    """
    Cog for processing commands from a specifc channel.
    Deals with removing, adding, and viewing mappings from Creator Coin to a channel.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_after_invoke(self, ctx):
        await pretty_print(
            ctx, "Command completed successfully!", title="Success", color=SUCCESS_COLOR
        )

    @errors.standard_error_handler
    async def cog_command_error(self, ctx, error):
        """
        A special method that is called whenever an error is dispatched inside this cog.
        This is similar to on_command_error() except only applying to the commands inside this cog.

        Parameters
        __________

          ctx (Context) – The invocation context where the error happened.
          error (CommandError) – The error that happened.

        """

        print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

    @commands.command(
        name="set_channel_mapping",
        help=" <coin name> <coin amount> <channel name> "
        + "Set a mapping between coin and channel. Channel membership will be constantly updated.",
    )
    @validation.owner_or_permissions(administrator=True)
    async def set_coin_for_channel(
        self, ctx, coin_name, coin_amount: int, channel: discord.TextChannel
    ):
        data.add_channel_coin_mapping(
            ctx.guild.id, coin_name, coin_amount, channel.name
        )
        await update_cog.force_update(self.bot, ctx)

    @commands.command(
        name="one_time_channel_mapping",
        help=" <coin name> <coin amount> <channel name>"
        + " Grant/deny access to a channel instantly.",
    )
    @validation.owner_or_permissions(administrator=True)
    async def one_time_channel_mapping(
        self, ctx, coin_name, coin_amount: int, channel: discord.TextChannel
    ):

        for member in ctx.guild.members:
            rally_id = data.get_rally_id(member.id)
            if rally_id:
                balances = rally_api.get_balances(rally_id)
                await update_cog.grant_deny_channel_to_member(
                    {
                        data.GUILD_ID_KEY: ctx.guild.id,
                        data.COIN_KIND_KEY: coin_name,
                        data.REQUIRED_BALANCE_KEY: coin_amount,
                        data.CHANNEL_NAME_KEY: channel.name,
                    },
                    member,
                    balances,
                )
        await update_cog.force_update(self.bot, ctx)

    @commands.command(
        name="unset_channel_mapping",
        help=" <coin name> <coin amount> <channel name> "
        + "Unset a mapping between coin and channel",
    )
    @validation.owner_or_permissions(administrator=True)
    async def unset_coin_for_channel(
        self, ctx, coin_name, coin_amount: int, channel: discord.TextChannel
    ):
        data.remove_channel_mapping(ctx.guild.id, coin_name, coin_amount, channel.name)

    @commands.command(name="get_channel_mappings", help="Get channel mappings")
    @validation.owner_or_permissions(administrator=True)
    async def get_channel_mappings(self, ctx):
        mappingsStr = "```Channel   Coin   Amount\n\n"
        for mapping in data.get_channel_mappings(ctx.guild.id):
            mappingsStr += f"{mapping[CHANNEL_NAME_KEY]}   {mapping[COIN_KIND_KEY]}   {mapping[REQUIRED_BALANCE_KEY]}\n"
        mappingsStr += "```"
        await pretty_print(
            ctx,
            mappingsStr,
            title=f"Role mappings",
            color=GREEN_COLOR,
        )

    @commands.command(name="set_purchase_message", help="Change the $purchase message")
    @validation.owner_or_permissions(administrator=True)
    async def set_purchase_message(self, ctx, *, message):
        data.set_purchase_message(ctx.guild.id, message)

    @commands.command(name="purchase", help="Learn how you can purchase")
    @commands.guild_only()
    async def purchase(self, ctx):
        message = data.get_purchase_message(ctx.guild.id)
        if message is not None:
            await ctx.send(message)
        else:
            await ctx.send(DEFAULT_PURCHASE_MESSAGE)

    @commands.command(name="set_donate_message", help="Change the $donate message")
    @validation.owner_or_permissions(administrator=True)
    async def set_donate_message(self, ctx, *, message):
        data.set_donate_message(ctx.guild.id, message)

    @commands.command(name="donate", help="Learn how you can donate")
    @commands.guild_only()
    async def donate(self, ctx):
        message = data.get_donate_message(ctx.guild.id)
        if message is not None:
            await ctx.send(message)
        else:
            await ctx.send(DEFAULT_DONATE_MESSAGE)
