import data
import json

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
            task = {
                'kwargs': {
                    'guild_id': int(guildId),
                    'timezone': instance['settings']['timezone'] if 'timezone' in instance['settings'] else '0',
                    'channel': instance['channel'],
                },
                'function': 'start_daily_stats_timers'
            }
            data.add_task(task)

    return {
        GUILD_ID_KEY: guildId,
        ALERTS_SETTINGS_KEY: output_data[ALERTS_SETTINGS_KEY]
    }
