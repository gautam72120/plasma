import discord
from discord.ext import menus
from discord.ext.menus.views import ViewMenuPages


class AsyncEmbedPageSource(menus.AsyncIteratorPageSource):
    def __init__(
        self,
        iterator,
        *,
        color,
        count,
        title,
        icon_url,
        per_page=20,
        delimiter="\n",
        format_index=True,
        format_entry=None,
        format_embed=None,
    ):
        super().__init__(iterator, per_page=per_page)
        self.color = color
        self.count = count
        self.title = title
        self.icon_url = icon_url
        self.delimiter = delimiter
        self.format_index = format_index
        self.format_entry = format_entry
        self.format_embed = format_embed

    async def format_page(self, menu, page):
        start = menu.current_page * self.per_page
        embed = discord.Embed(color=self.color)
        embed.set_author(name=self.title, icon_url=self.icon_url)
        embed.set_footer(
            text=f"Showing entries {start + 1}–{start + len(page)} out of {self.count}"
        )
        return start, embed


class CodeBlockTablePageSource(AsyncEmbedPageSource):
    def justify(self, string, width):
        return string.rjust(width) if string.isdigit() else string.ljust(width)

    async def format_page(self, menu, page):
        start, embed = await super().format_page(menu, page)

        table = [
            (
                (f"{i+1}.", *self.format_entry(x))
                if self.format_index
                else self.format_entry(x)
            )
            for i, x in enumerate(page, start=start)
        ]
        width = [max(len(x) for x in column) for column in zip(*table)]
        lines = [
            " ".join(self.justify(x, width[i]) for i, x in enumerate(line)).rstrip()
            for line in table
        ]

        embed.description = "```" + self.delimiter.join(lines) + "```"
        self.format_embed(embed)
        return embed


class FieldsPageSource(AsyncEmbedPageSource):
    async def format_page(self, menu, page):
        start, embed = await super().format_page(menu, page)

        for i, x in enumerate(page, start=start):
            embed.add_field(**self.format_entry(i, x))

        return embed


class ListPageSource(AsyncEmbedPageSource):
    async def format_page(self, menu, page):
        start, embed = await super().format_page(menu, page)

        lines = [
            f"{i+1}. {x}" if self.format_index else str(x)
            for i, x in enumerate(page, start=start)
        ]
        embed.description = self.delimiter.join(lines)
        return embed


class HelpPageSource(menus.ListPageSource):
    def __init__(self, entries, *, ctx, color, per_page=6):
        super().__init__(entries, per_page=per_page)
        self.ctx = ctx
        self.color = color

    async def format_page(self, menu, page):
        embed = discord.Embed(
            color=self.color,
            title=f"Command Categories (Page {menu.current_page + 1}/{self.get_max_pages()})",
            description=(
                f"Use `{self.ctx.clean_prefix}help <command>` for more info on a command.\n"
                f"Use `{self.ctx.clean_prefix}help <category>` for more info on a category."
            ),
        )

        for cog, commands in page:
            filtered = " ".join([f"`{command.name}`" for command in commands])
            embed.add_field(
                name=cog.qualified_name,
                value=f"{cog.description or 'No Description'}\n{filtered}",
                inline=False,
            )

        return embed


class Paginator(ViewMenuPages):
    REMOVE_BUTTONS = [
        "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        "\N{BLACK SQUARE FOR STOP}\ufe0f",
    ]

    def __init__(self, source, *, timeout=120, **kwargs):
        super().__init__(source, timeout=timeout, clear_reactions_after=True, **kwargs)
        for x in self.REMOVE_BUTTONS:
            self.remove_button(x)

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(self.current_page)
        keys = await self._get_kwargs_from_page(page)
        return await self.send_with_view(ctx, **keys)
