from datetime import timedelta

import discord
from discord.ext import commands

from helpers.embeds import Embed
from helpers.formats import human_timedelta


class Bot(commands.Cog):
    """For basic bot operations."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.content != before.content:
            await self.bot.process_commands(after)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send_help(ctx.command)

        if isinstance(error, commands.BotMissingPermissions):
            missing = [
                "`" + perm.replace("_", " ").replace("guild", "server").title() + "`"
                for perm in error.missing_permissions
            ]
            fmt = "\n".join(missing)
            msg = f"💥 Err, I need the following permissions to run this command:\n{fmt}\nPlease fix this and try again."

            try:
                return await ctx.send(msg, ephemeral=True)
            except discord.Forbidden:
                return await ctx.author.send(msg)

        if isinstance(error, commands.CommandOnCooldown):
            embed = Embed(
                f"You're on cooldown! Try again in {human_timedelta(timedelta(seconds=error.retry_after))}.",
                style="❌",
            )
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, commands.ConversionError):
            embed = Embed(str(error.original), style="❌")
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, (commands.UserInputError, commands.CheckFailure)):
            embed = Embed(str(error), style="❌")
            return await ctx.send(embed=embed, ephemeral=True)

        if isinstance(error, commands.CommandNotFound):
            return

    @commands.Cog.listener()
    async def on_error(self, event, error):
        if isinstance(error, discord.NotFound):
            return

    @commands.hybrid_command(cooldown_after_parsing=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ping(self, ctx):
        """Checks the bot's latency."""

        message = await ctx.send("Pong!")
        seconds = (message.created_at - ctx.message.created_at).total_seconds()
        await message.edit(content=f"Pong! **{seconds * 1000:.0f} ms**")

    @discord.app_commands.command()
    async def help(self, interaction, *, command: str | None = None):
        """Shows all available commands.

        Parameters:
        ------------
        command: `str | None`
            The command to get help for.
        """

        ctx = await self.bot.get_context(interaction)

        if command:
            cmd = self.bot.get_command(command)
            cog = self.bot.get_cog(command)

            if cmd or cog:
                await ctx.send_help(command)
            else:
                embed = Embed(f"No command called `{command}` found.", style="❌")
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx.send_help()

    @help.autocomplete("command")
    async def command_autocomplete(self, interaction, current):
        ctx = await self.bot.get_context(interaction)

        async def predicate(cmd):
            try:
                return await cmd.can_run(ctx)
            except commands.CommandError:
                return False

        options = sorted(self.bot.commands, key=lambda c: c.name)
        options = [cmd.name for cmd in options if await predicate(cmd)]
        choices = [
            discord.app_commands.Choice(name=option, value=option)
            for option in options
            if current.casefold() in option.casefold()
        ]
        return choices[:25]


async def setup(bot):
    await bot.add_cog(Bot(bot))
