import data

from fastapi import APIRouter, Depends, HTTPException
from .dependencies import bot_owner
from .models import BotGlobalsMapping


router = APIRouter(
    prefix="/mappings/bot_globals",
    tags=["bot_globals"],
    dependencies=[Depends(bot_owner)],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=BotGlobalsMapping)
async def read_mapping():
    avatar_url = data.get_bot_avatar_url()
    avatar_hash = data.get_bot_avatar_hash()
    if not avatar_url:
        raise HTTPException(status_code=404, detail="Bot config not found")
    return {"bot_avatar_url": avatar_url, "bot_avatar_hash": avatar_hash}


@router.post("/", response_model=BotGlobalsMapping)
async def add_mapping(mapping: BotGlobalsMapping):
    if mapping.bot_avatar_url is not None:
        data.set_bot_avatar(mapping.bot_avatar_url)
        data.set_bot_avatar_hash("")
    avatar_url = data.get_bot_avatar_url()
    avatar_hash = data.get_bot_avatar_hash()
    if not avatar_url:
        raise HTTPException(status_code=404, detail="Bot config not found")
    return {"bot_avatar_url": avatar_url, "bot_avatar_hash": avatar_hash}