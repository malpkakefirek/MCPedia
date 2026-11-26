"""Tests for villager autocomplete, trade parsing and slash commands."""

import json
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest

from cogs import villager
from conftest import make_page


TRADING_HTML = """
<h3><span>Armorer</span></h3>
<p>Works at a <a title="Blast Furnace">Blast Furnace</a>.</p>
<div>
  <table>
    <th>Level</th>
    <tbody>
      <tr><th>header</th><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td></tr>
      <tr><th>header</th><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td></tr>
      <tr><th>header</th><td>a</td><td>b</td><td>c</td><td>d</td><td>e</td></tr>
      <tr><th>Novice</th><td>a</td><td>b</td><td>36 Emerald [t 1]</td><td>Iron Helmet</td><td>12</td></tr>
    </tbody>
  </table>
</div>
"""

ITEM_SEARCH_HTML = """
<table>
  <tr><th data-description="Armorer">Armorer</th></tr>
  <tr><td>1</td><td>2</td><td>Emerald [t 1]</td><td>Iron Helmet</td><td>12</td></tr>
</table>
"""


class TestAutocomplete:
    async def test_filters_professions_case_insensitively(self):
        with mock.patch.object(villager, "professions_list", ["Armorer", "Librarian", "Nitwit"]):
            result = await villager.villagers(type("Ctx", (), {"value": "arm"})())
        assert result == ["Armorer"]

    async def test_no_match_returns_empty_list(self):
        with mock.patch.object(villager, "professions_list", ["Armorer"]):
            result = await villager.villagers(type("Ctx", (), {"value": "zzz"})())
        assert result == []


class TestGenerateUrl:
    def test_encodes_table_data_and_options(self):
        url = villager.generate_url("Trades", ["Level"], [["-", {"level": "Novice"}]])
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "api.quickchart.io"
        assert parsed.path == "/v1/table"
        query = parse_qs(parsed.query)
        data = json.loads(query["data"][0])
        assert data == {"title": "Trades", "columns": ["Level"], "dataSource": [["-", {"level": "Novice"}]]}
        assert "#59b731" in query["options"][0]


class TestVillagerInfo:
    async def test_extracts_trades_and_job_site(self):
        page = make_page(html=TRADING_HTML)
        with (
            mock.patch.object(villager, "wikipedia") as wikipedia,
            mock.patch.object(villager.requests, "get", return_value=mock.Mock(content=b"png")) as request,
        ):
            wikipedia.search.return_value = ["Trading"]
            wikipedia.page.return_value = page
            file, job_site = await villager.villager_info("Armorer")
        assert job_site == "Blast Furnace"
        assert file.filename == "villager_trade.png"
        data = json.loads(parse_qs(urlparse(request.call_args.args[0]).query)["data"][0])
        assert data["title"] == "Level"
        assert data["dataSource"][0] == "-"
        trade = data["dataSource"][1]
        assert trade["level"] == "Novice"
        assert trade["0"].strip() == "36 Emerald"
        assert trade["1"] == "Iron Helmet"
        assert trade["2"] == "12"

    async def test_current_heading_markup(self):
        html = """
        <div class="mw-heading mw-heading3"><h3 id="Armorer">Armorer</h3></div>
        <figure>An armorer.</figure>
        <p>Armorers need a <a title="Armorer" href="/w/Armorer">job</a> and
        a <a title="Blast Furnace" href="/w/Blast_Furnace">Blast Furnace</a>.</p>
        <table><th>Level</th><tbody>
          <tr><th>Level</th><th>Probability</th></tr>
          <tr><th>JE</th><th>BE</th></tr>
          <tr><th>Novice</th><td>40%</td><td>100%</td><td>Coal</td><td>Emerald</td><td>16</td></tr>
        </tbody></table>
        """
        page = make_page(html=html)
        with (
            mock.patch.object(villager, "wikipedia") as wikipedia,
            mock.patch.object(villager.requests, "get", return_value=mock.Mock(content=b"png")) as request,
        ):
            wikipedia.search.return_value = ["Trading"]
            wikipedia.page.return_value = page
            file, job_site = await villager.villager_info("Armorer")
        assert file.filename == "villager_trade.png"
        assert job_site == "Blast Furnace"
        data = json.loads(parse_qs(urlparse(request.call_args.args[0]).query)["data"][0])["dataSource"]
        assert data[1]["level"] == "Novice"
        assert data[1]["2"] == "16"

    async def test_unknown_profession_returns_no_result(self):
        with mock.patch.object(villager, "wikipedia") as wikipedia:
            wikipedia.search.return_value = ["Trading"]
            wikipedia.page.return_value = make_page(html=TRADING_HTML)
            assert await villager.villager_info("Missing") == (None, None)


class TestVillagerCommand:
    async def test_unknown_profession(self, ctx):
        with mock.patch.object(villager, "professions_list", ["Armorer"]):
            await villager.Villager.villager.callback(villager.Villager(None), ctx, "Wizard")
        assert ctx.response_content == (
            "Couldn't find `Wizard`! Make sure to choose from the autocomplete list."
        )
        assert not ctx.calls_named("defer")

    @pytest.mark.parametrize("profession", ["Nitwit", "Unemployed villager"])
    async def test_professions_without_trades(self, ctx, profession):
        with mock.patch.object(villager, "professions_list", [profession]):
            await villager.Villager.villager.callback(villager.Villager(None), ctx, profession)
        assert ctx.response_content == f"`{profession}` doesn't have any trades :("
        assert not ctx.calls_named("defer")

    async def test_valid_profession_sends_trades(self, ctx):
        with (
            mock.patch.object(villager, "professions_list", ["Armorer"]),
            mock.patch.object(villager, "villager_info", return_value=(object(), "Blast Furnace")),
        ):
            await villager.Villager.villager.callback(villager.Villager(None), ctx, "Armorer")
        assert ctx.calls_named("defer")
        assert ctx.response_content == '## Armorer\nArmorer needs "Blast Furnace"'
        assert ctx.calls_named("respond")[0][2]["file"] is not None


class TestItemCommand:
    async def test_finds_villager_trading_an_item(self, ctx):
        page = make_page(html=ITEM_SEARCH_HTML, toc={"Trade offers": ["Armorer"]})
        with mock.patch.object(villager, "wikipedia") as wikipedia:
            wikipedia.search.return_value = ["Trading"]
            wikipedia.page.return_value = page
            await villager.Villager.item.callback(villager.Villager(None), ctx, "iron helmet")
        embed = ctx.embed
        assert embed.title == "Here are your matches for `iron helmet`"
        assert "**Armorer** trades `Iron Helmet`" in embed.description
        view = ctx.calls_named("respond")[0][2]["view"]
        assert len(view.children) == 1
        assert view.children[0].name == "Armorer"

    async def test_no_matches(self, ctx):
        page = make_page(html=ITEM_SEARCH_HTML, toc={"Trade offers": ["Armorer"]})
        with mock.patch.object(villager, "wikipedia") as wikipedia:
            wikipedia.search.return_value = ["Trading"]
            wikipedia.page.return_value = page
            await villager.Villager.item.callback(villager.Villager(None), ctx, "diamond")
        assert ctx.embed.title == "Couldn't find a villager that has a trade using `diamond`"
