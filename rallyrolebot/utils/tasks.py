# tasks.py from https://github.com/dmontagu/fastapi-utils
import asyncio
import logging
import discord
import data
import time
import datetime
import os
import main

from cogs import update_cog
from constants import *
from asyncio import ensure_future
from functools import wraps
from traceback import format_exception
from typing import Any, Callable, Coroutine, Optional, Union

from starlette.concurrency import run_in_threadpool


NoArgsNoReturnFuncT = Callable[[], None]
NoArgsNoReturnAsyncFuncT = Callable[[], Coroutine[Any, Any, None]]
NoArgsNoReturnDecorator = Callable[
    [Union[NoArgsNoReturnFuncT, NoArgsNoReturnAsyncFuncT]], NoArgsNoReturnAsyncFuncT
]


def repeat_every(
    *,
    seconds: float,
    wait_first: bool = False,
    logger: Optional[logging.Logger] = None,
    raise_exceptions: bool = False,
    max_repetitions: Optional[int] = None
) -> NoArgsNoReturnDecorator:
    """
    Returns decorator that modifies a function to be run periodically after it's first call

    Parameters
    ----------
    seconds: float
        Repeat every x seconds
    wait_first: bool (default False)
        Wait before executing first call
    logger: Optional[logging.Logger] (default None)
        log any exceptions raised
    raise_exceptions: bool (default False)
        Only use if you want periodic execution to stop if there's an exception.
        Errors raised by the deecorated function will be raised to the  event loops exception handler.
    max_repetitions: Optional[int] (default None)
        Max number of times to repeat function, otherwise run forever
    """

    def decorator(
        func: Union[NoArgsNoReturnAsyncFuncT, NoArgsNoReturnFuncT]
    ) -> NoArgsNoReturnAsyncFuncT:
        """
        Convert decorated function to repeated function
        """
        is_coroutine = asyncio.iscoroutinefunction(func)

        @wraps(func)
        async def wrapped() -> None:
            repetitions = 0

            async def loop() -> None:
                nonlocal repetitions
                if wait_first:
                    await asyncio.sleep(seconds)
                while max_repetitions is None or repetitions < max_repetitions:
                    try:
                        if is_coroutine:
                            await func()
                        else:
                            await run_in_threadpool(func)
                        repetitions += 1
                    except Exception as exc:
                        if logger is not None:
                            formatted_exception = "".join(
                                format_exception(type(exc), exc, exc.__traceback__)
                            )
                            logger.error(formatted_exception)
                        if raise_exceptions:
                            raise exc
                    await asyncio.sleep(seconds)

            ensure_future(loop())

        return wrapped

    return decorator


async def update_avatar(guild_id: int, bot_id: int, new_avatar_path: str):
    """
    Update the avatar of a bot instance.

    @param guild_id: id of guild
    @param bot_id: id of bot
    @param new_avatar_path: path to tmp bot avatar file
    """

    # read file bytes
    with open(new_avatar_path, 'rb') as file:
        new_avatar = file.read()

    # delete tmp file
    os.remove(new_avatar_path)

    if new_avatar is None:
        new_avatar = update_cog.default_avatar

    # avatar change
    try:
        bot_object = main.running_bots[bot_id]['bot']
        await bot_object.user.edit(avatar=new_avatar)
        data.set_bot_avatar(guild_id, str(bot_object.user.avatar_url))
    except discord.HTTPException:
        # user is editing avatar too many times, set 1h timeout
        timout = round(time.time() + 3600)
        data.set_avatar_timout(guild_id, timout)
    except:
        pass


