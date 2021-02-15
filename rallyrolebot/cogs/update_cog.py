import sys
import traceback
import threading
import time
import datetime
import discord
import discord.utils
import json
import re

from discord.ext import commands, tasks
from discord.utils import get
from constants import *

import aiohttp

import config
import asyncio
import errors
import data
import rally_api
import validation
import requests
from utils import pretty_print

main_bot = None
running_bots = {}
running_bot_instances = []


webhook_message_data = {
    'buy': {
        "description": "**{data[username]}** has purchased **{data[amountOfCoin]}** coins of **{coinKind}!**",
    },
    'donate': {
        "description": "**{data[fromUsername]}** has donated **{data[amountOfCoin]}** coins of **{coinKind}!**",
    },
    'transfer': {
        "description": "**{data[fromUsername]}** has transferred **{data[amountOfCoin]}** coins of **{coinKind}!**",
    },
    'convert': {
        "description": "**{data[username]}** has converted **{data[fromAmount]}** coins of **{data[fromCoinKind]}** to **{data[toAmount]}** coins of **{data[toCoinKind]}!**",
    },
    'redeem': {
        "description": "**{data[username]}** has redeemed **{data[amountOfCoin]}** coins of **{coinKind}!**",
    }
}


default_avatar = ''


async def set_default_avatar():
    global default_avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(DEFAULT_BOT_AVATAR_URL) as response:
            default_avatar = await response.read()


async def format_alert_message(event, payload, instance):
    if instance['settings']['customMessage']:
        description = instance['settings']['customMessage']
    else:
        description = webhook_message_data[event]['description']

    if instance['settings']['customTitle']:
        title = instance['settings']['customTitle']
    else:
        title = 'Alert!'

    if instance['settings']['customColour']:
        colour = instance['settings']['customColour']
    else:
        colour = '#ff0000'

    colour = int(colour.replace('#', '0x'), 16)

    if 'showUsername' not in payload['data'] or not payload['data']['showUsername']:
        payload['data']['username'] = 'someone'

    coin_image_url = rally_api.get_coin_image_url(payload['coinKind'])

    payload.update(payload['data'])

    if event == 'convert':
        payload['valueInUSD'] = payload['valueInUSCents'] // 100
    elif event == 'redeem':
        payload['estimatedAmountInUSD'] = payload['estimatedAmountInUSCents'] // 100
    else:
        payload['costInUSD'] = payload['costInUSCents'] // 100

    variables = re.findall(r'({\w+})', description)
    for var in variables:
        try:
            description = description.replace(var, var.format(**payload))
        except:
            continue

    message = {
        "embeds": [
            {
                "description": description,
                "color": colour,
                "author": {
                    "name": title,
                    "icon_url": coin_image_url
                },
                "timestamp": payload['data']['createdDate']
            }
        ]
    }
    return message


async def get_webhook_url(guild_id, channel_name):
    bot_instance = data.get_bot_instance(guild_id)
    if not bot_instance:
        bot_object = main_bot
    else:
        bot_object = running_bots[bot_instance[BOT_ID_KEY]]['bot']

    await bot_object.wait_until_ready()

    guild_object = bot_object.get_guild(int(guild_id))
    if not guild_object:
        guild_object = await bot_object.fetch_guild(guild_id)
        if not guild_object:
            return

    channel_object = discord.utils.get(guild_object.channels, name=channel_name)
    if not channel_object:
        return

    webhook = data.get_webhook(guild_id, channel_object.id)
    if not webhook:
        try:
            webhook_object = await channel_object.create_webhook(name='RallyBotAlerts', avatar=default_avatar)
            data.add_webhook(guild_id, channel_object.id, webhook_object.url, webhook_object.id, webhook_object.token)
            webhook_url = webhook_object.url
        except:
            return
    else:
        webhook_url = webhook[WEBHOOK_URI]

    return webhook_url


