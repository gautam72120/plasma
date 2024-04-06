from typing import Literal

import discord


class Check:
    style = "✔️"
    color = discord.Color.green()
    emoji = "<:_:1223561046954872872>"


class Cross:
    style = "❌"
    color = discord.Color.red()
    emoji = "<:_:1223558879795744768>"


EmbedStyle = Literal["✔️", "❌"]


class Embed(discord.Embed):
    def __init__(self, message, *, style: EmbedStyle):
        map = {x.style: x for x in (Check, Cross)}
        cls = map[style]
        super().__init__(color=cls.color, description=f"{cls.emoji} {message}")
