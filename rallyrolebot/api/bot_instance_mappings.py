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

    bot_object = update_cog.running_bots[bot_instance[BOT_ID_KEY]]['bot']
    if bot_object:
        bot_avatar_url = str(bot_object.user.avatar_url)
        bot_name = str(bot_object.user.name)
        if bot_avatar_url != bot_instance[BOT_AVATAR_KEY]:
            data.set_bot_avatar(guildId, bot_avatar_url)
            bot_instance[BOT_AVATAR_KEY] = bot_avatar_url

        if bot_name != bot_instance[BOT_NAME_KEY]:
            data.set_bot_avatar(guildId, bot_name)
            bot_instance[BOT_NAME_KEY] = bot_name

        # bot isnt running, start it back up
        if bot_instance[BOT_TOKEN_KEY] not in update_cog.running_bot_instances:
            update_cog.running_bot_instances.append(bot_instance[BOT_TOKEN_KEY])
            asyncio.create_task(update_cog.UpdateTask.start_bot_instance(bot_instance[BOT_TOKEN_KEY]))

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

        update_cog.running_bot_instances.append(mapping.bot_instance)
        asyncio.create_task(update_cog.UpdateTask.start_bot_instance(mapping.bot_instance))

    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot config not found")

    # set default avatar
    await update_cog.update_avatar(bot_instance)

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
    old_bot_instance = data.get_bot_instance(guildId)

    if guildId is not None:
        data.remove_bot_instance(guildId)

    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        try:
            update_cog.running_bot_instances.remove(old_bot_instance[BOT_TOKEN_KEY])
            to_be_removed = [b for b in update_cog.running_bots if update_cog.running_bots[b]['token'] == old_bot_instance[BOT_TOKEN_KEY]]
            if to_be_removed:
                await update_cog.running_bots[to_be_removed[0]]['bot'].close()
                del update_cog.running_bots[to_be_removed[0]]
        except:
            raise HTTPException(status_code=500, detail="Error stopping bot")

        return {"deleted": True}

    raise HTTPException(status_code=404, detail="Bot config not found")
