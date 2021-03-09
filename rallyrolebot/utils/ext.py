import os

import functools

import dataset
import config

db = None


def create_dm(cog_function):
    """
    Decorator that creates a Direct Message (dm) and appends it to the current context.
    Must receive a class function with a Context argument.
    Useful in discord.Cog calls
    """

    # Preserve function name so discord can still call the command
    @functools.wraps(cog_function)
    async def wrapper(cls, ctx, *args, **kwargs):
        ctx.dm = None
        try:
            ctx.dm = await ctx.author.create_dm()
        except:
            print("Could not create dm")
        await cog_function(cls, ctx, *args, **kwargs)

    return wrapper


def send_to_dm(cog_function):
    """
    Decorator that creates a Direct Message (dm) and converts the current context to it
    Must recieve a class function with a Context argument.
    Useful in discord.Cog calls
    """

    # Preserve function name so discord can still call the command
    @functools.wraps(cog_function)
    async def wrapper(cls, ctx, *args, **kwargs):
        try:
            ctx.channel = await ctx.author.create_dm()
        except:
            print("Could not create dm")
        await cog_function(cls, ctx, *args, **kwargs)

    return wrapper


def connect_db(function):
    """
    Decorator that creates a database object and inserts as its
    the first argument in the calling function.
    Useful to prevent global objects
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        result = None
        engine_kwargs = {}

        pool_size = os.getenv("POOL_SIZE")
        max_overflow = os.getenv("MAX_OVERFLOW")

        if pool_size:
            engine_kwargs["pool_size"] = int(pool_size)

        if max_overflow:
            engine_kwargs["max_overflow"] = int(max_overflow)

        try:
            url = config.CONFIG.database_connection
        except:
            url = os.getenv("DATABASE_URL")

        global db
        if not db:
            db = dataset.connect(url, engine_kwargs=engine_kwargs)

        try:
            result = function(db, *args, **kwargs)
        except:
            db.rollback()

        return result

    return wrapper
