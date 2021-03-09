from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel


class ChannelMapping(BaseModel):
    id: Optional[int] = None
    guildId: Optional[str] = None
    coinKind: str
    requiredBalance: str
    channel: str


class RoleMapping(BaseModel):
    id: Optional[int] = None
    guildId: Optional[str] = None
    coinKind: str
    requiredBalance: str
    roleName: str


class CoinMapping(BaseModel):
    guildId: Optional[str] = None
    coinKind: Optional[str] = None


class PrefixMapping(BaseModel):
    guildId: Optional[str] = None
    prefix: str


class Command(BaseModel):
    name: str
    description: str


class AlertsSettings(BaseModel):
    guildId: Optional[str] = None
    settings: Optional[Dict] = None
    error: Optional[str] = None

      
class CoinPrice(BaseModel):
    coinKind: str
    priceInUSD: str
    usd_24h_change: Optional[str] = None


class CoinPrices(BaseModel):
    id: Optional[int] = None
    timeCreated: datetime
    coinKind: str
    priceInUSD: str


class BotNameMapping(BaseModel):
    bot_name: str
    name_timeout: Optional[int] = None


class BotAvatarMapping(BaseModel):
    bot_avatar: str
    avatar_timeout: Optional[int] = None
    guildId: Optional[str] = None


class BotInstanceMapping(BaseModel):
    bot_instance: str
    activity_type: Optional[str] = None
    activity_text: Optional[str] = None
    bot_avatar: Optional[str] = None
    avatar_timeout: Optional[int] = None
    bot_name: Optional[str] = None
    bot_id: Optional[int] = None
    name_timeout: Optional[int] = None


class BotActivityMapping(BaseModel):
    success: Optional[str] = None
    activity_type: Optional[str] = None
    activity_text: Optional[str] = None
