import data
import re
import base64
import time
import os

from fastapi import APIRouter, Depends, HTTPException
from .dependencies import owner_or_admin
from .models import BotAvatarMapping
from constants import *

import config
config.parse_args()


router = APIRouter(
    prefix="/mappings/bot_avatar",
    tags=["bot_avatar"],
    dependencies=[Depends(owner_or_admin)],
    responses={404: {"description": "Not found"}},
)


@router.get("/{guildId}", response_model=BotAvatarMapping)
async def read_mapping(guildId: str):
    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        return {"bot_avatar": DEFAULT_BOT_AVATAR_URL, "guildId": guildId}

    avatar = bot_instance[BOT_AVATAR_KEY]

    return {"bot_avatar": avatar, "avatar_timeout": int(bool(bot_instance[AVATAR_TIMEOUT_KEY])), "guildId": guildId}


@router.post("", response_model=BotAvatarMapping)
async def add_mapping(mapping: BotAvatarMapping, guildId: str):
    bot_instance = data.get_bot_instance(guildId)
    if not bot_instance:
        raise HTTPException(status_code=404, detail="Bot config not found")

    # avatar timout
    if bot_instance[AVATAR_TIMEOUT_KEY] and int(bot_instance[AVATAR_TIMEOUT_KEY]) <= time.time():
        data.set_avatar_timout(bot_instance[GUILD_ID_KEY], 0)
        bot_instance[AVATAR_TIMEOUT_KEY] = 0

    if not bot_instance[AVATAR_TIMEOUT_KEY]:
        # read new avatar data and decode the base64 form
        ext, image_data = re.findall('/(.*);base64,(.*)', mapping.bot_avatar)[0]
        new_avatar = base64.decodebytes(image_data.encode('utf-8'))

        # get path to tmp folder where avatars will be stored temporarily
        tmp_folder = os.path.abspath('tmp/')
        if not os.path.exists(tmp_folder):
            os.mkdir(tmp_folder)

        # get path to new file and write bytes to it
        file_path = os.path.join(os.path.abspath('tmp/'), f'{guildId}_tmp_bot_avatar.{ext}')
        with open(file_path, 'wb+') as file:
            file.write(new_avatar)

        task = {
            'kwargs': {
                'guild_id': int(guildId),
                'bot_id': int(bot_instance[BOT_ID_KEY]),
                'new_avatar_path': file_path,
            },
            'function': 'update_avatar'
        }
        data.add_task(task)

    return {"bot_avatar": mapping.bot_avatar, 'guildId': guildId, 'avatar_timeout': int(bool(bot_instance[AVATAR_TIMEOUT_KEY]))}
