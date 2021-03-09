from discord.ext import commands
from discord.ext.commands.errors import *
from constants import *
from utils import pretty_print


class IllegalRole(commands.CommandError):
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message


class WalletNotVerified(commands.CommandError):
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message


class InvalidCoin(commands.CommandError):
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message


class RequestError(commands.CommandError):
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message


class FatalError(commands.CommandError):
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message


def standard_error_handler(error_function):
    """
    Decorator that is prepended to a cog_command_error.
    It transforms the error handler into one that makes helpful and specific checks
    and returns a function that readily prints the error
    """

    async def wrapper(cls, ctx, error):

        extra = f"\n\nSee the help message for more information."

        # This prevents any commands with local handlers being handled here
        if hasattr(ctx.command, "on_error"):
            return

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, "original", error)

        ignored = (commands.CommandNotFound,)

        # Anything in ignored will return and prevent anything happening.
        if any([isinstance(error, i) for i in ignored]):
            return

        if isinstance(error, DisabledCommand):
            await pretty_print(
                ctx, "This command is disabled!", title="Error", color=ERROR_COLOR
            )

        elif isinstance(error, MemberNotFound):
            await pretty_print(
                ctx,
                str(error) + "\nNote: this command is case-sensitive." + extra,
                title="Error",
                color=ERROR_COLOR,
            )
            return

        elif isinstance(error, RoleNotFound):
            await pretty_print(
                ctx,
                str(error) + "\nNote: this command is case-sensitive." + extra,
                title="Error",
                color=ERROR_COLOR,
            )
            return

        elif isinstance(error, NoPrivateMessage):
            await pretty_print(
                ctx,
                "This command cannot be run in a private message." + extra,
                title="Error",
                color=ERROR_COLOR,
            )
            return

        elif isinstance(error, PrivateMessageOnly):
            try:
                await ctx.message.delete()
                extra += "\nYour message has been deleted"
            except:
                print("Could not delete message")
            await pretty_print(
                ctx,
                "This command should be run in a Private Message only!" + extra,
                title="Error",
                color=ERROR_COLOR,
            )
            return

        elif isinstance(error, MissingRole):
            await pretty_print(
                ctx, str(error) + extra, title="Error", color=ERROR_COLOR
            )
            return

        elif isinstance(error, IllegalRole):
            await pretty_print(
                ctx, error.message + extra, title="Error", color=ERROR_COLOR
            )
            return

        elif isinstance(error, CheckFailure):
            await pretty_print(
                ctx,
                "Could not run command, do you have sufficient permissions in this channel?"
                + extra,
                title="Error",
                color=ERROR_COLOR,
            )
            return

        elif isinstance(error, BadArgument):
            await ctx.send_help(ctx.command)
            await pretty_print(
                ctx,
                "Could not run command, is it formatted properly?" + extra,
                title="Error",
                color=ERROR_COLOR,
            )
            return

        elif isinstance(error, MissingRequiredArgument):
            await ctx.send_help(ctx.command)
            await pretty_print(
                ctx, "Missing required arguments", title="Error", color=ERROR_COLOR
            )
            return

        elif isinstance(error, BadUnionArgument):
            await ctx.send_help(ctx.command)
            await pretty_print(
                ctx,
                "Invalid argument",
                title="Error",
                color=ERROR_COLOR,
            )
            return

        elif isinstance(error, WalletNotVerified):
            await pretty_print(
                ctx, error.message + extra, title="Error", color=ERROR_COLOR
            )
            return

        elif isinstance(error, InvalidCoin):
            await pretty_print(
                ctx, error.message + extra, title="Error", color=ERROR_COLOR
            )
            return

        elif isinstance(error, RequestError):
            await pretty_print(
                ctx, error.message + extra, title="Error", color=ERROR_COLOR
            )
            return
        elif isinstance(error, FatalError):
            await pretty_print(
                ctx, error.message + extra, title="Error", color=ERROR_COLOR
            )
            return
        await error_function(cls, ctx, error)

    return wrapper
