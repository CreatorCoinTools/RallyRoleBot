import json
import sys
import time
import traceback
import asyncio
import datetime
import discord
from discord.ext import commands, tasks
from discord.utils import get

from constants import *
import data
import rally_api
import validation
import errors
import aiohttp

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

    async def update_setting(self, ctx, alert, channel, value, setting):
        if not alert or not channel or not value:
            return await pretty_print(ctx, "Missing <alert>, <channel> or <value>", title='Error', color=ERROR_COLOR)

        channel_object = None
        if type(channel) == str:
            channel_object = discord.utils.get(ctx.guild.channels, name=channel)
        elif ctx.message.channel_mentions:
            channel_object = ctx.message.channel_mentions[0]

        if not channel_object:
            return await pretty_print(ctx, "Invalid <channel>", title='Error', color=ERROR_COLOR)

        settings = data.get_alerts_settings(ctx.guild.id)
        if not settings:
            return await pretty_print(ctx, "Alert settings have not been configured on the dashboard", title='Error', color=ERROR_COLOR)

        settings = settings[ALERTS_SETTINGS_KEY]

        if alert not in settings:
            return await pretty_print(ctx, "Invalid <Alert>", title='Error', color=ERROR_COLOR)

        instance = [i for (i, instance) in enumerate(settings[alert]['instances']) if
                    instance['channel'] == channel_object.name]
        if not instance:
            return await pretty_print(ctx, "Couldn't find an entry with that channel name", title='Error', color=ERROR_COLOR)

        settings[alert]['instances'][instance[0]]['settings'][setting] = value
        data.set_alerts_settings(ctx.guild.id, json.dumps(settings))

        return await pretty_print(ctx, "Alert settings have been updated", title='Success', color=SUCCESS_COLOR)

    @commands.command(
        name='setmin',
        help='<alert> <channel> <value> - Set the minimum amount for an alert'
    )
    async def setmin(self, ctx, alert=None, channel=None, value=None):
        return await self.update_setting(ctx, alert, channel, value, 'minamount')

    @commands.command(
        name='setmax',
        help='<alert> <channel> <value> - Set the minimum amount for an alert'
    )
    async def setmax(self, ctx, alert=None, channel=None, value=None):
        return await self.update_setting(ctx, alert, channel, value, 'maxamount')

    @commands.command(
        name='settimezone',
        help='<channel> <value (-12 - +12)> - Set timezone setting for daily stats message'
    )
    async def settimezone(self, ctx, channel=None, value=None):
        return await self.update_setting(ctx, 'daily_stats', channel, value, 'timezone')

    @commands.command(
        name='allcoinstats',
        help='<day/week> - list the following stats in the coin alerts channel based on the time given'
    )
    async def allcoinstats(self, ctx, timeframe=''):
        timeframe = timeframe.lower()
        if timeframe not in ['day', 'week']:
            return await pretty_print(
                ctx, "Invalid timeframe, please type `day` or `week`", title="Error", color=ERROR_COLOR
            )

        default_coin = data.get_default_coin(ctx.guild.id)
        if not default_coin:
            return await pretty_print(
                ctx, "A default coin has not been set. An admin can set the default coin by typing $setdefaultcoin . Type $help for more information.", title="Error", color=ERROR_COLOR
            )

        coin_day_stats = data.get_coin_stats_day(default_coin)
        total_stats = rally_api.get_coin_summary(default_coin)
        rewards = rally_api.get_coin_rewards(default_coin)
        coin_image_url = rally_api.get_coin_image_url(default_coin)

        extra_str = 'Today' if timeframe == 'day' else 'This Week'
        reward_str = 'last24HourEarned' if timeframe == 'day' else 'weeklyAccumulatedReward'
        message = {
            "description": f"```xl\n"
                           f"- {extra_str}`s # of purchases: {coin_day_stats[PURCHASES_KEY]}\n\n"
                           f"- {extra_str}`s # of donations: {coin_day_stats[DONATIONS_KEY]}\n\n"
                           f"- {extra_str}`s # of transfers: {coin_day_stats[TRANSFERS_KEY]}\n\n"
                           f"- {extra_str}`s # of conversions: {coin_day_stats[CONVERSIONS_KEY]}\n\n"
                           f"- {extra_str}`s # of redeems: {coin_day_stats[REDEEMS_KEY]}\n\n"
                           f"- {extra_str}`s # of rewards earned: {rewards[reward_str]}\n"
                           f"```",
            "color": 0xff0000,
            "author": {
                "name": f"{default_coin} Stats {extra_str}",
                "icon_url": coin_image_url
            },
            "timestamp": datetime.datetime.now().isoformat()
        }

        embed = discord.Embed.from_dict(message)
        return await ctx.send(embed=embed)

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
        name="change_bot_name",
        help="Change the bot's name on this server"
    )
    @commands.is_owner()
    async def set_bot_name(self, ctx, *, name=""):
        try:
            await self.bot.user.edit(username=name)
            data.set_bot_name(ctx.guild.id, name)
        except Exception as e:
            return await ctx.send(f'Error: {e.text.split(":")[-1]}')

    @commands.command(
        name="change_bot_avatar",
        help="Changes the bot's avatar"
    )
    @commands.is_owner()
    async def set_bot_avatar(self, ctx, url=None):
        if url is None:
            url = DEFAULT_BOT_AVATAR_URL

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    avatar = await response.read()

            await self.bot.user.edit(avatar=avatar)
            data.set_bot_avatar(ctx.guild.id, url)
        except:
            return await ctx.send('Error setting new bot avatar')

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
