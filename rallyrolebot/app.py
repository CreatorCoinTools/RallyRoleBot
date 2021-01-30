import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import (
    channel_mappings,
    role_mappings,
    prefix_mappings,
    coin_mappings,
    bot_config_mappings,
    commands,
)
import config

from constants import *


app = FastAPI(
    title="Rally Discord Bot API",
    description="API for communicating with the Rally Role Bot for Discord",
    version="1.0.0",
    openapi_tags=API_TAGS_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channel_mappings.router)
app.include_router(role_mappings.router)
app.include_router(prefix_mappings.router)
app.include_router(coin_mappings.router)
app.include_router(bot_config_mappings.router)
app.include_router(commands.router)


@app.get("/")
async def root():
    return {
        "bot": "Welcome to rally discord bot api",
        "docs": "api documentation at /docs or /redoc",
    }


if __name__ == "__main__":
    config.parse_args()
    uvicorn.run("app:app", host=config.CONFIG.host, port=int(config.CONFIG.port))
