"""Tests for the brewing reference command."""

import discord

from cogs import brewing
from conftest import FakeContext


async def test_brewing_sends_reference_image(ctx):
    await brewing.Brewing.brewing.callback(brewing.Brewing(None), ctx)
    embed = ctx.embed
    assert embed.color == discord.Color.purple()
    assert embed.image.url == "https://minecraft.wiki/images/Minecraft_brewing_en.png"
    assert len(ctx.calls_named("respond")) == 1
