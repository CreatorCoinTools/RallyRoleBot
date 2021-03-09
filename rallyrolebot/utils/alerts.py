import rally_api
import re
import data
import main
import discord
import sys
import requests

from cogs.update_cog import default_avatar
from constants import *
from typing import Optional

# default descriptions for every event
webhook_message_data = {
    'buy': {
        "description": "**{data[username]}** has purchased **{data[amountOfCoin]}** coins of **{coinKind}!**",
    },
    'donate': {
        "description": "**{data[fromUsername]}** has donated **{data[amountOfCoin]}** coins of **{coinKind}!**",
    },
    'transfer': {
        "description": "**{data[fromUsername]}** has transferred **{data[amountOfCoin]}** coins of **{coinKind}!**",
    },
    'convert': {
        "description": "**{data[username]}** has converted **{data[fromAmount]}** coins of **{data[fromCoinKind]}** to **{data[toAmount]}** coins of **{data[toCoinKind]}!**",
    },
    'redeem': {
        "description": "**{data[username]}** has redeemed **{data[amountOfCoin]}** coins of **{coinKind}!**",
    }
}


async def format_alert_message(event: str, payload: dict, instance: dict) -> dict:
    """
    Format alert message for sending to a webhook

    @param event: event type [buy, donate, ...]
    @param payload: payload received
    @param instance: alert instance defined in dashboard
    @return: dict formatted with data for sending to a webhook
    """
    # set values to provided one or to default one
    description = instance['settings']['customMessage'] if instance['settings']['customMessage'] else webhook_message_data[event]['description']
    title = instance['settings']['customTitle'] if instance['settings']['customTitle'] else 'Alert!'
    colour = instance['settings']['customColour'] if instance['settings']['customColour'] else '#ff0000'

    # convert colour to int
    colour = int(colour.replace('#', '0x'), 16)

    # if showUsername is false set username to 'someone'
    if 'showUsername' not in payload['data'] or not payload['data']['showUsername']:
        payload['data']['username'] = 'someone'

    coin_image_url = rally_api.get_coin_image_url(payload['coinKind'])

    # move values from data to the root of payload
    payload.update(payload['data'])

    # add values for extra variables
    if event == 'convert':
        payload['valueInUSD'] = payload['valueInUSCents'] // 100
    elif event == 'redeem':
        payload['estimatedAmountInUSD'] = payload['estimatedAmountInUSCents'] // 100
    else:
        payload['costInUSD'] = payload['costInUSCents'] // 100

    # format provided message variable by variable, if variable doesnt exist in payload, continue on
    variables = re.findall(r'({\w+})', description)
    for var in variables:
        try:
            description = description.replace(var, var.format(**payload))
        except:
            continue

    # message in proper format for sending to webhook
    message = {
        "embeds": [
            {
                "description": description,
                "color": colour,
                "author": {
                    "name": title,
                    "icon_url": coin_image_url
                },
                "timestamp": payload['data']['createdDate']
            }
        ]
    }
    return message


async def get_webhook_url(guild_id: str, channel_name: str) -> Optional[str]:
    """
    Gets or creates webhook url.

    @param guild_id: guild id of webhook
    @param channel_name: channel name of webhook
    @return: webhook url or None if error occurred
    """
    # get bot object
    bot_instance = data.get_bot_instance(guild_id)
    bot_object = main.main_bot if not bot_instance else main.running_bots[bot_instance[BOT_ID_KEY]]['bot']

    # wait until bot is ready, just in case
    await bot_object.wait_until_ready()

    # get guild object, fetch if needed, if bot cant access guild, return
    guild_object = bot_object.get_guild(int(guild_id))
    if not guild_object:
        guild_object = await bot_object.fetch_guild(int(guild_id))
        if not guild_object:
            return

    # get channel
    channel_object = discord.utils.get(guild_object.channels, name=channel_name)
    if not channel_object:
        return

    # get webhook
    webhook = data.get_webhook(guild_id, channel_object.id)
    if not webhook:
        # if webhook doesnt exist, create new one and add it to the webhooks database
        try:
            webhook_object = await channel_object.create_webhook(name='RallyBotAlerts', avatar=default_avatar)
            data.add_webhook(guild_id, channel_object.id, webhook_object.url, webhook_object.id, webhook_object.token)
            webhook_url = webhook_object.url
        except:
            return
    else:
        webhook_url = webhook[WEBHOOK_URI]

    return webhook_url


async def process_payload(payload: dict, failed: bool = False) -> None:
    """
    Process payload received by webhook endpoint.

    @param payload: received payload
    @param failed: True if failed to send message to webhook, False on first attempt
    @return: None
    """
    # add to stats
    coin_kind = payload['coinKind']
    event = payload['event'].lower()
    data.add_event(event, coin_kind)

    # find guilds that have coin_kind as default coin and loop through them
    guilds = data.get_guilds_by_coin(coin_kind)
    for guild in guilds:
        guild_id = guild[GUILD_ID_KEY]
        # get alert settings
        alerts_settings = data.get_alerts_settings(guild_id)
        if not alerts_settings:
            continue

        settings_data = alerts_settings[ALERTS_SETTINGS_KEY]

        # if event isn't enabled, continue
        if not settings_data[event]['enabled']:
            continue

        # go through each instance
        for instance in settings_data[event]['instances']:
            # if channel is empty, continue
            if not instance['channel']:
                continue

            # set default value for minamount if needed
            if 'minamount' not in instance['settings'] or not instance['settings']['minamount']:
                instance['settings']['minamount'] = 0.0

            # set default value for maxamount if needed
            if 'maxamount' not in instance['settings'] or not instance['settings']['maxamount'] or instance['settings']['maxamount'] == 0:
                instance['settings']['maxamount'] = sys.maxsize

            # get coin amount from variable according to event (convert event is special)
            coin_amount = payload['data']['amountOfCoin'] if payload['event'] != 'convert' else payload['data']['fromAmount']

            # check if amount is between min and max limits
            if float(instance['settings']['minamount']) <= float(coin_amount) <= float(instance['settings']['maxamount']):
                # get webhooks, return if cant get one
                webhook_url = await get_webhook_url(guild_id, instance['channel'])
                if not webhook_url:
                    continue

                # get message for event and send it
                message = await format_alert_message(event, payload, instance)
                request = requests.post(webhook_url, json=message)

                # request failed, delete webhook db entry and try again, if it fails a second time dont try again
                if request.status_code not in [200, 204] and not failed:
                    data.delete_webhook(webhook_url)
                    return await process_payload(payload, True)


def get_day_stats(coin: str) -> dict:
    """
    Return dict of stats of events in the past 24h

    @param coin: con symbol e.g. "STANZ"
    @return: stats dict
    """
    return {
        'buy': data.get_day_events('buy', coin),
        'donate': data.get_day_events('donate', coin),
        'transfer': data.get_day_events('transfer', coin),
        'convert': data.get_day_events('convert', coin),
        'redeem': data.get_day_events('redeem', coin),
    }


def get_week_stats(coin: str) -> dict:
    """
    Return dict of stats of events in the past week

    @param coin: con symbol e.g. "STANZ"
    @return: stats dict
    """
    return {
        'buy': data.get_week_events('buy', coin),
        'donate': data.get_week_events('donate', coin),
        'transfer': data.get_week_events('transfer', coin),
        'convert': data.get_week_events('convert', coin),
        'redeem': data.get_week_events('redeem', coin),
    }
