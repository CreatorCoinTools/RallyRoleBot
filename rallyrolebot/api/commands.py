import data

from typing import List
from fastapi import APIRouter
from .models import Command

import config
config.parse_args()

router = APIRouter()


@router.get("/commands", tags=["commands"], response_model=List[Command])
async def read_commands():
    return [command for command in data.get_all_commands()]
