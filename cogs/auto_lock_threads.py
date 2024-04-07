import itertools
from collections import defaultdict
from datetime import timedelta

import discord
from discord.ext import commands, tasks


class AutoLockThreads(commands.Cog):
    """For automatically locking threads."""

    def __init__(self, bot):
        self.bot = bot
        self.threads = defaultdict(set)
        self.channels = itertools.cycle([1216779685267112027, 1216792842823794708])
        self.lock_threads.start()

    def clear_warnings(self, thread):
        for time in self.threads:
            self.threads[time].discard(thread.id)

    async def send_warning(self, thread, time):
        if thread.id in self.threads[time]:
            return

        embed = discord.Embed(
            color=discord.Color.yellow(),
            description=f"This thread will be locked in **{time}**.",
        )
        await thread.send(embed=embed)
        self.threads[time].add(thread.id)

    @tasks.loop(seconds=15)
    async def lock_threads(self):
        channel = self.bot.get_channel(next(self.channels))
        if channel is None:
            return

        for thread in channel.threads:
            if thread.flags.pinned:
                continue

            time_left = thread.created_at + timedelta(days=7) - discord.utils.utcnow()

            if time_left < timedelta():
                await thread.edit(archived=True, locked=True)
                self.clear_warnings(thread)

            elif timedelta(hours=23) < time_left < timedelta(days=1):
                await self.send_warning(thread, "24 hours")

            elif time_left < timedelta(hours=1):
                await self.send_warning(thread, "1 hour")

    @lock_threads.before_loop
    async def before_lock_threads(self):
        await self.bot.wait_until_ready()

    async def cog_unload(self):
        self.lock_threads.cancel()


async def setup(bot):
    await bot.add_cog(AutoLockThreads(bot))
