import aioredis

from discord.ext import commands


class Redis(commands.Cog):
    """For managing redis operations."""

    def __init__(self, bot):
        self.bot = bot
        self._pool = None
        self._task = bot.loop.create_task(self.connect())

    async def connect(self):
        await self.bot.wait_until_ready()
        self._pool = await aioredis.create_redis_pool(self.bot.config.REDIS_URI)

    async def close(self):
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()

    async def cog_unload(self):
        self.bot.loop.create_task(self.close())


async def setup(bot):
    await bot.add_cog(Redis(bot))
