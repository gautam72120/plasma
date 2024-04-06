import re
from dateutil.relativedelta import relativedelta

import discord
from discord.ext import commands


class BanConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await ctx.guild.fetch_ban(discord.Object(int(argument)))
        except discord.NotFound:
            raise commands.BadArgument("This member is not banned.")
        except ValueError:
            pass

        bans = await ctx.guild.bans()
        user = discord.utils.find(lambda u: str(u.user) == argument, bans)
        if user is None:
            raise commands.BadArgument("This member is not banned.")
        return user


class TimeConverter(commands.Converter):
    regex = re.compile(
        r"""^\s*
            (?:(?P<years>\d+)\s*y(?:ears?)?)?\s*        # e.g. 2y,  2 years
            (?:(?P<months>\d+)\s*mo(?:nths?)?)?\s*      # e.g. 2mo, 2 months
            (?:(?P<weeks>\d+)\s*w(?:eeks?)?)?\s*        # e.g. 10w, 10 weeks
            (?:(?P<days>\d+)\s*d(?:ays?)?)?\s*          # e.g. 14d, 14 days
            (?:(?P<hours>\d+)\s*h(?:ours?)?)?\s*        # e.g. 12h, 12 hours
            (?:(?P<minutes>\d+)\s*m(?:inutes?)?)?\s*    # e.g. 10m, 10 minutes
            (?:(?P<seconds>\d+)\s*s(?:econds?)?)?\s*    # e.g. 15s, 15 seconds
            $
        """,
        re.VERBOSE,
    )

    async def convert(self, ctx, argument):
        match = self.regex.match(argument.casefold())
        if match is None:
            raise commands.BadArgument("Invalid time duration format!")

        values = {k: int(v) for k, v in match.groupdict(default=0).items()}
        return ctx.message.created_at + relativedelta(**values)
