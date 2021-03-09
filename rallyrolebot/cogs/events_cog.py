import data
import rally_api
import datetime
import requests
import main
import time
import config
import discord

from cogs.update_cog import default_avatar, set_default_avatar
from constants import *
from utils import alerts
from discord.ext import commands
from main import RallyRoleBot


class Events(commands.Cog):
    def __init__(self, bot: RallyRoleBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_daily_stats_timer_over(self, timer: dict) -> None:
        """
        Function called when daily_stats timer is over.

        @param timer: timer object dict
        """
        # delete week old stats
        data.delete_week_old_events()

        # gather some needed data
        guild_id = timer['guildId']
        channel_name = timer['extras']['channel_name']
        webhook_url = await alerts.get_webhook_url(guild_id, channel_name)
        default_coin = data.get_default_coin(int(guild_id))

        # check if there is a webhook url to send stats to
        if webhook_url:
            # gather stats data
            coin_day_stats = alerts.get_day_stats(default_coin)
            total_stats = rally_api.get_coin_summary(default_coin)
            rewards = rally_api.get_coin_rewards(default_coin)

            # create stats message
            coin_image_url = rally_api.get_coin_image_url(default_coin)
            message = {
                "embeds": [
                    {
                        "description": f"```xl\n- Total coins: {round(total_stats['totalCoins'], 3)}\n\n"
                                       f"- Total supporters: {round(total_stats['totalSupporters'], 3)}\n\n"
                                       f"- Total support volume: {round(total_stats['totalSupportVolume'], 3)} USD\n\n\n"
                                       f"- Today`s purchases: {len(coin_day_stats['buy'])}\n\n"
                                       f"- Today`s donations: {len(coin_day_stats['donate'])}\n\n"
                                       f"- Today`s transfers: {len(coin_day_stats['transfer'])}\n\n"
                                       f"- Today`s conversions: {len(coin_day_stats['convert'])}\n\n"
                                       f"- Today`s redeems: {len(coin_day_stats['redeem'])}\n\n"
                                       f"- Today`s rewards earned: {round(rewards['last24HourEarned'], 3)}\n```",
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
        if timer['bot_id'] in main.running_bots:
            bot_object = main.running_bots[timer['bot_id']]['bot']
        else:
            bot_object = main.main_bot

        if not timer['extras']['timezone']:
            timer['extras']['timezone'] = 0

        # get time until next midnight
        dt = datetime.datetime.utcnow() + datetime.timedelta(hours=int(timer['extras']['timezone']))
        time_midnight = time.time() + (((24 - dt.hour - 1) * 60 * 60) + ((60 - dt.minute - 1) * 60) + (60 - dt.second))

        # if the timezone is whacky and time_midnight ends up coming up before current time,
        # just add 24h to current time and set that as time_midnight
        if time_midnight < round(time.time()):
            time_midnight = round(time.time()) + (24 * 3600)  # 24h

        self.bot.timers.create(
            guild_id=guild_id,
            expires=time_midnight,
            event='daily_stats',
            extras=timer['extras'],
            bot_id=bot_object.user.id
        )

    @commands.Cog.listener()
    async def on_ready(self):
        main.running_bots[self.bot.user.id] = {
            'bot': self.bot,
            'token': self.bot.http.token,
            'activity': None
        }

        update_cog_object = self.bot.get_cog('UpdateTask')

        # for instances
        if config.CONFIG.secret_token != self.bot.http.token:
            bot_instance = data.get_bot_instance_token(self.bot.http.token)

            # set presence
            if bot_instance[BOT_ACTIVITY_TEXT_KEY]:
                await self.bot.change_presence(status=discord.Status.online, activity=main.running_bots[self.bot.user.id]['activity'])

            # set bot id
            data.set_bot_id(self.bot.user.id, self.bot.http.token)
            # set bot name
            data.set_bot_name(bot_instance[GUILD_ID_KEY], self.bot.user.name)

        # for the main bot
        else:
            main.main_bot = self.bot
            await self.bot.run_bot_instances()
            update_cog_object.run_tasks.start()

        print("We have logged in as {0.user}".format(self.bot))
        update_cog_object.update.start()

        if not default_avatar:
            await set_default_avatar()

        self.bot.timers.run_old()


def setup(bot: RallyRoleBot):
    bot.add_cog(Events(bot))
