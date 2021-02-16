from discord import Color

# TODO: Place holder for now - can use __init__.py once dependencies such as
# data.ROLE_MAPPINGS_TABLE and rally_api.BASE_URL have been removed

"""
 Constants useful for data module
"""
ROLE_MAPPINGS_TABLE = "mappings"
CHANNEL_MAPPINGS_TABLE = "channel_mappings"
RALLY_CONNECTIONS_TABLE = "rally_connections"
CHANNEL_PREFIXES_TABLE = "channel_prefixes"
DEFAULT_COIN_TABLE = "default_coin"
CONFIG_TABLE = "config"
USERS_TABLE = "users"
USERS_TOKEN_TABLE = "users_token"
COMMANDS_TABLE = "commands"
COIN_PRICE_TABLE = "coin_price"


GUILD_ID_KEY = "guildId"
PRICE_KEY = "priceInUSD"
REQUIRED_BALANCE_KEY = "requiredBalance"
ROLE_NAME_KEY = "roleName"
CHANNEL_NAME_KEY = "channel"
DISCORD_ID_KEY = "discordId"
RALLY_ID_KEY = "rallyId"

BOT_TOKEN_KEY = "botToken"
BOT_INSTANCES_KEY = "botInstances"
OWNER_ID_KEY = "ownerId"
TIME_ADDED_KEY = "timeAdded"
BOT_NAME_KEY = "botName"
BOT_AVATAR_KEY = "botAvatar"
BOT_ID_KEY = "botId"
AVATAR_TIMEOUT_KEY = "avatarTimeout"
NAME_TIMEOUT_KEY = "nameTimeout"
BOT_ACTIVITY_TEXT_KEY = "botActivityText"
BOT_ACTIVITY_TYPE_KEY = "botActivityType"

USERNAME_KEY = "username"
DISCRIMINATOR_KEY = "discriminator"
GUILDS_KEY = "guilds"
TOKEN_KEY = "token"
TIME_CREATED_KEY = "timeCreated"
NAME_KEY = "name"
DESCRIPTION_KEY = "description"

PREFIX_KEY = "prefix"

CONFIG_NAME_KEY = "configName"
PURCHASE_MESSAGE_KEY = "purchaseMessage"
DONATE_MESSAGE_KEY = "donateMessage"

ALERT_SETTINGS_TABLE = 'alerts_settings_table'
ALERTS_SETTINGS_KEY = 'settings'

WEBHOOKS_TABLE = 'webhook_table'
WEBHOOK_URI = 'webhook_uri'
WEBHOOK_CHANNEL_ID = 'webhook_channel'
WEBHOOK_ID = 'webhook_id'
WEBHOOK_TOKEN = 'webhook_token'

TIMERS_TABLE = 'timers_table'

COIN_KIND_KEY = 'coinKind'

EVENTS_TABLE = 'eventsTable'
EVENT_KEY = 'event'


"""
 Constants useful for  rally_api module
"""

COIN_BALANCE_KEY = "coinBalance"

BASE_URL = "https://api.rally.io/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
DISCORD_API_URL = "https://discord.com/api"


"""
    Constants useful for update_cog module
"""
UPDATE_WAIT_TIME = 600

"""
    Miscellaneous constants
"""

ERROR_COLOR = Color(0xFF0000)
SUCCESS_COLOR = Color(0x0000FF)
WARNING_COLOR = Color(0xFFFF00)
GREEN_COLOR = Color(0x00FF00)
RED_COLOR = Color(0xFF0000)
WHITE_COLOR = Color(0xFFFFFE)
DARK_RED_COLOR = Color(0x800000)
DARK_GREEN_COLOR = Color(0x008000)

PRICE_GRADIENT_DEPTH = 5

DEFAULT_DONATE_MESSAGE = "You can donate to by going to - Your donation helps grow and support the community and creator - Plus, there are 10 tiers of Donation badges to earn to show off your support!"
DEFAULT_PURCHASE_MESSAGE = "You can purchase at by using a Credit/Debit card or a number of different Crypto Currencies! Buying earns rewards, supports the community, and you can even get VIP Status! (hint: there’s a secret VIP room for users who hold over X # of ;)"

DEFAULT_BOT_AVATAR_URL = "https://rallybot.app/img/space.5424f731.png"

API_TAGS_METADATA = [
    {"name": "channels", "description": "Coin channel mappings"},
    {"name": "coin", "description": "Default coin in guild"},
    {"name": "commands", "description": "Get list of all available bot commands"},
    {"name": "prefix", "description": "Command prefix in guild"},
    {"name": "roles", "description": "Coin role mappings"},
    {"name": "coins", "description": "Coin price data"},
    {"name": "bot_instance", "description": "Bot instances"},
    {"name": "bot_avatar", "description": "Configure bot avatar"},
    {"name": "bot_name", "description": "Configure bot name"},
]