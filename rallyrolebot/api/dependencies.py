import data
import requests
import json

from fastapi import Header, HTTPException

from rally_api import return_req_error
from constants import *


def get_user(authorization):
    url = DISCORD_API_URL + "/users/@me"
    headers = {"authorization": authorization}
    result = requests.get(url, headers=headers)
    if result.status_code != 200:
        return_req_error(url, result)
        return None
    return result.json()


def owner_or_admin_guilds(authorization):
    user_id = data.get_user_id(authorization)
    if user_id:
        return json.loads(data.get_user_guilds(user_id))

    user = get_user(authorization)
    url = DISCORD_API_URL + "/users/@me/guilds"
    headers = {"authorization": authorization}
    result = requests.get(url, headers=headers)
    if result.status_code != 200 or not user:
        return_req_error(url, result)
        return None

    guilds = [
        guild["id"]
        for guild in result.json()
        if guild["owner"] or (guild["permissions"] & 0x8) == 0x8
    ]
    data.add_user(
        user["id"], user["username"], user["discriminator"], json.dumps(guilds)
    )
    data.add_user_token(authorization, user["id"])

    return guilds


async def owner_or_admin(guildId: str, authorization: str = Header(...)):
    guilds = owner_or_admin_guilds(authorization)
    if not guilds or guildId not in guilds:
        raise HTTPException(status_code=400, detail="you cannot access this record")
