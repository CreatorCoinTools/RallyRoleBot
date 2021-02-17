import sys
import traceback
import threading
import time
import datetime
import discord
import discord.utils
import re

from typing import Optional
from discord.ext import commands
from discord.ext import tasks as discord_tasks
from discord.utils import get
from constants import *
from utils import tasks
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

# default descriptions for every event
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


# sets global default avatar value for use in webhooks
async def set_default_avatar():
    global default_avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(DEFAULT_BOT_AVATAR_URL) as response:
            default_avatar = await response.read()


async def format_alert_message(event: str, payload: dict, instance: dict) -> dict:
    """
    Format alert message for sending to a webhook

    @param event: event type [buy, donate, ...]
    @param payload: payload received
    @param instance: alert instance defined in dashboard
    @return: dict formatted with data for sending to a webhook
    """
    # set values to provided one or to default one
    description = instance['settings']['customMessage'] if instance['settings']['customMessage'] else webhook_message_data[event]['description']
    title = instance['settings']['customTitle'] if instance['settings']['customTitle'] else 'Alert!'
    colour = instance['settings']['customColour'] if instance['settings']['customColour'] else '#ff0000'

    # convert colour to int
    colour = int(colour.replace('#', '0x'), 16)

    # if showUsername is false set username to 'someone'
    if 'showUsername' not in payload['data'] or not payload['data']['showUsername']:
        payload['data']['username'] = 'someone'

    coin_image_url = rally_api.get_coin_image_url(payload['coinKind'])

    # move values from data to the root of payload
    payload.update(payload['data'])

    # add values for extra variables
    if event == 'convert':
        payload['valueInUSD'] = payload['valueInUSCents'] // 100
    elif event == 'redeem':
        payload['estimatedAmountInUSD'] = payload['estimatedAmountInUSCents'] // 100
    else:
        payload['costInUSD'] = payload['costInUSCents'] // 100

    # format provided message variable by variable, if variable doesnt exist in payload, continue on
    variables = re.findall(r'({\w+})', description)
    for var in variables:
        try:
            description = description.replace(var, var.format(**payload))
        except:
            continue

    # message in proper format for sending to webhook
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


async def get_webhook_url(guild_id: str, channel_name: str) -> Optional[str]:
    """
    Gets or creates webhook url.

    @param guild_id: guild id of webhook
    @param channel_name: channel name of webhook
    @return: webhook url or None if error occurred
    """
    # get bot object
    bot_instance = data.get_bot_instance(guild_id)
    bot_object = main_bot if not bot_instance else running_bots[bot_instance[BOT_ID_KEY]]['bot']

    # wait until bot is ready, just in case
    await bot_object.wait_until_ready()

    # get guild object, fetch if needed, if bot cant access guild, return
    guild_object = bot_object.get_guild(int(guild_id))
    if not guild_object:
        guild_object = await bot_object.fetch_guild(guild_id)
        if not guild_object:
            return

    # get channel
    channel_object = discord.utils.get(guild_object.channels, name=channel_name)
    if not channel_object:
        return

    # get webhook
    webhook = data.get_webhook(guild_id, channel_object.id)
    if not webhook:
        # if webhook doesnt exist, create new one and add it to the webhooks database
        try:
            webhook_object = await channel_object.create_webhook(name='RallyBotAlerts', avatar=default_avatar)
            data.add_webhook(guild_id, channel_object.id, webhook_object.url, webhook_object.id, webhook_object.token)
            webhook_url = webhook_object.url
        except:
            return
    else:
        webhook_url = webhook[WEBHOOK_URI]

    return webhook_url


