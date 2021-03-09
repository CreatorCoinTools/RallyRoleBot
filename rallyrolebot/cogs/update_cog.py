import sys
import traceback
import threading
import discord
import discord.utils
import main

from discord.ext import commands
from discord.ext import tasks as discord_tasks
from discord.utils import get
from constants import *
from utils import tasks
import aiohttp

import asyncio
import errors
import data
import rally_api
import validation
from utils import pretty_print

default_avatar = ''


# sets global default avatar value for use in webhooks
async def set_default_avatar():
    global default_avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(DEFAULT_BOT_AVATAR_URL) as response:
            default_avatar = await response.read()


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
    def __init__(self, bot: main.RallyRoleBot):
        self.bot = bot
        self.update_lock = threading.Lock()
        self.task_run_lock = threading.Lock()

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

    @discord_tasks.loop(seconds=5)
    async def run_tasks(self):
        await self.bot.wait_until_ready()
        with self.task_run_lock:
            all_tasks = data.get_tasks()
            for task in all_tasks:
                try:
                    # get function object and kwargs
                    task_function = getattr(tasks, task['function'])
                    kwargs = task['kwargs']

                    # call function
                    asyncio.create_task(task_function(**kwargs))

                    # delete task
                    data.delete_task(task['id'])
                except Exception as e:
                    print(e)

    @discord_tasks.loop(seconds=UPDATE_WAIT_TIME)
    async def update(self):
        await self.bot.wait_until_ready()
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

            print(
                "Done! Checked "
                + str(guild_count)
                + " guilds. "
                + str(mapping_count)
                + " mappings. "
                + str(member_count)
                + " members."
            )

    @commands.command(
        name='change_rally_id',
        help="updates your wallet balance / roles immediately"
    )
    @commands.guild_only()
    async def set_rally_id(self, ctx):
        member = ctx.author

        with self.update_lock:
            for guild in self.bot.guilds:
                await guild.chunk()

                if member not in guild.members:
                    continue

                role_mappings = list(data.get_role_mappings(guild.id))
                channel_mappings = list(data.get_channel_mappings(guild.id))

                rally_id = data.get_rally_id(member.id)
                if rally_id:
                    balances = rally_api.get_balances(rally_id)
                    for role_mapping in role_mappings:
                        try:
                            await grant_deny_role_to_member(
                                role_mapping, member, balances
                            )
                        except discord.HTTPException:
                            raise errors.RequestError("network error, try again later")
                        except:
                            # Forbidden, NotFound or Invalid Argument exceptions only called when code
                            # or bot is wrongly synced / setup
                            raise errors.FatalError("bot is setup wrong, call admin")
                    for channel_mapping in channel_mappings:
                        try:
                            await grant_deny_channel_to_member(
                                channel_mapping, member, balances
                            )
                        except discord.HTTPException:
                            raise errors.RequestError("network error, try again later")
                        except:
                            # Forbidden, NotFound or Invalid Argument exceptions only called when code
                            # or bot is wrongly synced / setup
                            raise errors.FatalError("bot is setup wrong, call admin")

            await pretty_print(
                ctx,
                "Command completed successfully!",
                title="Success",
                color=SUCCESS_COLOR,
            )


def setup(bot: main.RallyRoleBot):
    bot.add_cog(UpdateTask(bot))
