from datetime import timezone
from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient

from discord.ext import commands


class Mongo(commands.Cog):
    """For handling database operations."""

    def __init__(self, bot):
        self.bot = bot
        self._client = AsyncIOMotorClient(bot.config.DATABASE_PATH)

    @property
    def db(self):
        return self._client[self.bot.config.DATABASE_NAME].with_options(
            codec_options=CodecOptions(tz_aware=True, tzinfo=timezone.utc)
        )

    async def get_prefix(self, guild):
        if guild is None:
            return None

        query = {"_id": guild.id}
        entry = await self.db.guild.find_one_and_update(
            query, {"$setOnInsert": query}, upsert=True, return_document=True
        )
        return entry.get("prefix")

    async def reserve_id(self, name):
        entry = await self.db.counter.find_one_and_update(
            {"_id": name}, {"$inc": {"next": 1}}, upsert=True, return_document=True
        )
        return entry["next"]


async def setup(bot):
    await bot.add_cog(Mongo(bot))
