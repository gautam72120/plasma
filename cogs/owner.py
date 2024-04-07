from discord.ext import commands

from helpers.embeds import Embed


class Owner(commands.Cog):
    """For bot owners to manage the bot."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.is_owner()
    async def sync(self, ctx):
        """Syncs application commands with the bot."""

        count = await self.bot.tree.sync()
        embed = Embed(f"Synced `{len(count)}` commands globally.", style="✔️")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Owner(bot))
