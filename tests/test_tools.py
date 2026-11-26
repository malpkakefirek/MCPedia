"""Tests for the utility functions and slash commands in ``cogs.tools``."""

import json
import uuid
from pathlib import Path
from unittest import mock

import pytest

from cogs import tools
from conftest import FakeContext


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.urls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def get(self, url):
        self.urls.append(url)
        return self.response


def patch_client_session(response):
    session = FakeSession(response)
    return session, mock.patch.object(tools.aiohttp, "ClientSession", return_value=session)


class TestOfflineUuid:
    def test_known_uuid(self):
        result = tools.generate_minecraft_offline_uuid("Notch")
        assert str(result) == "b50ad385-829d-3141-a216-7e7d7539ba7f"
        assert isinstance(result, uuid.UUID)
        assert result.version == 3
        assert result.variant == uuid.RFC_4122

    def test_deterministic_and_case_sensitive(self):
        assert tools.generate_minecraft_offline_uuid("Notch") == tools.generate_minecraft_offline_uuid("Notch")
        assert tools.generate_minecraft_offline_uuid("Notch") != tools.generate_minecraft_offline_uuid("notch")


class TestGetMinecraftProfile:
    async def test_returns_json_for_ok_status(self):
        profile = {"id": "abc123", "name": "Notch"}
        session, patcher = patch_client_session(FakeResponse(200, profile))
        with patcher:
            assert await tools.get_minecraft_profile("Notch") == profile
        assert session.urls == ["https://api.minecraftservices.com/minecraft/profile/lookup/name/Notch"]

    async def test_returns_none_for_missing_profile(self):
        _, patcher = patch_client_session(FakeResponse(404, None))
        with patcher:
            assert await tools.get_minecraft_profile("Nobody") is None


class TestCalculateCommand:
    async def test_calculates_stacks_remainder_and_chests(self):
        ctx = FakeContext()
        await tools.Tools.calculate.callback(tools.Tools(None), ctx, 100, 64)
        embed = ctx.embed
        assert embed.title == "100 items equals to:"
        assert [(field.name, field.value) for field in embed.fields] == [
            ("Stacks (x64)", "1"),
            ("Remaining Items", "36"),
            ("Chests / Shulkers", "0.06"),
            ("Double Chests", "0.03"),
        ]

    async def test_uses_default_stack_size_and_custom_stack_size(self):
        ctx = FakeContext()
        await tools.Tools.calculate.callback(tools.Tools(None), ctx, 32, 16)
        assert [field.value for field in ctx.embed.fields] == ["2", "0", "0.07", "0.04"]


class TestFallCommand:
    @pytest.mark.parametrize(
        ("damage", "height", "expected"),
        [
            (3, 0, "You take 3 damage from these heights:\n6, 6.5"),
            (9, 0, "It's impossible to take 9 damage from falling :("),
            (0, 4.3, "Falling from 4.5 blocks takes 2 damage"),
            (0, 23.5, "Falling from 23.5 blocks takes 20 damage"),
            (0, 1.0, None),
        ],
    )
    async def test_damage_and_height_lookup(self, damage, height, expected):
        ctx = FakeContext()
        await tools.Tools.fall.callback(tools.Tools(None), ctx, damage, height)
        assert ctx.response_content == expected
        assert len(ctx.calls_named("respond")) == (1 if expected else 0)

    @pytest.mark.parametrize(
        ("damage", "height"),
        [(0, 0), (5, 7.5)],
    )
    async def test_requires_exactly_one_input(self, damage, height):
        ctx = FakeContext()
        await tools.Tools.fall.callback(tools.Tools(None), ctx, damage, height)
        assert ctx.response_content == "You have to input one of: damage or height"
        assert ctx.calls_named("respond")[0][2]["ephemeral"] is True

    async def test_fall_data_matches_loaded_json(self):
        data = json.loads((Path(__file__).resolve().parents[1] / "fall_data.json").read_text())
        assert data["20"] == ["23.5"]


class TestUuidCommand:
    async def test_online_profile(self):
        ctx = FakeContext()
        profile = {"id": "b50ad385829d3141a2167e7d7539ba7f", "name": "Notch"}
        with mock.patch.object(tools, "get_minecraft_profile", return_value=profile):
            await tools.Tools.uuid.callback(tools.Tools(None), ctx, "Notch")
        embed = ctx.embed
        assert embed.title == "Notch"
        assert "b50ad385-829d-3141-a216-7e7d7539ba7f" in embed.description
        assert "b50ad385829d3141a2167e7d7539ba7f" in embed.description
        assert embed.thumbnail.url == "https://api.mineatar.io/face/b50ad385829d3141a2167e7d7539ba7f"

    async def test_offline_profile(self):
        ctx = FakeContext()
        with mock.patch.object(tools, "get_minecraft_profile", return_value=None):
            await tools.Tools.uuid.callback(tools.Tools(None), ctx, "Notch")
        embed = ctx.embed
        assert embed.title == "Notch (Offline)"
        assert "Online UUID" not in embed.description
        assert embed.thumbnail.url == "https://api.mineatar.io/face/00000000000000000000000000000000"
