import asyncio
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import NamedTuple

import discord
from discord.ext import commands

from helpers.converters import TimeConverter
from helpers.embeds import Embed
from helpers.formats import human_timedelta
from helpers.pagination import FieldsPageSource, Paginator
from helpers.utils import FakeUser


@dataclass
class Reminder:
    message: str
    user_id: int
    channel_id: int
    message_id: int
    created_at: datetime
    expires_at: datetime
    _id: int = None

    @property
    def user(self):
        return self.bot.get_user(self.user_id) or FakeUser(self.user_id)

    @property
    def duration(self):
        return self.expires_at - self.created_at

    @classmethod
    def build_from_mongo(cls, reminder):
        return cls(**reminder)

    def to_dict(self):
        return asdict(self)


class DispatchedReminder(NamedTuple):
    reminder: Reminder
    task: asyncio.Task


class Reminders(commands.Cog):
    """For reminders."""

    def __init__(self, bot):
        self.bot = bot
        self._current = None
        bot.loop.create_task(self.update_current())

    def clear_current(self):
        if self._current and not self._current.task.done():
            self._current.task.cancel()
            self._current = None

    async def get_next_reminder(self):
        reminder = await self.bot.mongo.db.reminder.find_one(sort=(("expires_at", 1),))
        return Reminder.build_from_mongo(reminder) if reminder else None

    async def update_current(self, reminder=None):
        await self.bot.wait_until_ready()

        reminder = reminder or await self.get_next_reminder()
        if reminder is None:
            return

        if self._current and not self._current.task.done():
            if reminder.expires_at > self._current.reminder.expires_at:
                return
            self.clear_current()

        self._current = DispatchedReminder(
            reminder=reminder,
            task=self.bot.loop.create_task(self.dispatch_reminder(reminder)),
        )

    async def dispatch_reminder(self, reminder):
        try:
            await discord.utils.sleep_until(reminder.expires_at)
        except asyncio.CancelledError:
            return

        await self.bot.mongo.db.reminder.delete_one({"_id": reminder._id})
        mention = None

        try:
            channel = await self.bot.fetch_channel(reminder.channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

        if channel:
            try:
                message = await channel.fetch_message(reminder.message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                mention = reminder.user.mention
                message = None

            if isinstance(channel, discord.DMChannel):
                mention = None

            embed = discord.Embed(
                color=discord.Color.teal(),
                title="Reminder",
                description=reminder.message,
                timestamp=reminder.expires_at,
            )
            await channel.send(mention, embed=embed, reference=message)

        self.bot.loop.create_task(self.update_current())

    @commands.hybrid_group(
        aliases=["remind", "remindme"], cooldown_after_parsing=True, fallback="set"
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reminder(self, ctx, time: TimeConverter, *, message):
        """Sets a reminder for a duration of time.

        Parameters:
        ------------
        time: `str`
            The duration after which the reminder should trigger.
        message: `str`
            The message to be displayed when the reminder triggers.

        Examples:
        ----------
        * `?reminder 30m take a break`
        * `?reminder 10h do something`
        """

        reminder = Reminder(
            message=message,
            user_id=ctx.author.id,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            created_at=ctx.message.created_at,
            expires_at=time,
        )

        reminder._id = await self.bot.mongo.reserve_id("reminder")
        await self.bot.mongo.db.reminder.insert_one(reminder.to_dict())

        self.bot.loop.create_task(self.update_current(reminder))

        embed = Embed(
            f"Alright, I'll remind you in {human_timedelta(reminder.duration)}: {message}",
            style="✔️",
        )
        await ctx.send(embed=embed)

    @reminder.command(aliases=["remove"], cooldown_after_parsing=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def delete(self, ctx, ids: commands.Greedy[int]):
        """Deletes one or more reminders by their IDs.

        Parameters:
        ------------
        ids: `int(s)`
            The ID(s) of the reminder(s) to delete.
        """

        result = await self.bot.mongo.db.reminder.delete_many(
            {"_id": {"$in": ids}, "user_id": ctx.author.id}
        )
        if result.deleted_count == 0:
            raise commands.BadArgument("No reminders found.")

        affix = "entry" if result.deleted_count == 1 else "entries"
        embed = Embed(
            f"Successfully deleted `{result.deleted_count}` {affix}.", style="✔️"
        )
        await ctx.send(embed=embed)

        self.clear_current()
        self.bot.loop.create_task(self.update_current())

    @commands.hybrid_command(cooldown_after_parsing=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reminders(self, ctx):
        """Lists all active reminders set by you."""

        query = {"user_id": ctx.author.id}
        count = await self.bot.mongo.db.reminder.count_documents(query)

        async def get_reminders():
            async for reminder in self.bot.mongo.db.reminder.find(query).sort("expires_at", 1):  # type: ignore
                yield Reminder.build_from_mongo(reminder)

        def format_entry(i, x):
            name = f"ID: {x._id} | {discord.utils.format_dt(x.expires_at, 'R')}"
            text = textwrap.shorten(x.message, 512)
            return {"name": name, "value": text, "inline": False}

        paginator = Paginator(
            source=FieldsPageSource(
                get_reminders(),
                color=discord.Color.teal(),
                count=count,
                title="Reminders",
                icon_url=ctx.author.display_avatar.url,
                per_page=5,
                format_entry=format_entry,
            )
        )

        try:
            await paginator.start(ctx)
        except IndexError:
            raise commands.BadArgument("No reminders found.")


async def setup(bot):
    Reminder.bot = bot
    await bot.add_cog(Reminders(bot))