async def update_activity(guild_id: int, bot_id: int, activity_type_str: str, activity_text: str):
    """
    Updates bot activity on the bot instance and in the database

    @param guild_id: id of guild
    @param bot_id: id of bot
    @param activity_type_str: string of activity type to be converted into discord activity object
    @param activity_text: text for activity
    """
    if activity_type_str and activity_text:
        # get proper object for activity type
        activity_type_switch = {
            'playing': discord.ActivityType.playing,
            'listening': discord.ActivityType.listening,
            'competing': discord.ActivityType.competing,
            'watching': discord.ActivityType.watching
        }
        activity_type = activity_type_switch.get(activity_type_str, None)
        if not activity_type:
            return

        current_activity = main.running_bots[bot_id]['activity']
        bot_object = main.running_bots[bot_id]['bot']

        try:
            # check that current_activity isn't duplicate of new activity
            if not current_activity or (current_activity and current_activity.type != activity_text) or \
                    (current_activity and repr(current_activity.name) != repr(activity_text)):
                # update all the needed stuff
                new_activity = discord.Activity(type=activity_type, name=activity_text)
                main.running_bots[bot_id]['activity'] = new_activity
                await bot_object.change_presence(status=discord.Status.online, activity=new_activity)
                data.set_activity(guild_id, activity_type_str, activity_text)
        except:
            pass


async def start_daily_stats_timers(guild_id: int, timezone, channel: str):
    """
    Start daily_stats timer for provided guild and channel

    @param guild_id: id of guild
    @param timezone: number from -12 to +12, set by users to tell the bot when to send the message in
    relation to the utc timezone
    @param channel: name of channel where message will be sent
    """
    # get bot instance, if it isn't set, assume the bot being used is the main one
    bot_instance = data.get_bot_instance(guild_id)
    bot_object = main.main_bot if not bot_instance else main.running_bots[bot_instance[BOT_ID_KEY]]['bot']

    try:
        # get guild to see if bot has permission to manage webhooks
        guild_object = bot_object.get_guild(guild_id)
        if not guild_object:
            guild_object = await bot_object.fetch_guild(guild_id)
            if not guild_object:
                return

        has_permission = guild_object.me.guild_permissions.is_superset(discord.Permissions(536870912))
        if not has_permission:
            return
    except:
        # just in case no guild can be gotten
        return

    # set timezone to a default 0 if needed
    if not timezone:
        timezone = '0'

    try:
        # get time relative to user timezone
        dt = datetime.datetime.utcnow() + datetime.timedelta(hours=int(timezone))
    except:
        return

    # get time until midnight
    time_midnight = time.time() + (((24 - dt.hour - 1) * 60 * 60) + ((60 - dt.minute - 1) * 60) + (60 - dt.second))

    # start new timer for instance
    bot_object.timers.create(
        guild_id=guild_id,
        expires=time_midnight,
        event='daily_stats',
        extras={
            'channel_name': channel,
            'timezone': timezone
        },
        bot_id=bot_object.user.id,
    )


async def start_new_bot_instance(bot_token: str):
    """
    Start up a new instance of a bot.

    @param bot_token: Token of the new bot
    """
    # add token to running bot instances list
    main.running_bot_instances.append(bot_token)
    # create task for bot startup
    asyncio.create_task(main.RallyRoleBot.start_bot_instance(bot_token))


async def update_name(guild_id: int, bot_id: int, new_name: str):
    """
    Update the name of bot

    @param guild_id: id of guild
    @param bot_id: id of bot
    @param new_name: new neame of the bot
    """
    bot_object = main.running_bots[bot_id]['bot']
    # name change
    try:
        if new_name != bot_object.user.name:
            await bot_object.user.edit(username=new_name)
            data.set_bot_name(guild_id, new_name)
    except discord.HTTPException:
        # user is editing name too many times, set 1h timeout
        timout = round(time.time() + 3600)
        data.set_name_timeout(guild_id, timout)
    except:
        pass


async def delete_bot_instance(guild_id: int):
    """
    Delete a bot instance and stop it

    @param guild_id: id of guild
    """

    bot_instance = data.get_bot_instance(guild_id)
    try:
        data.remove_bot_instance(guild_id)
        main.running_bot_instances.remove(bot_instance[BOT_TOKEN_KEY])
        to_be_removed = main.running_bots[bot_instance[BOT_ID_KEY]]
        if to_be_removed:
            await to_be_removed['bot'].close()
            del main.running_bots[bot_instance[BOT_ID_KEY]]
    except:
        pass
