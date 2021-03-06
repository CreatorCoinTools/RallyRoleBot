from cogs import update_cog
from fastapi import APIRouter, Request

import config
config.parse_args()

router = APIRouter(
    prefix="/mappings/webhooks",
    tags=["webhooks"],
)


@router.post("/{event}")
async def add_mappings(request: Request):
    payload = await request.json()
    return await update_cog.process_payload(payload)
