import dataset
import datetime
import urllib

import config
from constants import *

from utils.ext import connect_db

"""Functions for managing a dataset SQL database
    # Schemas

    #################### mappings ######################
    guildId
    coinKind
    requiredBalance
    roleName

    #################### channel_mappings ######################
    guildId
    coinKind
    requiredBalance
    channelName

    #################### rally_connections ######################
    discordId
    rallyId
    
    #################### channel_prefixes ######################
    guildId
    prefix
    
    #################### default_coin ######################
    guildId
    coin

    #################### server_config ####################
    purchaseMessage
    donateMessage
    
    #################### users ####################
    discordId
    username
    discriminator
    guilds
    
    #################### users_token ####################
    token
    discordId
    timeCreated
    
    #################### commands ####################
    name
    description

"""


@connect_db
def add_role_coin_mapping(db, guild_id, coin, required_balance, role):
    table = db[ROLE_MAPPINGS_TABLE]
    table.upsert(
        {
            GUILD_ID_KEY: guild_id,
            COIN_KIND_KEY: coin,
            REQUIRED_BALANCE_KEY: required_balance,
            ROLE_NAME_KEY: role,
        },
        [GUILD_ID_KEY, ROLE_NAME_KEY],
    )


@connect_db
def add_channel_coin_mapping(db, guild_id, coin, required_balance, channel):
    table = db[CHANNEL_MAPPINGS_TABLE]
    table.upsert(
        {
            GUILD_ID_KEY: guild_id,
            COIN_KIND_KEY: coin,
            REQUIRED_BALANCE_KEY: required_balance,
            CHANNEL_NAME_KEY: channel,
        },
        [GUILD_ID_KEY, CHANNEL_NAME_KEY],
    )


@connect_db
def get_role_mappings(db, guild_id, coin=None, required_balance=None, role=None):

    table = db[ROLE_MAPPINGS_TABLE]
    filtered_mappings = table.find(guildId=guild_id)
    if coin is not None:
        filtered_mappings = [m for m in filtered_mappings if m[COIN_KIND_KEY] == coin]
    if required_balance is not None:
        filtered_mappings = [
            m for m in filtered_mappings if m[REQUIRED_BALANCE_KEY] == required_balance
        ]
    if role is not None:
        filtered_mappings = [m for m in filtered_mappings if m[ROLE_NAME_KEY] == role]
    return filtered_mappings


@connect_db
def get_channel_mappings(db, guild_id, coin=None, required_balance=None, channel=None):

    table = db[CHANNEL_MAPPINGS_TABLE]
    filtered_mappings = table.find(guildId=guild_id)
    if coin is not None:
        filtered_mappings = [m for m in filtered_mappings if m[COIN_KIND_KEY] == coin]
    if required_balance is not None:
        filtered_mappings = [
            m for m in filtered_mappings if m[REQUIRED_BALANCE_KEY] == required_balance
        ]
    if channel is not None:
        filtered_mappings = [
            m for m in filtered_mappings if m[CHANNEL_NAME_KEY] == channel
        ]
    return filtered_mappings


@connect_db
def remove_role_mapping(db, guild_id, coin, required_balance, role):

    table = db[ROLE_MAPPINGS_TABLE]
    table.delete(
        guildId=guild_id, coinKind=coin, requiredBalance=required_balance, roleName=role
    )


@connect_db
def remove_channel_mapping(db, guild_id, coin, required_balance, channel):

    table = db[CHANNEL_MAPPINGS_TABLE]
    table.delete(
        guildId=guild_id,
        coinKind=coin,
        requiredBalance=required_balance,
        channel=channel,
    )


@connect_db
def add_discord_rally_mapping(db, discord_id, rally_id):
    table = db[RALLY_CONNECTIONS_TABLE]
    table.upsert({DISCORD_ID_KEY: discord_id, RALLY_ID_KEY: rally_id}, [DISCORD_ID_KEY])


@connect_db
def get_rally_id(db, discord_id):

    table = db[RALLY_CONNECTIONS_TABLE]
    row = table.find_one(discordId=discord_id)
    if row is not None:
        return row[RALLY_ID_KEY]
    return None


@connect_db
def get_all_users(db):

    table = db[RALLY_CONNECTIONS_TABLE]
    all_users = table.all()
    return all_users


@connect_db
def remove_discord_rally_mapping(db, discord_id, rally_id):

    table = db[RALLY_CONNECTIONS_TABLE]
    table.delete(
        discordId=discord_id,
        rallyId=rally_id,
    )


@connect_db
def add_prefix_mapping(db, guild_id, prefix):
    table = db[CHANNEL_PREFIXES_TABLE]
    table.upsert({GUILD_ID_KEY: guild_id, PREFIX_KEY: prefix}, [GUILD_ID_KEY])


@connect_db
def get_prefix(db, guild_id):

    table = db[CHANNEL_PREFIXES_TABLE]
    row = table.find_one(guildId=guild_id)
    if row is not None:
        return row[PREFIX_KEY]
    return None


@connect_db
def add_default_coin(db, guild_id, coin=None):
    table = db[DEFAULT_COIN_TABLE]
    table.upsert({GUILD_ID_KEY: guild_id, COIN_KIND_KEY: coin}, [GUILD_ID_KEY])


@connect_db
def get_default_coin(db, guild_id):

    table = db[DEFAULT_COIN_TABLE]
    row = table.find_one(guildId=guild_id)
    if row is not None:
        return row[COIN_KIND_KEY]
    return None


