from discord.ext import commands

import rally_api
import coingecko_api
import errors


class CommonCoin(commands.Converter):
    async def convert(self, ctx, argument):
        valid = coingecko_api.valid_coin(argument)
        if not valid:
            raise errors.InvalidCoin("Invalid coin symbol")

        data = coingecko_api.get_price_data(argument)
        return {"symbol": argument, "data": data}


class CreatorCoin(commands.Converter):
    async def convert(self, ctx, argument):
        valid = rally_api.valid_coin_symbol(argument)
        if not valid:
            raise errors.InvalidCoin("Invalid coin symbol")

        data = rally_api.get_price_data(argument)
        return {"symbol": argument, "data": data}


class CurrencyType(commands.Converter):
    async def convert(self, ctx, argument):
        currencyType = argument.upper()
        if currencyType != "USD" and currencyType != "COIN":
            raise errors.BadArgument("<currencyType> must be USD or COIN")

        return currencyType


class TimeframeType(commands.Converter):
    async def convert(self, ctx, argument):
        timeframe = argument.lower()
        if timeframe not in ['day', 'week']:
            raise errors.BadArgument("<timeframe> argument must be day or week")

        return timeframe