async def process_payload(payload: dict, failed: bool = False) -> None:
    """
    Process payload received by webhook endpoint.

    @param payload: received payload
    @param failed: True if failed to send message to webhook, False on first attempt
    @return: None
    """
    # add to stats
    coin_kind = payload['coinKind']
    event = payload['event'].lower()
    data.add_event(event, coin_kind)

    # find guilds that have coin_kind as default coin and loop through them
    guilds = data.get_guilds_by_coin(coin_kind)
    for guild in guilds:
        guild_id = guild[GUILD_ID_KEY]
        # get alert settings
        alerts_settings = data.get_alerts_settings(guild_id)
        if not alerts_settings:
            continue

        settings_data = alerts_settings[ALERTS_SETTINGS_KEY]

        # if event isn't enabled, continue
        if not settings_data[event]['enabled']:
            continue

        # go through each instance
        for instance in settings_data[event]['instances']:
            # if channel is empty, continue
            if not instance['channel']:
                continue

            # set default value for minamount if needed
            if 'minamount' not in instance['settings'] or not instance['settings']['minamount']:
                instance['settings']['minamount'] = 0.0

            # set default value for maxamount if needed
            if 'maxamount' not in instance['settings'] or not instance['settings']['maxamount'] or instance['settings']['maxamount'] == 0:
                instance['settings']['maxamount'] = sys.maxsize

            # get coin amount from variable according to event (convert event is special)
            coin_amount = payload['data']['amountOfCoin'] if payload['event'] != 'convert' else payload['data']['fromAmount']

            # check if amount is between min and max limits
            if float(instance['settings']['minamount']) <= float(coin_amount) <= float(instance['settings']['maxamount']):
                # get webhooks, return if cant get one
                webhook_url = await get_webhook_url(guild_id, instance['channel'])
                if not webhook_url:
                    continue

                # get message for event and send it
                message = await format_alert_message(event, payload, instance)
                request = requests.post(webhook_url, json=message)

                # request failed, delete webhook db entry and try again, if it fails a second time dont try again
                if request.status_code not in [200, 204] and not failed:
                    data.delete_webhook(webhook_url)
                    return await process_payload(payload, True)


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


def get_day_stats(coin: str) -> dict:
    """
    Return dict of stats of events in the past 24h

    @param coin: con symbol e.g. "STANZ"
    @return: stats dict
    """
    return {
        'buy': data.get_day_events('buy', coin),
        'donate': data.get_day_events('donate', coin),
        'transfer': data.get_day_events('transfer', coin),
        'convert': data.get_day_events('convert', coin),
        'redeem': data.get_day_events('redeem', coin),
    }


def get_week_stats(coin: str) -> dict:
    """
    Return dict of stats of events in the past week

    @param coin: con symbol e.g. "STANZ"
    @return: stats dict
    """
    return {
        'buy': data.get_week_events('buy', coin),
        'donate': data.get_week_events('donate', coin),
        'transfer': data.get_week_events('transfer', coin),
        'convert': data.get_week_events('convert', coin),
        'redeem': data.get_week_events('redeem', coin),
    }


class UpdateTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_lock = threading.Lock()
        self.task_run_lock = threading.Lock()

    async def run_old_timers(self):
        """Starts up old timers that werent finished when the bot was closed."""

        print(f'running old timers')
        # get all the timers attached to a self.bot and run them
        timers = data.get_all_timers(self.bot.user.id)
        for timer in timers:
            asyncio.create_task(self.run_timer(timer))

    async def run_timer(self, timer: dict) -> None:
        """
        Run a timer.

        @param timer: Timer object dict
        """
        now = round(time.time())

        # if timer hasn't expired yet, wait for needed amount
        if timer['expires'] > now:
            await asyncio.sleep(int(timer['expires'] - now))

        # call timer event when timer is finished
        await self.call_timer_event(timer)

    async def call_timer_event(self, timer):
        """
        Call provided timer event.
    
        @param timer: Timer object dict
        """
        # check if timer has been deleted, if it hasn't call provided event
        timer = data.get_timer(timer['id'])
        if not timer:
            return

        # delete timer
        data.delete_timer(timer['id'])
        
        # dispatch event
        self.bot.dispatch(f'{timer["event"]}_timer_over', timer)

    async def create_timer(self, *, guild_id: int, expires: int, event: str, extras: dict, bot_id: int) -> None:
        """
        Create a new timer to run in the background, slowly ticking away, until its time to strike.
    
        @param guild_id: guild id
        @param expires: time when timer expires (epoch time)
        @param event: event to call when timer is over "on_{event}_timer_over"
        @param extras: extra values
        @param bot_id: bot id
        """
        
        timer = {
            'guild_id': guild_id,
            'expires': expires,
            'event': event,
            'extras': extras,
            'bot_id': bot_id
        }
        
        timer_id = data.add_timer(timer)
        timer['id'] = timer_id
        asyncio.create_task(self.run_timer(timer))

    @commands.Cog.listener()
    async def on_daily_stats_timer_over(self, timer: dict) -> None:
        """
        Function called when daily_stats timer is over.
        
        @param timer: timer object dict
        """
        # delete week old stats
        data.delete_week_old_events()
        
        # gather some needed data
        guild_id = timer['guild_id']
        channel_name = timer['extras']['channel_name']
        webhook_url = await get_webhook_url(guild_id, channel_name)
        default_coin = data.get_default_coin(int(guild_id))
        
        # check if there is a webhook url to send stats to
        if webhook_url:
            # gather stats data
            coin_day_stats = get_day_stats(default_coin)
            total_stats = rally_api.get_coin_summary(default_coin)
            rewards = rally_api.get_coin_rewards(default_coin)
            
            # create stats message
            coin_image_url = rally_api.get_coin_image_url(default_coin)
            message = {
                "embeds": [
                    {
                        "description": f"```xl\n- Total coins: {total_stats['totalCoins']}\n\n"
                                       f"- Total supporters: {total_stats['totalSupporters']}\n\n"
                                       f"- Total Support Volume: {total_stats['totalSupportVolume']} USD\n\n\n"
                                       f"- Today`s purchases: {len(coin_day_stats['buy'])}\n\n"
                                       f"- Today`s donations: {len(coin_day_stats['donate'])}\n\n"
                                       f"- Today`s transfers: {len(coin_day_stats['transfer'])}\n\n"
                                       f"- Today`s conversions: {len(coin_day_stats['convert'])}\n\n"
                                       f"- Today`s redeems: {len(coin_day_stats['redeem'])}\n\n"
                                       f"- Today`s rewards earned: {rewards['last24HourEarned']}\n```",
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

        # start timer again
        if timer['bot_id'] in running_bots:
            bot_object = running_bots[timer['bot_id']]['bot']
        else:
            bot_object = main_bot

        if not timer['extras']['timezone']:
            timer['extras']['timezone'] = 0

        # get time until next midnight
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
    async def start_bot_instance(token: str) -> None:
        """
        Stats a bot instance.

        @param token: Bot token
        """
        # get initiated bot class from main
        from main import bot

        try:
            # start up bot instance
            await bot.start(token)
        finally:
            # close if needed
            if not bot.is_closed():
                await bot.close()

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

            # set presence
            if bot_instance[BOT_ACTIVITY_TEXT_KEY]:
                await self.bot.change_presence(status=discord.Status.online, activity=running_bots[self.bot.user.id]['activity'])

            # set bot id
            data.set_bot_id(self.bot.user.id, self.bot.http.token)
            # set bot name
            data.set_bot_name(bot_instance[GUILD_ID_KEY], self.bot.user.name)

        # for the main bot
        if not running_bot_instances:
            global main_bot
            main_bot = self.bot
            asyncio.create_task(self.run_bot_instances())
            self.run_tasks.start()

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

    @discord_tasks.loop(seconds=5)
    async def run_tasks(self):
        await self.bot.wait_until_ready()
        with self.task_run_lock:
            all_tasks = data.get_tasks()
            for task in all_tasks:
                try:
                    # get function object and kwargs
                    task_function = getattr(tasks, task['function'])
                    kwargs = task['kwargs']

                    # call function
                    asyncio.create_task(task_function(**kwargs))

                    # delete task
                    data.delete_task(task['id'])
                except Exception as e:
                    print(e)

    @discord_tasks.loop(seconds=UPDATE_WAIT_TIME)
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