async def process_payload(payload: dict):
    # add to stats
    coin_kind = payload['coinKind']
    coin_stats_day = data.get_coin_stats_day(coin_kind)
    if not coin_stats_day:
        coin_stats_day = {
            COIN_KIND_KEY: coin_kind,
            PURCHASES_KEY: 0,
            DONATIONS_KEY: 0,
            TRANSFERS_KEY: 0,
            CONVERSIONS_KEY: 0,
            REDEEMS_KEY: 0
        }

    event_to_stats_switch = {
        'buy': PURCHASES_KEY,
        'donate': DONATIONS_KEY,
        'transfer': TRANSFERS_KEY,
        'convert': CONVERSIONS_KEY,
        'redeem': REDEEMS_KEY,
    }

    event = payload['event'].lower()
    coin_stats_day[event_to_stats_switch.get(event)] += 1

    data.add_coin_stats_day(**coin_stats_day)

    # send webhook message
    alerts_settings = data.get_all_alerts_settings()
    for settings in alerts_settings:
        settings_data = json.loads(settings[ALERTS_SETTINGS_KEY])
        guild_id = int(settings[GUILD_ID_KEY])
        default_coin = data.get_default_coin(str(guild_id))
        if not default_coin:
            continue

        if not settings_data[event]['enabled']:
            continue

        for instance in settings_data[event]['instances']:
            if not instance['channel']:
                continue

            if 'minamount' not in instance['settings'] or not instance['settings']['minamount']:
                instance['settings']['minamount'] = 0.0

            if 'maxamount' not in instance['settings'] or not instance['settings']['maxamount'] or instance['settings']['maxamount'] == 0:
                instance['settings']['maxamount'] = sys.maxsize

            coin_amount = payload['data']['amountOfCoin'] if payload['event'] != 'convert' else payload['data']['fromAmount']
            # check if amount is between limits
            if float(instance['settings']['minamount']) <= float(coin_amount) <= float(instance['settings']['maxamount']):
                webhook_url = await get_webhook_url(guild_id, instance['channel'])
                if not webhook_url:
                    continue

                message = await format_alert_message(event, payload, instance)
                requests.post(webhook_url, json=message)


async def grant_deny_channel_to_member(channel_mapping, member, balances):
    """
    Determine if the rally_id and balance for a channel is still valid for a particular member
    Update status in database.

    Parameters
    __________

      channel_mapping  (list) - list of information for the channel mapped to the member
      member (discord.Member) - The discord member to check
      balances (list)  - The amount of coin allocated to this member per coin

    """

    print("Checking channel")
    rally_id = data.get_rally_id(member.id)
    if rally_id is None or balances is None:
        return
    matched_channels = [
        channel
        for channel in member.guild.channels
        if channel.name == channel_mapping[data.CHANNEL_NAME_KEY]
    ]
    if len(matched_channels) == 0:
        return

    channel_to_assign = matched_channels[0]
    if channel_to_assign is not None:
        if (
            rally_api.find_balance_of_coin(
                channel_mapping[data.COIN_KIND_KEY], balances
            )
            >= channel_mapping[data.REQUIRED_BALANCE_KEY]
        ):
            perms = channel_to_assign.overwrites_for(member)
            perms.send_messages = True
            perms.read_messages = True
            perms.read_message_history = True
            await channel_to_assign.set_permissions(member, overwrite=perms)
            print("Assigned channel to member")
        else:
            perms = channel_to_assign.overwrites_for(member)
            perms.send_messages = False
            perms.read_messages = False
            perms.read_message_history = False
            await channel_to_assign.set_permissions(member, overwrite=perms)
            print("Removed channel to member")
    else:
        print("Channel not found")


