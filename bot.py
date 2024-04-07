import os

import discord
from discord.ext import commands, events
from discord.ext.events import member_kick

import config
from helpers.context import CustomContext


async def determine_prefix(bot, message):
    prefix = await bot.mongo.get_prefix(message.guild)
    prefix = prefix or "?"
    return commands.when_mentioned_or(prefix)(bot, message)


class Bot(commands.Bot, events.EventsMixin):
    def __init__(self):
        super().__init__(
            determine_prefix,
            intents=discord.Intents.all(),
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="/help"
            ),
            case_insensitive=True,
            strip_after_prefix=True,
        )

        self.config = config

    async def setup_hook(self):
        cogs = [
            filename for filename in os.listdir("./cogs") if filename.endswith(".py")
        ]
        for cog in cogs:
            name = f"cogs.{cog[:-3]}"
            await self.load_extension(name)

    @property
    def mongo(self):
        return self.get_cog("Mongo")

    @property
    def redis(self):
        return self.get_cog("Redis")._pool

    async def get_context(self, origin, /, *, cls=CustomContext):
        return await super().get_context(origin, cls=cls)


if __name__ == "__main__":
    bot = Bot()
    bot.run(config.BOT_TOKEN)
