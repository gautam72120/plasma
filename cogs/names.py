import re
import string
import unidecode

from discord.ext import commands


class Names(commands.Cog):
    """For normalizing usernames."""

    def __init__(self, bot):
        self.bot = bot
        self.regex = re.compile(
            r"(([a-z]{3,6}://)|(^|\s))([a-zA-Z0-9\-]+\.)+[a-z]{2,13}[\.\?\=\&\%\/\w\-]*\b([^@]|$)"
        )

    def normalize(self, text):
        if text is None:
            return None

        text = unidecode.unidecode(text)
        text = re.sub(self.regex, "", text)
        text = text.lstrip(string.punctuation + string.whitespace)

        if len(text) == 0:
            return None
        return text[:32]

    async def normalize_member(self, member):
        if member.bot:
            return

        normalized = (
            self.normalize(member.nick) or self.normalize(member.name) or "User"
        )
        if normalized != member.display_name:
            await member.edit(nick=normalized)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.normalize_member(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if after.nick != before.nick:
            await self.normalize_member(after)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if after.name == before.name:
            return

        for guild in self.bot.guilds:
            if member := guild.get_member(after.id):
                await self.normalize_member(member)


async def setup(bot):
    await bot.add_cog(Names(bot))