async def grant_deny_role_to_member(role_mapping, member, balances):
    """
    Determine if the rally_id and balance for a role is still valid for a particular member
    Update status in database.

    Parameters
    __________

      channel_mapping (list) - list of information for the channel mapped to the member
      member (discord.Member) - The discord member to check
      balances (list)  - The amount allocated to this member per coin

    """

    rally_id = data.get_rally_id(member.id)
    if rally_id is None or balances is None:
        return
    role_to_assign = get(member.guild.roles, name=role_mapping[data.ROLE_NAME_KEY])
    if (
        rally_api.find_balance_of_coin(role_mapping[data.COIN_KIND_KEY], balances)
        >= role_mapping[data.REQUIRED_BALANCE_KEY]
    ):
        if role_to_assign is not None:
            await member.add_roles(role_to_assign)
            print("Assigned role to member")
        else:
            print("Can't find role")
            print(role_mapping["role"])
    else:
        if role_to_assign in member.roles:
            await member.remove_roles(role_to_assign)
            print("Removed role to member")


async def force_update(bot, ctx):
    await bot.get_cog("UpdateTask").force_update(ctx)


async def update_activity(bot_instance, new_activity_type, new_activity_text):
    error = False
    if new_activity_type and new_activity_text:
        if new_activity_type == 'playing':
            activity_type = discord.ActivityType.playing
        elif new_activity_type == 'listening':
            activity_type = discord.ActivityType.listening
        elif new_activity_type == 'competing':
            activity_type = discord.ActivityType.competing
        elif new_activity_type == 'watching':
            activity_type = discord.ActivityType.watching
        else:
            error = True
            return error

        current_activity = running_bots[bot_instance[BOT_ID_KEY]]['activity']
        bot_object = running_bots[bot_instance[BOT_ID_KEY]]['bot']

        try:
            if not current_activity or (current_activity and current_activity.type != new_activity_text) or \
                    (current_activity and repr(current_activity.name) != repr(new_activity_text)):
                # check that current_activity isnt duplicate of new activity
                new_activity = discord.Activity(type=activity_type, name=new_activity_text)
                running_bots[bot_instance[BOT_ID_KEY]]['activity'] = new_activity
                await bot_object.change_presence(status=discord.Status.online, activity=new_activity)
                data.set_activity(bot_instance[GUILD_ID_KEY], new_activity_type, new_activity_text)
        except:
            error = True

    return error


async def update_avatar(bot_instance, new_avatar=None):
    if new_avatar is None:
        new_avatar = default_avatar

    error = False
    # avatar change
    try:
        bot_object = running_bots[bot_instance[BOT_ID_KEY]]['bot']
        await bot_object.user.edit(avatar=new_avatar)
        data.set_bot_avatar(bot_instance[GUILD_ID_KEY], str(bot_object.user.avatar_url))
    except discord.HTTPException:
        # user is editing avatar too many times, set 1h timeout
        timout = round(time.time() + 3600)
        data.set_avatar_timout(bot_instance[GUILD_ID_KEY], timout)
        bot_instance[AVATAR_TIMEOUT_KEY] = timout
    except Exception as e:
        print(e)
        error = True

    return error


class UpdateTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_lock = threading.Lock()

    async def run_old_timers(self):
        print(f'running old timers')
        timers = data.get_all_timers()
        for timer in timers:
            asyncio.create_task(self.run_timer(timer))

    async def run_timer(self, timer):
        now = round(time.time())

        if timer['expires'] > now:
            await asyncio.sleep(int(timer['expires'] - now))

        await self.call_timer_event(timer)

    async def call_timer_event(self, timer):
        timer = data.get_timer(timer['id'])
        if not timer:
            return

        data.delete_timer(timer['id'])
        self.bot.dispatch(f'{timer["event"]}_timer_over', timer)

    async def create_timer(self, **kwargs):
        timer_id = data.add_timer(kwargs)
        kwargs['id'] = timer_id
        asyncio.create_task(self.run_timer(kwargs))

    @commands.Cog.listener()
    async def on_daily_stats_timer_over(self, timer):
        guild_id = timer['guild_id']
        channel_name = timer['extras']['channel_name']
        webhook_url = await get_webhook_url(guild_id, channel_name)

        default_coin = data.get_default_coin(int(guild_id))
        if webhook_url:
            coin_day_stats = data.get_coin_stats_day(default_coin)
            total_stats = rally_api.get_coin_summary(default_coin)
            rewards = rally_api.get_coin_rewards(default_coin)
            coin_image_url = rally_api.get_coin_image_url(default_coin)

            message = {
              "embeds": [
                {
                  "description": f"```xl\n- Total # of coins: {total_stats['totalCoins']}\n\n"
                                 f"- Total # of supporters: {total_stats['totalSupporters']}\n\n"
                                 f"- Total Support Volume: {total_stats['totalSupportVolume']} USD\n\n\n"
                                 f"- Today`s # of purchases: {coin_day_stats[PURCHASES_KEY]}\n\n"
                                 f"- Today`s # of donations: {coin_day_stats[DONATIONS_KEY]}\n\n"
                                 f"- Today`s # of transfers: {coin_day_stats[TRANSFERS_KEY]}\n\n"
                                 f"- Today`s # of conversions: {coin_day_stats[CONVERSIONS_KEY]}\n\n"
                                 f"- Today`s # of redeems: {coin_day_stats[REDEEMS_KEY]}\n\n"
                                 f"- Today`s # of rewards earned: {rewards['last24HourEarned']}\n```",
                  "color": 0xff0000,
                  "author": {
                    "name": f"{default_coin} Daily Stats",
                    "icon_url": coin_image_url
                  },
                  "timestamp": datetime.datetime.now().isoformat()
                }
              ]
            }

            requests.post(webhook_url, json=message)

        # 0 out week stats if day is money
        timezone = int(timer['extras']['timezone'])
        check = 0 if timezone >= 0 else 6
        if datetime.datetime.utcnow().weekday() == check:
            coin_stats_week = {
                COIN_KIND_KEY: default_coin,
                PURCHASES_KEY: 0,
                DONATIONS_KEY: 0,
                TRANSFERS_KEY: 0,
                CONVERSIONS_KEY: 0,
                REDEEMS_KEY: 0
            }
            data.add_coin_stats_week(coin_stats_week)

        # start timer again
        if timer['bot_id'] in running_bots:
            bot_object = running_bots[timer['bot_id']]['bot']
        else:
            bot_object = main_bot

        if not timer['extras']['timezone']:
            timer['extras']['timezone'] = 0

        dt = datetime.datetime.utcnow() + datetime.timedelta(hours=int(timer['extras']['timezone']))
        time_midnight = time.time() + (((24 - dt.hour - 1) * 60 * 60) + ((60 - dt.minute - 1) * 60) + (60 - dt.second))

        # if the timezone is whacky and time_midnight ends up coming up before current time,
        # just add 24h to current time and set that as time_midnight
        if time_midnight < round(time.time()):
            time_midnight = round(time.time()) + (24 * 3600)  # 24h

        await self.create_timer(
            guild_id=guild_id,
            expires=time_midnight,
            event='daily_stats',
            extras=timer['extras'],
            bot_id=bot_object.user.id
        )

    @staticmethod
    async def start_bot_instance(bot_instance):
        from main import bot

        try:
            await bot.start(bot_instance)
        finally:
            if not bot.is_closed():
                await bot.close()

        running_bot_instances.remove(bot_instance[BOT_TOKEN_KEY])

    async def run_bot_instances(self):
        all_bot_instances = data.get_all_bot_instances()
        if all_bot_instances:
            for instance in all_bot_instances:
                running_bot_instances.append(instance[BOT_TOKEN_KEY])
                asyncio.create_task(self.start_bot_instance(instance[BOT_TOKEN_KEY]))

    @commands.Cog.listener()
    async def on_ready(self):
        running_bots[self.bot.user.id] = {
            'bot': self.bot,
            'token': self.bot.http.token,
            'activity': None
        }

        # for instances
        if config.CONFIG.secret_token != self.bot.http.token:
            bot_instance = data.get_bot_instance_token(self.bot.http.token)

            if bot_instance[BOT_ACTIVITY_TEXT_KEY]:
                await update_activity(bot_instance, bot_instance[BOT_ACTIVITY_TYPE_KEY], bot_instance[BOT_ACTIVITY_TEXT_KEY])

            # set bot id
            data.set_bot_id(self.bot.user.id, self.bot.http.token)
            # set bot name
            data.set_bot_name(bot_instance[GUILD_ID_KEY], self.bot.user.name)

        # for the main bot
        if not running_bot_instances:
            global main_bot
            main_bot = self.bot
            asyncio.create_task(self.run_bot_instances())

        print("We have logged in as {0.user}".format(self.bot))
        self.update.start()

        if not default_avatar:
            await set_default_avatar()

        await self.run_old_timers()

    @errors.standard_error_handler
    async def cog_command_error(self, ctx, error):
        # All other Errors not returned come here. And we can just print the default TraceBack.
        print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

    @commands.command(name="update", help="Force an immediate update")
    @validation.owner_or_permissions(administrator=True)
    async def force_update(self, ctx):
        self.update.restart()
        await ctx.send("Updating!")

    @tasks.loop(seconds=UPDATE_WAIT_TIME)
    async def update(self):
        await self.bot.wait_until_ready()
        with self.update_lock:

            print("Updating roles")
            guilds = self.bot.guilds
            guild_count = 0
            member_count = 0
            mapping_count = 0

            for guild in guilds:

                guild_count += 1
                await guild.chunk()

                role_mappings = list(data.get_role_mappings(guild.id))
                channel_mappings = list(data.get_channel_mappings(guild.id))
                mapping_count += len(role_mappings) + len(channel_mappings)

                for member in guild.members:
                    member_count += 1
                    rally_id = data.get_rally_id(member.id)
                    if rally_id:
                        balances = rally_api.get_balances(rally_id)
                        for role_mapping in role_mappings:
                            print(role_mapping)
                            await grant_deny_role_to_member(
                                role_mapping, member, balances
                            )
                        for channel_mapping in channel_mappings:
                            await grant_deny_channel_to_member(
                                channel_mapping, member, balances
                            )

            print(
                "Done! Checked "
                + str(guild_count)
                + " guilds. "
                + str(mapping_count)
                + " mappings. "
                + str(member_count)
                + " members."
            )

    @commands.command(
        name='change_rally_id',
        help="updates your wallet balance / roles immediately"
    )
    @commands.guild_only()
    async def set_rally_id(self, ctx):
        member = ctx.author

        with self.update_lock:
            for guild in self.bot.guilds:
                await guild.chunk()

                if not member in guild.members:
                    continue

                role_mappings = list(data.get_role_mappings(guild.id))
                channel_mappings = list(data.get_channel_mappings(guild.id))

                rally_id = data.get_rally_id(member.id)
                if rally_id:
                    balances = rally_api.get_balances(rally_id)
                    for role_mapping in role_mappings:
                        try:
                            await grant_deny_role_to_member(
                                role_mapping, member, balances
                            )
                        except discord.HTTPException:
                            raise errors.RequestError("network error, try again later")
                        except:
                            # Forbidden, NotFound or Invalid Argument exceptions only called when code
                            # or bot is wrongly synced / setup
                            raise errors.FatalError("bot is setup wrong, call admin")
                    for channel_mapping in channel_mappings:
                        try:
                            await grant_deny_channel_to_member(
                                channel_mapping, member, balances
                            )
                        except discord.HTTPException:
                            raise errors.RequestError("network error, try again later")
                        except:
                            # Forbidden, NotFound or Invalid Argument exceptions only called when code
                            # or bot is wrongly synced / setup
                            raise errors.FatalError("bot is setup wrong, call admin")

            await pretty_print(
                ctx,
                "Command completed successfully!",
                title="Success",
                color=SUCCESS_COLOR,
            )
