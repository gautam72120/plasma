import re
from datetime import timedelta

import discord
from discord.ext import commands

from helpers import checks
from helpers.embeds import Embed
from helpers.formats import human_timedelta
from helpers.pagination import CodeBlockTablePageSource, Paginator
from helpers.utils import FakeUser


class Reputation(commands.Cog):
    """For reputation."""

    triggers = (
        "+rep",
        "thank",
        "thanks",
        "thx",
        "ty",
        "thnx",
        "tnx",
        "tysm",
        "tyvm",
        "thanx",
    )

    def __init__(self, bot):
        self.bot = bot
        self.regex = re.compile(
            rf"(?<!\w)({'|'.join([f'({re.escape(trigger)}+)' for trigger in self.triggers])})(?!\w)"
        )

    async def get_rep(self, member):
        query = {"_id": {"id": member.id, "guild_id": member.guild.id}}
        entry = await self.bot.mongo.db.member.find_one_and_update(
            query, {"$setOnInsert": query}, upsert=True, return_document=True
        )

        rep = entry.get("reputation", 0)
        rank = await self.bot.mongo.db.member.count_documents(
            {
                "_id": {"id": {"$ne": member.id}, "guild_id": member.guild.id},
                "reputation": {"$gt": rep},
            }
        )
        return rep, rank

    async def update_rep(self, member, *, set=None, inc=None):
        if set is None and inc is None:
            raise ValueError("Either 'set' or 'inc' must be provided.")

        update = {}
        if set:
            update["$set"] = {"reputation": set}
        if inc:
            update["$inc"] = {"reputation": inc}

        query = {"_id": {"id": member.id, "guild_id": member.guild.id}}
        await self.bot.mongo.db.member.update_one(query, update, upsert=True)

    async def process_giverep(self, ctx, member):
        if member.bot:
            return "You can't give rep to a bot user!"

        if member.id == ctx.author.id:
            return "You can't give rep to yourself!"

        cd = await self.bot.redis.pttl(key := f"rep:{ctx.guild.id}:{ctx.author.id}")
        if cd >= 0:
            return f"You're on cooldown! Try again in {human_timedelta(timedelta(seconds=cd / 1000))}."

        user_cd = await self.bot.redis.pttl(
            user_key := f"rep:{ctx.guild.id}:{ctx.author.id}:{member.id}"
        )
        if user_cd >= 0:
            return f"You can rep **{member}** again in {human_timedelta(timedelta(seconds=user_cd / 1000))}."

        await self.bot.redis.set(key, 1, expire=120)
        await self.bot.redis.set(user_key, 1, expire=3600)
        await self.update_rep(member, inc=1)
        await ctx.send(f"Gave 1 rep to **{member}**.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or len(message.mentions) == 0:
            return

        match = self.regex.search(message.content.casefold())
        if match:
            ctx = await self.bot.get_context(message)
            await self.process_giverep(ctx, message.mentions[0])

    @commands.hybrid_command(cooldown_after_parsing=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.guild_only()
    async def rep(self, ctx, *, member: discord.Member = commands.Author):
        """Shows the reputation of a given user.

        Parameters:
        ------------
        member: `Member`
            The member whose reputation you want to check.
        """

        rep, rank = await self.get_rep(member)

        embed = discord.Embed(color=discord.Color.purple())
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.add_field(name="Reputation", value=str(rep))
        embed.add_field(name="Rank", value=str(rank + 1))
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["gr"], cooldown_after_parsing=True)
    @commands.cooldown(1, 120, commands.BucketType.user)
    @commands.guild_only()
    async def giverep(self, ctx, *, member: discord.Member):
        """Gives a reputation point to a user.

        Parameters:
        ------------
        member: `Member`
            The member to give reputation to.
        """

        if message := await self.process_giverep(ctx, member):
            ctx.command.reset_cooldown(ctx)
            raise commands.BadArgument(message)

    @commands.hybrid_command()
    @checks.is_admin()
    async def setrep(self, ctx, member: discord.Member, value: int):
        """Sets a user's reputation to a given value.

        Parameters:
        ------------
        member: `Member`
            The member whose reputation will be set.
        value: `int`
            The reputation value to set for the member.
        """

        await self.update_rep(member, set=value)

        embed = Embed(f"Set **{member}**'s rep to `{value}`.", style="✔️")
        await ctx.send(embed=embed)

    @commands.hybrid_command(cooldown_after_parsing=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def toprep(self, ctx):
        """Displays the server reputation leaderboard."""

        query = {"_id.guild_id": ctx.guild.id, "reputation": {"$gt": 0}}
        users = self.bot.mongo.db.member.find(query).sort("reputation", -1)
        count = await self.bot.mongo.db.member.count_documents(query)

        def format_entry(x):
            user = self.bot.get_user(x["_id"]["id"]) or FakeUser(x["_id"]["id"])
            return str(x["reputation"]), "-", str(user)

        def format_embed(e):
            e.description += f"\nUse `{ctx.clean_prefix}rep` to view your reputation, and `{ctx.clean_prefix}giverep` to give rep to others."

        paginator = Paginator(
            source=CodeBlockTablePageSource(
                users,
                color=discord.Color.purple(),
                count=count,
                title="Reputation Leaderboard",
                icon_url=ctx.guild.icon.url,
                format_entry=format_entry,
                format_embed=format_embed,
            )
        )

        try:
            await paginator.start(ctx)
        except IndexError:
            raise commands.BadArgument("No users found.")


async def setup(bot):
    await bot.add_cog(Reputation(bot))
