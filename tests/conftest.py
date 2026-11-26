"""Shared setup and fakes for the MCPedia unit tests.

The bot cogs talk to the Minecraft Wiki at import time (``cogs.villager``
fetches the villager list on module load) and read JSON data files relative to
the working directory.  Importing them under patched MediaWiki methods and
from the repository root keeps the test suite offline and deterministic.
"""

import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import mediawiki
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


_FAKE_TOC = {
    "Non-trading villagers": {},
    "Trade offers": {"Armorer": [], "Librarian": []},
    "Wandering trader sales": {"Java Edition sales": []},
}
_FAKE_PAGE = SimpleNamespace(
    title="Trading",
    html="<html></html>",
    content="Trading content",
    sections=list(_FAKE_TOC),
    table_of_contents=_FAKE_TOC,
    summarize=mock.Mock(return_value="Trading summary"),
    section=mock.Mock(return_value=""),
)

# Both patches are active only while the cogs are imported below.
with (
    mock.patch.object(mediawiki.MediaWiki, "search", return_value=["Trading"]),
    mock.patch.object(mediawiki.MediaWiki, "page", return_value=_FAKE_PAGE),
):
    for _module in (
        "cogs.brewing",
        "cogs.crafting",
        "cogs.enchants",
        "cogs.help_command",
        "cogs.tools",
        "cogs.villager",
        "cogs.wiki",
    ):
        importlib.import_module(_module)


class CallRecorder:
    """Stores ``(name, args, kwargs)`` for every recorded async call."""

    def __init__(self):
        self.calls = []

    def record(self, name, args, kwargs):
        self.calls.append((name, args, kwargs))

    def calls_named(self, name):
        return [call for call in self.calls if call[0] == name]


class FakeMessage:
    """Minimal stand-in for a Discord message returned by a response."""

    def __init__(self, content=None, embed=None, **kwargs):
        self.content = content
        self.embed = embed
        self._recorder = CallRecorder()
        self.edits = self._recorder
        self.deleted = False

    async def edit(self, content=None, embed=None, **kwargs):
        self._recorder.record("edit", (), {"content": content, "embed": embed, **kwargs})
        if content is not None:
            self.content = content
        if embed is not None:
            self.embed = embed

    async def delete(self):
        self._recorder.record("delete", (), {})
        self.deleted = True

    def calls_named(self, name):
        return self._recorder.calls_named(name)


class FakeInteraction:
    """Fake slash-command interaction with recorded responses."""

    def __init__(self, user=None, message=None, values=None):
        self.user = user or SimpleNamespace(id=42, name="tester")
        self.message = message or FakeMessage()
        self.values = values or []
        self._recorder = CallRecorder()
        self.response = SimpleNamespace(
            defer=_async_record(self._recorder, "response.defer"),
            edit_message=_async_record(self._recorder, "response.edit_message"),
        )
        self.followup = SimpleNamespace(send=_async_record(self._recorder, "followup.send"))
        self.respond = _async_record(self._recorder, "respond")
        self.edit = _async_record(self._recorder, "edit")
        self.original_response = _async_record(self._recorder, "original_response")
        self.edit_original_response = _async_record(self._recorder, "edit_original_response")

    @property
    def calls(self):
        return self._recorder.calls

    def calls_named(self, name):
        return self._recorder.calls_named(name)


def _async_record(recorder, name):
    async def method(*args, **kwargs):
        recorder.record(name, args, kwargs)
        return FakeMessage(content=kwargs.get("content"), embed=kwargs.get("embed"))

    return method


class FakeContext:
    """Fake application-command context that captures every response."""

    def __init__(self, user=None, channel=None, guild=None):
        self.user = user or SimpleNamespace(id=42, name="tester")
        self.author = self.user
        self.channel = channel or SimpleNamespace(name="general")
        self.guild = guild or SimpleNamespace(name="Test Guild")
        self._recorder = CallRecorder()
        self.defer = _async_record(self._recorder, "defer")
        self.respond = _async_record(self._recorder, "respond")
        self.send = _async_record(self._recorder, "send")

    @property
    def calls(self):
        return self._recorder.calls

    def calls_named(self, name):
        return self._recorder.calls_named(name)

    @property
    def embed(self):
        for _, _, kwargs in self.calls_named("respond"):
            if kwargs.get("embed") is not None:
                return kwargs["embed"]
        return None

    @property
    def response_content(self):
        for _, args, kwargs in self.calls_named("respond"):
            if args:
                return args[0]
            if kwargs.get("content") is not None:
                return kwargs["content"]
        return None


def make_page(
    title="Test Page",
    summary="A short summary",
    sections=None,
    toc=None,
    html="<html></html>",
    content="Page content",
):
    """Build a fake MediaWiki page with a configurable table of contents."""

    sections = sections or {}
    toc = toc if toc is not None else {name: [] for name in sections}
    return SimpleNamespace(
        title=title,
        html=html,
        content=content,
        sections=list(toc),
        table_of_contents=toc,
        summarize=mock.Mock(return_value=summary),
        section=mock.Mock(side_effect=lambda name: sections.get(name, "")),
    )


@pytest.fixture
def ctx():
    return FakeContext()


@pytest.fixture
def interaction():
    return FakeInteraction()
