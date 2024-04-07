import itertools
import textwrap
from collections import defaultdict

from discord.ext import commands, tasks


class Post:
    def __init__(self, channels, message, *, each=1):
        self.message = textwrap.dedent(message).strip()
        self.execute = itertools.cycle([True] + [False] * (each - 1))
        self.channels = itertools.cycle(channels)


class AutoPost(commands.Cog):
    """For automatic message posting."""

    posts = [
        Post(
            [1216778836717342870],
            """
            **Reminder:** It is your own responsibility to evaluate trades you make. Once both parties have agreed to and completed a trade, that trade is final. If you change your mind after you make a trade, nothing can nor will be done.
            
            To ensure you get a fair deal, you are highly encouraged to do the following:
            
            * Research trades, market listings, and auctions with similar pokémon from the past.
            * Ask for other trainers' opinions if unsure about the fairness of a trade.
            * Don't give into pressure to buy or sell immediately. You can always try again later.
            """,
            each=6,
        ),
        Post(
            [
                1216779322933776485,  # 💫｜poketwo¹
                1216779541599621220,  # 💫｜poketwo²
                1216792380083015780,  # 🌺｜pokemon¹
                1216792707528265869,  # 🌺｜pokemon²
                1216783608698900590,  # 🦄｜pokecord¹
                1216783653548326952,  # 🦄｜pokecord²
                1216784517134680177,  # 🦄｜pokecord³
                1216784617198194829,  # 🦄｜pokecord⁴
                1216796812132876318,  # 🍃｜deriver¹
                1216796895582883920,  # 🍃｜deriver²
                1216797024159268974,  # 🍃｜deriver³
                1216797096397639761,  # 🍃｜deriver⁴
            ],
            """
            **Reminder:** This channel is for catching only.
           
            * Spamming is not allowed here.
            * Do not run generic bot commands here. Use <#1216778836717342870> instead.
            * Market advertisements are not allowed.
            """,
        ),
    ]

    def __init__(self, bot):
        self.bot = bot
        self.update = defaultdict(bool)
        self.autopost.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.bot.user.id:
            self.update[message.channel.id] = True

    @tasks.loop(minutes=10)
    async def autopost(self):
        for post in self.posts:
            if not next(post.execute):
                continue

            channel_id = next(post.channels)
            if self.update[channel_id]:
                channel = self.bot.get_channel(channel_id)

                if channel:
                    await channel.send(post.message)
                    self.update[channel_id] = False

    @autopost.before_loop
    async def before_autopost(self):
        await self.bot.wait_until_ready()

    async def cog_unload(self):
        self.autopost.cancel()


async def setup(bot):
    await bot.add_cog(AutoPost(bot))