@connect_db
def set_purchase_message(db, guild_id, message):
    table = db[CONFIG_TABLE]
    table.upsert(
        {
            GUILD_ID_KEY: guild_id,
            PURCHASE_MESSAGE_KEY: message,
            CONFIG_NAME_KEY: PURCHASE_MESSAGE_KEY,
        },
        [GUILD_ID_KEY, CONFIG_NAME_KEY],
    )


@connect_db
def get_purchase_message(db, guild_id):
    table = db[CONFIG_TABLE]
    row = table.find_one(guildId=guild_id, configName=PURCHASE_MESSAGE_KEY)
    if row is not None:
        return row[PURCHASE_MESSAGE_KEY]
    return None


@connect_db
def set_donate_message(db, guild_id, message):
    table = db[CONFIG_TABLE]
    table.upsert(
        {
            GUILD_ID_KEY: guild_id,
            DONATE_MESSAGE_KEY: message,
            CONFIG_NAME_KEY: DONATE_MESSAGE_KEY,
        },
        [GUILD_ID_KEY, CONFIG_NAME_KEY],
    )


@connect_db
def get_donate_message(db, guild_id):
    table = db[CONFIG_TABLE]
    row = table.find_one(guildId=guild_id, configName=DONATE_MESSAGE_KEY)
    if row is not None:
        return row[DONATE_MESSAGE_KEY]
    return None


@connect_db
def set_bot_name(db, guild_id, name):
    table = db[CONFIG_TABLE]
    table.upsert(
        {
            GUILD_ID_KEY: guild_id,
            BOT_NAME_KEY: name,
            CONFIG_NAME_KEY: BOT_NAME_KEY
        },
        [GUILD_ID_KEY, CONFIG_NAME_KEY],
    )

@connect_db
def get_bot_name(db, guild_id):
    table = db[CONFIG_TABLE]
    row = table.find_one(guildId=guild_id, configName=BOT_NAME_KEY)
    if row is not None:
        return row[BOT_NAME_KEY]
    return None


@connect_db
def set_bot_avatar(db, url):
    try:
        response = urllib.request.urlopen(url)

        table = db[CONFIG_TABLE]
        table.upsert(
            {
                BOT_AVATAR_KEY: response.read(),
                CONFIG_NAME_KEY: BOT_AVATAR_KEY
            },
            [CONFIG_NAME_KEY],
        )
        table.upsert(
            {
                BOT_AVATAR_URL_KEY: url,
                CONFIG_NAME_KEY: BOT_AVATAR_URL_KEY
            },
            [CONFIG_NAME_KEY],
        )

    except urllib.error.HTTPError as e:
        raise Exception("Failed to download avatar") from e


@connect_db
def get_bot_avatar(db):
    table = db[CONFIG_TABLE]
    row = table.find_one(configName=BOT_AVATAR_KEY)
    if row is not None:
        return row[BOT_AVATAR_KEY]
    return None


@connect_db
def get_bot_avatar_url(db):
    table = db[CONFIG_TABLE]
    row = table.find_one(configName=BOT_AVATAR_URL_KEY)
    if row is not None:
        return row[BOT_AVATAR_URL_KEY]
    return None


@connect_db
def set_bot_avatar_hash(db, hash):
    table = db[CONFIG_TABLE]
    table.upsert(
        {
            BOT_AVATAR_HASH_KEY: hash,
            CONFIG_NAME_KEY: BOT_AVATAR_HASH_KEY
        },
        [CONFIG_NAME_KEY],
    )


@connect_db
def get_bot_avatar_hash(db):
    table = db[CONFIG_TABLE]
    row = table.find_one(configName=BOT_AVATAR_HASH_KEY)
    if row is not None:
        return row[BOT_AVATAR_HASH_KEY]
    return None


@connect_db
def add_user(db, discord_id, username, discriminator, guilds):
    table = db[USERS_TABLE]
    table.upsert(
        {
            DISCORD_ID_KEY: discord_id,
            USERNAME_KEY: username,
            DISCREMINATOR_KEY: discriminator,
            GUILDS_KEY: guilds,
        },
        [DISCORD_ID_KEY],
    )


@connect_db
def get_user_guilds(db, discord_id):
    table = db[USERS_TABLE]
    row = table.find_one(discordId=discord_id)
    if row is not None:
        return row[GUILDS_KEY]
    return None


@connect_db
def add_user_token(db, token, discord_id):
    table = db[USERS_TOKEN_TABLE]
    table.upsert(
        {
            TOKEN_KEY: token,
            DISCORD_ID_KEY: discord_id,
            TIME_CREATED_KEY: datetime.datetime.now(),
        },
        [DISCORD_ID_KEY],
    )


@connect_db
def get_user_id(db, token):
    table = db[USERS_TOKEN_TABLE]
    row = table.find_one(token=token)
    if row is not None:
        created = row[TIME_CREATED_KEY]
        if (created + datetime.timedelta(hours=1)) >= datetime.datetime.now():
            return row[DISCORD_ID_KEY]
        else:
            table.delete(token=token)
    return None


@connect_db
def add_command(db, name, description):
    table = db[COMMANDS_TABLE]
    table.upsert(
        {
            NAME_KEY: name,
            DESCRIPTION_KEY: description,
        },
        [NAME_KEY],
    )


@connect_db
def get_all_commands(db):
    table = db[COMMANDS_TABLE]
    return table.all()