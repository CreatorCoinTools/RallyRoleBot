import data

from cogs import update_cog
from fastapi import APIRouter, Depends, HTTPException
from .dependencies import owner_or_admin
from .models import BotActivityMapping
from constants import *

import config
config.parse_args()


router = APIRouter(
    prefix="/mappings/bot_activity",
    tags=["bot_activity"],
    dependencies=[Depends(owner_or_admin)],
    responses={404: {"description": "Not found"}},
)


@router.get("/{guildId}", response_model=BotActivityMapping)
async def read_mapping(guildId: str):
    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        return {}

    activity_text = bot_instance[BOT_ACTIVITY_TEXT_KEY]
    activity_type = bot_instance[BOT_ACTIVITY_TYPE_KEY]

    return {"activity_text": activity_text, "activity_type": activity_type}


@router.post("", response_model=BotActivityMapping)
async def add_mapping(mapping: BotActivityMapping, guildId: str):
    bot_instance = data.get_bot_instance(guildId)

    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot config not found")

    task = {
        'kwargs': {
            'guild_id': int(guildId),
            'bot_id': int(bot_instance[BOT_ID_KEY]),
            'activity_type_str': mapping.activity_type,
            'activity_text': mapping.activity_text
        },
        'function': 'update_activity'
    }
    data.add_task(task)

    return {"success": 1}
