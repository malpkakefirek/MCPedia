"""Opt-in contract tests against the live Minecraft Wiki API.

These tests hit the real API because the wiki's HTML and section structure
change over time.  Run them explicitly with:

    MCPEDIA_RUN_INTEGRATION=1 pytest -m integration

They are skipped by default so the regular unit suite stays offline.
"""

import os

import pytest
from bs4 import BeautifulSoup
from mediawiki import MediaWiki

from cogs import crafting, villager, wiki

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("MCPEDIA_RUN_INTEGRATION") != "1",
        reason="set MCPEDIA_RUN_INTEGRATION=1 to run tests against the live wiki",
    ),
]

USER_AGENT = "MCPediaDiscordBot/2.5 (https://github.com/malpkakefirek) pymediawiki/0.7.3 integration-tests"


@pytest.fixture(scope="module")
def api():
    return MediaWiki("https://minecraft.wiki/api.php", user_agent=USER_AGENT, timeout=20)


@pytest.fixture(scope="module")
def dirt_page(api):
    return api.page(title="Dirt", auto_suggest=False)


@pytest.fixture(scope="module")
def trading_page(api):
    return api.page(title="Trading", auto_suggest=False)


@pytest.fixture(scope="module")
def stick_page(api):
    return api.page(title="Stick", auto_suggest=False)


class TestWikiApiContracts:
    def test_search_and_page_metadata(self, api, dirt_page):
        assert "Dirt" in api.search("Dirt", results=3)
        assert dirt_page.url == "https://minecraft.wiki/w/Dirt"
        assert dirt_page.summarize()
        assert dirt_page.html

    def test_table_of_contents_is_a_mapping_of_subsections(self, dirt_page):
        toc = dirt_page.table_of_contents
        assert "Obtaining" in toc
        assert "Breaking" in toc["Obtaining"]
        assert all(isinstance(title, str) for title in toc)
        assert all(isinstance(subsections, dict) for subsections in toc.values())

    def test_section_text_can_be_fetched(self, dirt_page):
        # Parent sections such as "Obtaining" only contain subsections, so a
        # leaf section is the meaningful contract for page.section().
        assert "Dirt" in dirt_page.section("Breaking")

    def test_infobox_markup_still_matches_the_embed_builder(self, dirt_page):
        soup = BeautifulSoup(dirt_page.html, "html.parser")
        image_area = soup.find(class_="infobox-imagearea")
        assert image_area is not None
        assert any("File:" in link.get("href", "") for link in image_area.find_all("a"))
        infobox = soup.find(class_="infobox-rows")
        assert infobox is not None
        assert infobox.find("tr").find("th") is not None
        assert infobox.find("tr").find("td") is not None

    # phrase, expected page title, whether an infobox is parsed, whether a
    # thumbnail is found.  These cover disambiguations, mobs, items, blocks,
    # biomes, dimensions, mechanics, people, redstone and command pages.
    @pytest.mark.parametrize(
        ("phrase", "expected_title", "expect_fields", "expect_thumbnail"),
        [
            ("gold", "Disambiguation Error!", None, None),
            ("villager", "Villager", True, True),
            ("ender dragon", "Ender Dragon", True, True),
            ("helmet", "Helmet", True, True),
            ("stairs", "Stairs", False, False),
            ("desert", "Desert", True, True),
            ("nether", "The Nether", False, False),
            ("bartering", "Bartering", False, False),
            ("iron ingot", "Iron Ingot", True, True),
            ("Notch", "Markus Persson", True, True),
            ("redstone clock", "Redstone circuits/Clock", False, False),
            ("inventory", "Inventory", False, False),
            ("/data", "Commands/data", True, False),
        ],
    )
    async def test_wiki_command_with_live_phrases(
        self, ctx, phrase, expected_title, expect_fields, expect_thumbnail
    ):
        await wiki.Wiki.wiki_search.callback(wiki.Wiki(None), ctx, phrase)
        responses = ctx.calls_named("respond")
        assert len(responses) == 1
        embed = ctx.embed
        assert embed is not None
        assert embed.title == expected_title

        if phrase == "gold":
            # Search resolves to a disambiguation page, which must not crash
            # the command or produce the normal page view.
            assert "may refer to" in embed.description
            assert "- " in embed.description
            assert responses[0][2].get("view") is None
            return

        assert embed.url == "https://minecraft.wiki/w/" + expected_title.replace(" ", "_")
        assert embed.description
        assert bool(embed.fields) is expect_fields
        assert bool(embed.thumbnail) is expect_thumbnail
        view = responses[0][2]["view"]
        selects = [child for child in view.children if isinstance(child, wiki.SectionsSelect)]
        assert len(selects) == 1
        assert selects[0].options

    @pytest.mark.parametrize(
        "phrase", ["Dirt", "Villager", "Ender Dragon", "Redstone circuits/Clock"]
    )
    async def test_section_embeds_obey_discord_limits(self, ctx, phrase):
        # Wiki markup regularly introduces image-only cells and very long
        # sections; neither may produce an embed Discord would reject.
        await wiki.Wiki.wiki_search.callback(wiki.Wiki(None), ctx, phrase)
        assert all(field.value for field in ctx.embed.fields)
        view = ctx.calls_named("respond")[0][2]["view"]
        select = next(child for child in view.children if isinstance(child, wiki.SectionsSelect))
        sections = ["Info"] + [option.label for option in select.options if option.label != "Info"]
        for section in sections:
            embeds = wiki.createSectionEmbed(select.html, select.page, section, select.embed)
            assert embeds
            for embed in embeds:
                assert len(embed.fields) <= wiki.MAX_FIELDS
                assert all(
                    field.value and len(field.value) <= wiki.MAX_FIELD_CHARS
                    for field in embed.fields
                )
                assert len(embed.description or "") <= wiki.MAX_DESCRIPTION_CHARS
                assert wiki._embed_size(embed) <= wiki.MAX_EMBED_CHARS


class TestCraftingApiContracts:
    def test_recipe_table_and_grid_classes(self, stick_page):
        soup = BeautifulSoup(stick_page.html, "html.parser")
        table = crafting.get_crafting_grids_table(soup)
        grid = table.find("span", class_="mcui-Crafting_Table")
        assert grid is not None
        assert grid.find("span", class_="mcui-input")
        assert grid.find("span", class_="mcui-output")
        assert len(grid.find("span", class_="mcui-input").find_all("span", class_="invslot")) == 9


class TestVillagerApiContracts:
    def test_trading_toc_still_exposes_professions(self, trading_page):
        toc = trading_page.table_of_contents
        assert "Trade offers" in toc
        assert "Armorer" in toc["Trade offers"]
        assert "Librarian" in toc["Trade offers"]
        professions = villager.get_villagers()
        assert "Armorer" in professions
        assert "Librarian" in professions

    async def test_villager_info_fetches_trades_from_live_page(self):
        file, job_site = await villager.villager_info("Armorer")
        assert file is not None
        assert file.filename == "villager_trade.png"
        assert job_site == "Blast Furnace"

    async def test_item_lookup_returns_matching_villager(self, ctx):
        await villager.Villager.item.callback(villager.Villager(None), ctx, "iron helmet")
        embed = ctx.embed
        assert embed is not None
        assert "Armorer" in embed.description
