import data
import asyncio

from cogs import update_cog
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import owner_or_admin
from .models import BotInstanceMapping
from constants import *

import config
config.parse_args()

router = APIRouter(
    prefix="/mappings/bot_instance",
    tags=["bot_instance"],
    dependencies=[Depends(owner_or_admin)],
    responses={404: {"description": "Not found"}},
)


@router.get("/{guildId}")
async def read_mapping(guildId: str):
    bot_instance = data.get_bot_instance(int(guildId))

    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot config not found")

    return {
        "bot_instance": bot_instance[BOT_TOKEN_KEY],
        "bot_avatar": bot_instance[BOT_AVATAR_KEY],
        "bot_name": bot_instance[BOT_NAME_KEY],
        'avatar_timout': bot_instance[AVATAR_TIMEOUT_KEY],
        'name_timeout': bot_instance[NAME_TIMEOUT_KEY],
        'activity_type': bot_instance[BOT_ACTIVITY_TYPE_KEY],
        'activity_text': bot_instance[BOT_ACTIVITY_TEXT_KEY],
        'bot_id': bot_instance[BOT_ID_KEY],
        "guildId": guildId
    }


@router.post("/", response_model=BotInstanceMapping)
async def add_mapping(mapping: BotInstanceMapping, guildId: str):
    if mapping.bot_instance is not None:
        data.add_bot_instance(guildId, mapping.bot_instance)

        task = {
            'kwargs': {
                'bot_token': mapping.bot_instance
            },
            'function': 'start_new_bot_instance'
        }
        data.add_task(task)

    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot config not found")

    return {
        "bot_instance": bot_instance[BOT_TOKEN_KEY],
        "bot_avatar": bot_instance[BOT_AVATAR_KEY],
        "bot_name": bot_instance[BOT_NAME_KEY],
        'avatar_timout': bot_instance[AVATAR_TIMEOUT_KEY],
        'name_timeout': bot_instance[NAME_TIMEOUT_KEY],
        'activity_type': bot_instance[BOT_ACTIVITY_TYPE_KEY],
        'activity_text': bot_instance[BOT_ACTIVITY_TEXT_KEY],
        'bot_id': bot_instance[BOT_ID_KEY],
        "guildId": guildId
    }


@router.delete("/")
async def delete_mapping(guildId: str):
    bot_instance = data.get_bot_instance(guildId)

    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot config not found")

    if guildId is not None:
        task = {
            'kwargs': {
                'guild_id': int(guildId)
            },
            'function': 'delete_bot_instance'
        }
        data.add_task(task)

