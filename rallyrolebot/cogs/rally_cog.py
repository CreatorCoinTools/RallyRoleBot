import json
import sys
import traceback
from typing import Union

import discord
from discord import Color
from discord.ext import commands, tasks
from discord.utils import get

import data
import rally_api
import coingecko_api
import validation
import errors

from urllib.parse import urlencode

from utils import pretty_print, send_to_dm, gradient
from utils.converters import CreatorCoin, CommonCoin, CurrencyType
from constants import *


class RallyCommands(commands.Cog):
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

    @commands.command(name="set_rally_id", help="Set your rally id")
    @commands.dm_only()
    async def set_rally_id(self, ctx, rally_id):
        data.add_discord_rally_mapping(ctx.author.id, rally_id)

    @commands.command(name="price", help="Get the price data of a coin")
    async def price(self, ctx, coin: Union[CreatorCoin, CommonCoin]):
        def get_gradient_color(percentage):

            percentage = 50 + int(percentage) / 2
            return gradient(
                Color.red(),
                Color.magenta(),
                Color.lighter_grey(),
                Color.teal(),
                Color.green(),
                percentage=percentage,
            )

        data = coin["data"]

        percentage_24h = data["price_change_percentage_24h"]
        percentage_30d = data["price_change_percentage_30d"]

        if not data:
            raise errors.RequestError("There was an error while fetching the coin data")
        else:
            await pretty_print(
                ctx,
                f"Current Price: {data['current_price']}",
                title="Current Price",
                color=WHITE_COLOR,
            )
            await pretty_print(
                ctx,
                f"{percentage_24h}%",
                title="24H Price Change",
                color=get_gradient_color(percentage_24h),
            )
            await pretty_print(
                ctx,
                f"{percentage_30d}%",
                title="30D Price Change",
                color=get_gradient_color(percentage_30d),
            )

    @commands.command(name="unset_rally_id", help="Unset your rally id")
    @commands.dm_only()
    async def unset_rally_id(self, ctx, rally_id):
        data.remove_discord_rally_mapping(ctx.author.id, rally_id)

 
    @commands.command(
        name="coinlink",
        help="To generate a custom coin link, type $coinlink <CoinName> <COIN/USD> <Amount> <Memo>",
    )
    async def generate_coinlink_deeplink(
        self,
        ctx,
        coin: Union[CreatorCoin, CommonCoin],
        currencyType: CurrencyType,
        amount: int,
        memo: str,
    ):

        params = {"inputType": currencyType, "amount": amount, "note": memo}
        deeplink = (
            "https://www.rally.io/creator/" + coin["symbol"] + "/?" + urlencode(params)
        )

        await pretty_print(deeplink)


    @commands.command(name="balance", help="View your balance")
    @commands.dm_only()
    @validation.is_wallet_verified()
    async def balance(self, ctx):
        rally_id = data.get_rally_id(ctx.message.author.id)
        balances = rally_api.get_balances(rally_id)

        balanceStr = ""

        for balance in balances:
            balanceStr += f"{balance['coinKind']}: {balance['coinBalance']} (Est. USD$ {balance['estimatedInUsd']})\n"

        await pretty_print(
            ctx,
            balanceStr,
            title=f"{ctx.message.author.name}'s Balance",
            color=WARNING_COLOR,
        )

