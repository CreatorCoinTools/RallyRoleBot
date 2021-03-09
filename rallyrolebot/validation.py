from discord.ext import commands
from discord.utils import get

import errors
import data


def owner_or_permissions(**perms):
    """
    Decorator to check for discord.py specific paramaters before running a given cog command

    Returns
    --------
        True if the user is the owner of the guild or
        the user satisfies all keyword arguments (ex. adminstrator = True)
        and the command is run in a server (Not a private message)

    Raises
    ---------

        CheckFailure
        NoPrivateMessage
    """
    original = commands.has_permissions(**perms).predicate

    async def extended_check(ctx):
        if ctx.guild is None:
            raise errors.NoPrivateMessage
        return ctx.guild.owner_id == ctx.author.id or await original(ctx)

    return commands.check(extended_check)


async def is_valid_role(ctx, role_name):
    """
    TODO: Use discord.py converters instead of is_valid_role check
    """
    if get(ctx.guild.roles, name=role_name) is None:
        await ctx.send("Role does not exist on this server. Please create it first.")
        return False
    return True


async def is_valid_channel(ctx, channel_name):
    """
    TODO: Use discord.py converters instead of is_valid_channel check
    """
    matched_channels = [
        channel for channel in ctx.guild.channels if channel.name == channel_name
    ]
    if len(matched_channels) == 0:
        await ctx.send(
            "Cannot find the channel "
            + channel_name
            + " ensure that the bot has permissions for the channel."
        )
        return False
    return True


def is_wallet_verified():
    async def extended_check(ctx):
        rally_id = data.get_rally_id(ctx.message.author.id)
        if rally_id is None:
            raise errors.WalletNotVerified(
                ctx.message.author.mention
                + " you haven't verified your wallet yet! Use the `set_rally_id` command"
            )
        return True

    return commands.check(extended_check)
