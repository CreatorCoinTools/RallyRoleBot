import json
import sys
import traceback
import threading

import discord
from discord.ext import commands, tasks
from discord.utils import get

from constants import *

import errors
import data
import rally_api
import validation

from cogs import defaults_cog

async def grant_deny_channel_to_member(channel_mapping, member, balances):
    """
    Determine if the rally_id and balance for a channel is still valid for a particular member
    Update status in database.

    Parameters
    __________

      channel_mapping  (list) - list of information for the channel mapped to the member
      member (discord.Member) - The discord member to check
      balances (list)  - The amount of coin allocated to this member per coin

    """

    print("Checking channel")
    rally_id = data.get_rally_id(member.id)
    if rally_id is None or balances is None:
        return
    matched_channels = [
        channel
        for channel in member.guild.channels
        if channel.name == channel_mapping[data.CHANNEL_NAME_KEY]
    ]
    if len(matched_channels) == 0:
        return
    channel_to_assign = matched_channels[0]
    if channel_to_assign is not None:
        if (
            rally_api.find_balance_of_coin(
                channel_mapping[data.COIN_KIND_KEY], balances
            )
            >= channel_mapping[data.REQUIRED_BALANCE_KEY]
        ):
            perms = channel_to_assign.overwrites_for(member)
            perms.send_messages = True
            perms.read_messages = True
            perms.read_message_history = True
            await channel_to_assign.set_permissions(member, overwrite=perms)
            print("Assigned channel to member")
        else:
            perms = channel_to_assign.overwrites_for(member)
            perms.send_messages = False
            perms.read_messages = False
            perms.read_message_history = False
            await channel_to_assign.set_permissions(member, overwrite=perms)
            print("Removed channel to member")
    else:
        print("Channel not found")


async def grant_deny_role_to_member(role_mapping, member, balances):
    """
    Determine if the rally_id and balance for a role is still valid for a particular member
    Update status in database.

    Parameters
    __________

      channel_mapping (list) - list of information for the channel mapped to the member
      member (discord.Member) - The discord member to check
      balances (list)  - The amount allocated to this member per coin

    """

    rally_id = data.get_rally_id(member.id)
    if rally_id is None or balances is None:
        return
    role_to_assign = get(member.guild.roles, name=role_mapping[data.ROLE_NAME_KEY])
    if (
        rally_api.find_balance_of_coin(role_mapping[data.COIN_KIND_KEY], balances)
        >= role_mapping[data.REQUIRED_BALANCE_KEY]
    ):
        if role_to_assign is not None:
            await member.add_roles(role_to_assign)
            print("Assigned role to member")
        else:
            print("Can't find role")
            print(role_mapping["role"])
    else:
        if role_to_assign in member.roles:
            await member.remove_roles(role_to_assign)
            print("Removed role to member")


async def force_update(bot, ctx):
    await bot.get_cog("UpdateTask").force_update(ctx)


class UpdateTask(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_lock = threading.Lock()
        self.update.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print("We have logged in as {0.user}".format(self.bot))

    @errors.standard_error_handler
    async def cog_command_error(self, ctx, error):
        # All other Errors not returned come here. And we can just print the default TraceBack.
        print("Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

    @commands.command(name="update", help="Force an immediate update")
    @validation.owner_or_permissions(administrator=True)
    async def force_update(self, ctx):
        self.update.restart()
        await ctx.send("Updating!")

    @tasks.loop(seconds=UPDATE_WAIT_TIME)
    async def update(self):
        with self.update_lock:

            print("Updating roles")
            guilds = self.bot.guilds
            guild_count = 0
            member_count = 0
            mapping_count = 0

            for guild in guilds:

                guild_count += 1
                await guild.chunk()

                role_mappings = list(data.get_role_mappings(guild.id))
                channel_mappings = list(data.get_channel_mappings(guild.id))
                mapping_count += len(role_mappings) + len(channel_mappings)

                for member in guild.members:
                    member_count += 1
                    rally_id = data.get_rally_id(member.id)
                    if rally_id:
                        balances = rally_api.get_balances(rally_id)
                        for role_mapping in role_mappings:
                            print(role_mapping)
                            await grant_deny_role_to_member(
                                role_mapping, member, balances
                            )
                        for channel_mapping in channel_mappings:
                            await grant_deny_channel_to_member(
                                channel_mapping, member, balances
                            )

                # Update bot config
                try:
                    bot_name = data.get_bot_name(guild.id)
                    if bot_name != guild.me.nick:
                        await guild.me.edit(nick=bot_name)
                except discord.errors.HTTPException as e:
                    print("Failed to update bot's nickname:", e)

                try:
                    bot_avatar = data.get_bot_avatar()
                    bot_avatar_url = data.get_bot_avatar_url()
                    bot_avatar_hash = data.get_bot_avatar_hash()
                    if not bot_avatar_url:
                        url = DEFAULT_BOT_AVATAR_URL
                        data.set_bot_avatar(url)
                        data.set_bot_avatar_hash("")
                        await self.update()
                        data.set_bot_avatar_hash(self.bot.user.avatar)
                    elif bot_avatar_hash != self.bot.user.avatar:
                        print("Updating avatar")
                        await self.bot.user.edit(avatar=bot_avatar)
                except discord.errors.HTTPException as e:
                    print("Failed to update bot's avatar:", e)
                    data.set_bot_avatar_hash("")

            print(
                "Done! Checked "
                + str(guild_count)
                + " guilds. "
                + str(mapping_count)
                + " mappings. "
                + str(member_count)
                + " members."
            )
