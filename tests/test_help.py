"""Tests for the help/about commands and their embed delivery fallback."""

from types import SimpleNamespace

import discord
from discord.commands import slash_command
from discord.errors import Forbidden
from discord.ext import commands

from cogs import help_command


def forbidden():
    return Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "Missing Permissions")


def make_slash_command(name, description="A slash command", command_id=123):
    @slash_command(name=name, description=description)
    async def command(ctx):
        pass

    command.id = command_id
    command.cog = None
    return command


def make_text_command(name, brief="A text command", hidden=False):
    @commands.command(name=name, brief=brief, hidden=hidden)
    async def command(ctx):
        pass

    command.cog = None
    return command


class FakeCog:
    """Description used by the help embed."""

    def __init__(self, cog_commands):
        self.cog_commands = cog_commands

    def get_commands(self):
        return self.cog_commands


def make_bot(cogs=None, app_commands=None, text_commands=None, owner_ids=None):
    cogs = cogs or {}
    return SimpleNamespace(
        cogs=cogs,
        owner_ids=owner_ids if owner_ids is not None else {42},
        get_cog=lambda name: cogs[name],
        walk_application_commands=lambda: app_commands or [],
        walk_commands=lambda: text_commands or [],
    )


class TestSendEmbed:
    async def test_sends_embed_directly(self, ctx):
        embed = discord.Embed(title="Help")
        await help_command.send_embed(ctx, embed)
        assert ctx.calls_named("respond")[0][2]["embed"] is embed
        assert not ctx.calls_named("send")

    async def test_falls_back_to_plain_message(self, ctx):
        async def fail(*args, **kwargs):
            raise forbidden()

        ctx.respond = fail
        await help_command.send_embed(ctx, discord.Embed(title="Help"))
        assert ctx.calls_named("send")[0][1][0] == "I can't send embeds. Check my pemissions"

    async def test_falls_back_to_author_dm(self, ctx):
        async def fail(*args, **kwargs):
            raise forbidden()

        ctx.respond = fail
        ctx.send = fail
        ctx.author.send = _RecordingSend()
        embed = discord.Embed(title="Help")
        await help_command.send_embed(ctx, embed)
        assert "channel general" in ctx.author.send.args[0]
        assert "Test Guild" in ctx.author.send.args[0]
        assert ctx.author.send.kwargs["embed"] is embed


class _RecordingSend:
    def __init__(self):
        self.args = ()
        self.kwargs = {}

    async def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class TestHelpSlash:
    async def test_lists_cogs_commands_and_hidden_commands_for_owner(self, ctx):
        cog_commands = [
            make_slash_command("wiki", "Search the wiki"),
            make_text_command("ping", "Test connection", hidden=True),
        ]
        bot = make_bot(
            cogs={"TestCog": FakeCog(cog_commands)},
            app_commands=[make_slash_command("about", "About the bot")],
            text_commands=[make_text_command("hidden", "Hidden", hidden=True)],
        )
        cog = help_command.Help(bot)
        await help_command.Help.help_slash.callback(cog, ctx, None)
        embed = ctx.embed
        assert "All commands" in embed.title
        assert "Category TestCog" in [field.name for field in embed.fields]
        assert "No category" in [field.name for field in embed.fields]
        all_values = "\n".join(field.value for field in embed.fields)
        assert "</wiki:123> - Search the wiki" in all_values
        assert "`m!ping`" in all_values
        assert "`m!hidden`" in all_values
        assert "Version 2.5" in embed.footer.text

    async def test_hides_owner_only_commands_from_other_users(self, ctx):
        ctx.author.id = 7
        bot = make_bot(
            cogs={"TestCog": FakeCog([make_text_command("ping", hidden=True)])},
            text_commands=[make_text_command("hidden", hidden=True)],
        )
        await help_command.Help.help_slash.callback(help_command.Help(bot), ctx, None)
        assert ctx.embed.fields == []

    async def test_cog_lookup_by_name(self, ctx):
        bot = make_bot(cogs={"TestCog": FakeCog([make_slash_command("wiki", "Search the wiki")])})
        await help_command.Help.help_slash.callback(help_command.Help(bot), ctx, "testcog")
        embed = ctx.embed
        assert embed.title == "TestCog - Commands"
        assert embed.description == "Description used by the help embed."
        assert "</wiki:123>" in embed.fields[0].name

    async def test_unknown_command(self, ctx):
        bot = make_bot()
        await help_command.Help.help_slash.callback(help_command.Help(bot), ctx, "doesnotexist")
        assert ctx.embed.title == "What's that?!"
        assert "doesnotexist" in ctx.embed.description


class TestAboutSlash:
    async def test_about_embed(self, ctx):
        await help_command.Help.about_slash.callback(help_command.Help(make_bot()), ctx)
        embed = ctx.embed
        assert embed.title == ":sparkles: __About MCPedia__ :sparkles:"
        assert "Minecraft Wiki" in embed.description
        assert embed.footer.text == "Made by malpkakefirek"
