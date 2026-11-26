"""Tests for the bot entry point, event handlers and the owner-only ping."""

import os
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

import discord
from discord.ext import commands

from conftest import FakeContext

# Importing main.py starts the bot; patch run() and provide a token first.
with (
    mock.patch.dict(os.environ, {"DISCORD_TOKEN": "test-token"}),
    mock.patch.object(commands.Bot, "run"),
):
    import main


@contextmanager
def bot_property(name, value):
    """Bot.user/guilds are read-only properties, so patch them on the class."""
    with mock.patch.object(type(main.bot), name, new_callable=mock.PropertyMock, return_value=value):
        yield


def bot_user(user):
    return bot_property("user", user)


def test_bot_configuration():
    assert main.bot.command_prefix == "m!"
    assert main.bot.help_command is None
    assert list(main.bot.owner_ids) == [336475402535174154, 311117384951791618]


class TestOnMessage:
    async def test_ignores_messages_from_bots(self):
        message = SimpleNamespace(author=SimpleNamespace(bot=True))
        with (
            bot_user(SimpleNamespace(bot=True)),
            mock.patch.object(main.bot, "process_commands", new_callable=mock.AsyncMock) as process,
        ):
            await main.on_message(message)
        process.assert_not_awaited()

    async def test_ignores_messages_from_self(self):
        bot_user_instance = SimpleNamespace(bot=False)
        message = SimpleNamespace(author=bot_user_instance)
        with (
            bot_user(bot_user_instance),
            mock.patch.object(main.bot, "process_commands", new_callable=mock.AsyncMock) as process,
        ):
            await main.on_message(message)
        process.assert_not_awaited()

    async def test_processes_commands_from_users(self):
        message = SimpleNamespace(author=SimpleNamespace(id=2, bot=False))
        with (
            bot_user(SimpleNamespace(id=1, bot=False)),
            mock.patch.object(main.bot, "process_commands", new_callable=mock.AsyncMock) as process,
        ):
            await main.on_message(message)
        process.assert_awaited_once_with(message)


class TestOnReady:
    async def test_sets_listening_activity(self):
        guilds = [SimpleNamespace(name="Guild One"), SimpleNamespace(name="Guild Two")]
        with (
            bot_user("MCPedia#0001"),
            bot_property("guilds", guilds),
            mock.patch.object(main.bot, "change_presence", new_callable=mock.AsyncMock) as change_presence,
        ):
            await main.on_ready()
        activity = change_presence.await_args.kwargs["activity"]
        assert activity.type == discord.ActivityType.listening
        assert activity.name == "/help"


class TestPing:
    async def test_ping_sends_pong(self):
        ctx = FakeContext()
        await main.bot.get_command("ping").callback(ctx)
        assert ctx.calls_named("send")[0][1][0] == "Pong!"
