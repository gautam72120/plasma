from discord.ext import commands

from . import constants


def is_admin():
    async def predicate(ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()

        if (
            await ctx.bot.is_owner(ctx.author)
            or ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
        ):
            return True
        raise commands.CheckFailure("You are not an admin.")

    return commands.check(predicate)


def is_moderator():
    async def predicate(ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()

        query = {"_id": ctx.guild.id}
        entry = await ctx.bot.mongo.db.guild.find_one_and_update(
            query, {"$setOnInsert": query}, upsert=True, return_document=True
        )
        roles = entry.get("moderators", [])

        if (
            await ctx.bot.is_owner(ctx.author)
            or ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
            or any(role.id in roles for role in ctx.author.roles)
        ):
            return True
        raise commands.CheckFailure("You are not a moderator.")

    return commands.check(predicate)


def is_premium():
    async def predicate(ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()

        guild = ctx.bot.get_guild(constants.COMMUNITY_SERVER_ID)
        member = guild.get_member(ctx.author.id)

        if (
            await ctx.bot.is_owner(ctx.author)
            or ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
            or (member and member.premium_since)
        ):
            return True
        raise commands.BadArgument("You are not a server booster.")

    return commands.check(predicate)


def in_guilds(*guild_ids):
    def predicate(ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()

        if ctx.guild.id in guild_ids:
            return True
        raise commands.CheckFailure("This command is not available in this guild.")

    return commands.check(predicate)


def community_server_only():
    return in_guilds(constants.COMMUNITY_SERVER_ID)


def exclusive_server_only():
    return in_guilds(constants.EXCLUSIVE_SERVER_ID)
