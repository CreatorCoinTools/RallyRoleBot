import errors

from discord.ext import commands

""" 
    A collection of useful decorators used for checking 
    certain properties of discord commands
"""


# Case insensitive check for custom role
def has_any_role(*roles):
    original = commands.has_any_role(roles).predicate

    @commands.guild_only()
    async def predicate(ctx):
        for role in roles:
            if role.lower() in [i.name.lower() for i in ctx.guild.roles]:
                return True
        return await original(ctx)

    return commands.check(predicate)


# Case insensitive check for custom role
def does_not_have_role(*roles):
    async def predicate(ctx):
        if not ctx.guild:
            return True
        if not ctx.guild.roles:
            return True
        for role in roles:
            print("here", role)
            if role.lower() in [i.name.lower() for i in ctx.guild.roles]:
                raise errors.IllegalRole(
                    f"Users with the role '{role.upper()}' are not allowed \
                        to use this command"
                )
        return True

    return commands.check(predicate)
