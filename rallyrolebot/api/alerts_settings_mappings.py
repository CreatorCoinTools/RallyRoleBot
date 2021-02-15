import data
import json
import datetime
import time

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
        data.delete_timers(str(guildId))
        for i, instance in enumerate(output_data[ALERTS_SETTINGS_KEY]['daily_stats']['instances']):
            bot_instance = data.get_bot_instance(guildId)
            if not bot_instance:
                bot_object = update_cog.main_bot
            else:
                bot_object = update_cog.running_bots[bot_instance[BOT_ID_KEY]]['bot']

            if not instance['settings']['timezone']:
                instance['settings']['timezone'] = '0'

            try:
                dt = datetime.datetime.utcnow() + datetime.timedelta(hours=int(instance['settings']['timezone']))
            except:
                continue

            time_midnight = time.time() + 5

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
