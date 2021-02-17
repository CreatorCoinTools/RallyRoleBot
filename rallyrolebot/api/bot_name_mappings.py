import data
import discord
import time

from cogs import update_cog
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import owner_or_admin
from .models import BotNameMapping
from constants import *

import config
config.parse_args()

router = APIRouter(
    prefix="/mappings/bot_name",
    tags=["bot_name"],
    dependencies=[Depends(owner_or_admin)],
    responses={404: {"description": "Not found"}},
)


@router.get("/{guildId}", response_model=BotNameMapping)
async def read_mapping(guildId: str):
    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        return {"guildId": guildId, "bot_name": "rallybot"}

    return {"guildId": guildId, "bot_name": bot_instance[BOT_NAME_KEY], 'name_timeout': int(bool(bot_instance[NAME_TIMEOUT_KEY]))}


@router.post("/", response_model=BotNameMapping)
async def add_mapping(mapping: BotNameMapping, guildId: str):
    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot config not found")

    # name timout
    if bot_instance[NAME_TIMEOUT_KEY] and int(bot_instance[NAME_TIMEOUT_KEY]) <= time.time():
        data.set_name_timeout(bot_instance[GUILD_ID_KEY], 0)
        bot_instance[NAME_TIMEOUT_KEY] = 0

    if mapping.bot_name and not bot_instance[NAME_TIMEOUT_KEY]:
        task = {
            'kwargs': {
                'guild_id': int(guildId),
                'bot_id': int(bot_instance[BOT_ID_KEY]),
                'new_name': mapping.bot_name,
            },
            'function': 'update_name'
        }
        data.add_task(task)

    return {"guildId": guildId, "bot_name": mapping.bot_name, 'name_timeout': int(bool(bot_instance[NAME_TIMEOUT_KEY]))}
