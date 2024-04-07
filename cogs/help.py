import inspect
import re
from datetime import timedelta

import discord
from discord.ext import commands

from helpers.embeds import Embed
from helpers.formats import human_timedelta
from helpers.pagination import HelpPageSource, Paginator


class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={"help": "Shows all available commands."})

    def command_not_found(self, string):
        return f"No command called `{string}` found."

    async def send_error_message(self, error, *, resolve=False):
        error = self.command_not_found(error) if resolve else error
        embed = Embed(error, style="❌")
        await self.context.send(embed=embed, ephemeral=True)

    def get_examples(self, command):
        docstring = inspect.getdoc(command.callback)
        if docstring is None:
            return None

        pattern = r"Examples:\s*[\n-]+\s*(.*?)(?=Parameters|\Z)"
        matches = re.findall(pattern, docstring, re.DOTALL)
        return "\n".join(matches)

    def make_page_embed(self, commands, *, color, title, description):
        embed = discord.Embed(color=color, title=title, description=description)
        embed.set_footer(
            text=f'Use "{self.context.clean_prefix}help command" for more info on a command.'
        )

        for command in commands:
            name = self.get_command_signature(command)
            help = command.help.splitlines()[0] if command.help else "No help found..."
            embed.add_field(name=name, value=f"`{help}`", inline=False)

        return embed

    async def send_bot_help(self, mapping):
        entries = []

        for cog, commands in mapping.items():
            commands = await self.filter_commands(commands, sort=True)

            if cog is None or len(commands) == 0:
                continue

            entries.append((cog, commands))

        paginator = Paginator(
            source=HelpPageSource(entries, ctx=self.context, color=0xFE9AC9)
        )
        await paginator.start(self.context)

    async def send_cog_help(self, cog):
        commands = await self.filter_commands(cog.get_commands(), sort=True)
        if len(commands) == 0:
            return await self.send_error_message(cog.qualified_name, resolve=True)

        embed = self.make_page_embed(
            commands,
            color=0xFE9AC9,
            title=f"{cog.qualified_name} Commands",
            description=cog.description or "No Description",
        )
        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        commands = await self.filter_commands(subcommands, sort=True)
        if len(commands) == 0:
            return await self.send_error_message(group.qualified_name, resolve=True)

        embed = discord.Embed(
            commands,
            color=0xFE9AC9,
            title=self.get_command_signature(group),
            description=(
                group.help.splitlines()[0] if group.help else "No help found..."
            ),
        )
        if examples := self.get_examples(group):
            embed.description += "\n\n" + f"**Examples**\n{examples}"

        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        async def predicate():
            try:
                return await command.can_run(self.context)
            except commands.CommandError:
                return False

        valid = await predicate()
        if not valid:
            return await self.send_error_message(command.name, resolve=True)

        embed = discord.Embed(
            color=0xFE9AC9,
            title=f"{self.context.clean_prefix}{command.name} {command.signature}",
            description=(
                command.help.splitlines()[0] if command.help else "No help found..."
            ),
        )

        if aliases := command.aliases:
            value = " ".join([f"`{alias}`" for alias in aliases])
            embed.add_field(name="Aliases", value=value, inline=False)

        if cooldown := command.cooldown:
            value = human_timedelta(timedelta(seconds=cooldown.per / cooldown.rate))
            embed.add_field(name="Cooldown", value=value, inline=False)

        if examples := self.get_examples(command):
            embed.add_field(name="Examples", value=examples, inline=False)

        await self.context.send(embed=embed)


async def setup(bot):
    bot.old_help_command = bot.help_command
    bot.help_command = CustomHelpCommand()


async def teardown(bot):
    bot.help_command = bot.old_help_command
    del bot.old_help_command
