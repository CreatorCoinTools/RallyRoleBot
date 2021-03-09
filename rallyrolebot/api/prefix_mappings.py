import data

from fastapi import APIRouter, Depends, HTTPException
from .dependencies import owner_or_admin
from .models import PrefixMapping

import config
config.parse_args()


router = APIRouter(
    prefix="/mappings/prefix",
    tags=["prefix"],
    dependencies=[Depends(owner_or_admin)],
    responses={404: {"description": "Not found"}},
)


@router.get("/{guildId}", response_model=PrefixMapping)
async def read_mapping(guildId: str):
    prefix = data.get_prefix(guildId)
    if not prefix:
        raise HTTPException(status_code=404, detail="Prefix not found")
    return {"guildId": guildId, "prefix": prefix}


@router.post("", response_model=PrefixMapping)
async def add_mapping(mapping: PrefixMapping, guildId: str):
    data.add_prefix_mapping(guildId, mapping.prefix)
    prefix = data.get_prefix(guildId)
    if not prefix:
        raise HTTPException(status_code=404, detail="Prefix not found")
    return {"guildId": guildId, "prefix": prefix}