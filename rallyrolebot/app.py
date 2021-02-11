import uvicorn

import logging
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.tasks import repeat_every
from api import (
    channel_mappings,
    role_mappings,
    prefix_mappings,
    coin_mappings,
    commands,
    price_data,
)

import config
import data
import rally_api

from constants import *

config.parse_args()
logger = logging.getLogger(__name__)
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
app.include_router(commands.router)
app.include_router(price_data.router)


@app.get("/")
async def root():
    return {
        "bot": "Welcome to rally discord bot api",
        "docs": "api documentation at /docs or /redoc",
    }


@app.on_event("startup")
@repeat_every(seconds=60 * 60, logger=logger)
def get_prices():
    coins = rally_api.get_creator_coins()
    for coin in coins:
        try:
            symbol = coin["coinSymbol"]
            price = rally_api.get_current_price(symbol)
            data.add_coin_price(str(price["priceInUSD"]), symbol)
        except:
            print(f"Failed to get price for {coin['coinSymbol']}")
    count = data.price_count()
    max = int(config.CONFIG.cache_max)
    print(f"Price cache updated, Count: {count}, Max: {max}")
    if count > max:
        data.clean_price_cache(count - max)
        print(f"{count - max} cache entries removed")


if __name__ == "__main__":
    uvicorn.run("app:app", host=config.CONFIG.host, port=int(config.CONFIG.port))
