import data

from fastapi import APIRouter, Depends, HTTPException
from .dependencies import owner_or_admin
from .models import BotConfigMapping


router = APIRouter(
    prefix="/mappings/bot_config",
    tags=["bot_config"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get("/{guildId}", response_model=BotConfigMapping)
async def read_mapping(guildId: str):
    name = data.get_bot_name(guildId)
    if not name:
        raise HTTPException(status_code=404, detail="Bot config not found")
    return {"guildId": guildId, "bot_name": name}


@router.post("/{guildId}", response_model=BotConfigMapping)
async def add_mapping(mapping: BotConfigMapping, guildId: str):
    if mapping.bot_name is not None:
      data.set_bot_name(guildId, mapping.bot_name)
    name = data.get_bot_name(guildId)
    if not name:
        raise HTTPException(status_code=404, detail="Bot config not found")
    return {"guildId": guildId, "bot_name": name}