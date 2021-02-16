import data
import json
import datetime
import time
import discord

from cogs import update_cog
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import owner_or_admin
from .models import AlertsSettings
from constants import *

import config
config.parse_args()

router = APIRouter(
    prefix="/mappings/alerts_settings",
    tags=["alerts_settings"],
    dependencies=[Depends(owner_or_admin)],
)


@router.get("/{guildId}", response_model=AlertsSettings)
async def read_mappings(guildId: str):
    output_data = data.get_alerts_settings(guildId)
    if not output_data:
        return {GUILD_ID_KEY: guildId}

    return {
        GUILD_ID_KEY: guildId,
        ALERTS_SETTINGS_KEY: output_data[ALERTS_SETTINGS_KEY]
    }


@router.post("", response_model=AlertsSettings)
async def add_mappings(mapping: AlertsSettings, guildId: str):
    if mapping.settings:
        data.set_alerts_settings(guildId, json.dumps(mapping.settings))

    output_data = data.get_alerts_settings(guildId)
    if not output_data:
        raise HTTPException(status_code=500, detail="Failed to set alerts settings")

    # add timer if daily stats is enabled
    if output_data[ALERTS_SETTINGS_KEY]['daily_stats']['enabled'] and output_data[ALERTS_SETTINGS_KEY]['daily_stats']['instances']:
        # delete old timers
        data.delete_timers(str(guildId))

        # loop through each instance of the daily_stats
        for i, instance in enumerate(output_data[ALERTS_SETTINGS_KEY]['daily_stats']['instances']):

            # get bot instance, if it isn't set, assume the bot being used is the main one
            bot_instance = data.get_bot_instance(guildId)
            if not bot_instance:
                bot_object = update_cog.main_bot
            else:
                bot_object = update_cog.running_bots[bot_instance[BOT_ID_KEY]]['bot']

            try:
                # get guild to see if bot has permission to manage webhooks
                guild_object = bot_object.get_guild(int(guildId))
                if not guild_object:
                    guild_object = await bot_object.fetch_guild(guildId)
                    if not guild_object:
                        return

                has_permission = guild_object.me.guild_permissions.is_superset(discord.Permissions(536870912))
                if not has_permission:
                    return {'error': "Bot is missing Manage Webhooks permissions"}
            except:
                # just in case no guild can be gotten
                return {'error': "Invalid Guild"}

            # set timezone to a default 0 if needed
            if 'timezone' not in instance['settings'] or not instance['settings']['timezone']:
                instance['settings']['timezone'] = '0'

            try:
                # get time relative to user timezone
                dt = datetime.datetime.utcnow() + datetime.timedelta(hours=int(instance['settings']['timezone']))
            except:
                continue

            # get time until midnight
            time_midnight = time.time() + (((24 - dt.hour - 1) * 60 * 60) + ((60 - dt.minute - 1) * 60) + (60 - dt.second))

            # start new timer for instance
            await bot_object.get_cog("UpdateTask").create_timer(
                guild_id=guildId,
                expires=time_midnight,
                event='daily_stats',
                extras={
                    'channel_name':  instance['channel'],
                    'timezone': instance['settings']['timezone']
                },
                bot_id=bot_object.user.id,
            )

    return {
        GUILD_ID_KEY: guildId,
        ALERTS_SETTINGS_KEY: output_data[ALERTS_SETTINGS_KEY]
    }
