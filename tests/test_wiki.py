"""Tests for the wiki search command and its embed-building helpers."""

from types import SimpleNamespace
from unittest import mock

import discord
from bs4 import BeautifulSoup
from mediawiki import DisambiguationError, MediaWikiException

from cogs import wiki
from conftest import make_page


INFOBOX_HTML = """
<div class="infobox-imagearea"><a href="/w/File:Dirt.png">Dirt</a></div>
<table class="infobox-rows">
  <tr><th>Hardness</th><td><span class="sprite" title="0.5"></span></td></tr>
  <tr><th>Renewable</th><td>Yes<br>Usually</td></tr>
</table>
"""


def old_embed(color=discord.Color(43520)):
    embed = discord.Embed(title="Dirt", url="https://minecraft.wiki/w/Dirt", color=color)
    embed.set_thumbnail(url="https://minecraft.wiki/images/Dirt.png")
    return embed


class TestGetEmbedThumbnailUrl:
    def test_returns_url_when_present(self):
        assert wiki.getEmbedThumbnailUrl(old_embed()) == "https://minecraft.wiki/images/Dirt.png"

    def test_returns_none_when_absent(self):
        assert wiki.getEmbedThumbnailUrl(discord.Embed(title="No thumbnail")) is None


class TestInfoboxFormatting:
    @staticmethod
    def fields(html):
        infobox = BeautifulSoup(html, "html.parser").find(class_="infobox-rows")
        return wiki.format_infobox_fields(infobox)

    def test_image_only_cell_gets_a_readable_label(self):
        fields = self.fields("""
        <table class="infobox-rows">
          <tr><th>Tool</th><td><span class="pixel-image"><img alt="SlotSprite Shovel Required.png: Sprite image for Shovel Required in Minecraft"></span></td></tr>
          <tr><th>Unknown</th><td></td></tr>
        </table>
        """)
        assert fields == [("Tool", "Shovel Required"), ("Unknown", "—")]

    def test_nested_italics_and_footnotes_are_formatted(self):
        value = self.fields("""
        <table class="infobox-rows"><tr><th>Behavior</th><td>
          Passive<sup class="reference"><a href="#note"><span>[</span>note 1<span>]</span></a></sup>
          <i><span><a href="/w/Java_Edition">Java Edition</a> only</span></i>
        </td></tr></table>
        """)[0][1]
        assert "note 1" not in value
        assert "*[Java Edition](<https://minecraft.wiki/w/Java_Edition>) only*" in value

    def test_source_markup_is_not_mutated(self):
        html = "<table class='infobox-rows'><tr><th>X</th><td><b>bold</b></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        infobox = soup.find(class_="infobox-rows")
        assert wiki.format_infobox_fields(infobox) == wiki.format_infobox_fields(infobox)
        assert infobox.find("b").get_text() == "bold"


class TestCreateSectionEmbed:
    def test_info_reuses_existing_description_without_another_api_call(self):
        page = make_page(summary="Should not be requested again")
        embed = old_embed()
        embed.description = "Cached summary"
        assert wiki.createSectionEmbed(None, page, "Info", embed)[0].description == "Cached summary"
        page.summarize.assert_not_called()

    def test_more_than_25_fields_are_split_across_embeds(self):
        rows = "".join(f"<tr><th>Field {i}</th><td>value</td></tr>" for i in range(28))
        html = BeautifulSoup(f"<table class='infobox-rows'>{rows}</table>", "html.parser")
        embeds = wiki.createSectionEmbed(html, make_page(), "Info", old_embed())
        assert len(embeds) == 2
        assert max(len(embed.fields) for embed in embeds) <= wiki.MAX_FIELDS
        assert all(wiki._embed_size(embed) <= wiki.MAX_EMBED_CHARS for embed in embeds)

    def test_info_section_includes_summary_and_infobox(self):
        page = make_page(summary="Dirt is a block.")
        html = BeautifulSoup(INFOBOX_HTML, "html.parser")
        embeds = wiki.createSectionEmbed(html, page, "Info", old_embed())
        assert len(embeds) == 1
        embed = embeds[0]
        assert embed.title == "Dirt"
        assert embed.description == "Dirt is a block."
        assert embed.thumbnail.url == "https://minecraft.wiki/images/Dirt.png"
        assert [(field.name, field.value) for field in embed.fields] == [
            ("Hardness", "0.5"),
            ("Renewable", "Yes\nUsually"),
        ]

    def test_section_with_subsections(self):
        page = make_page(
            sections={"Usage": "A" * 5000, "Subsection": "short text"},
            toc={"Usage": ["Subsection"]},
        )
        embeds = wiki.createSectionEmbed(BeautifulSoup("<html></html>", "html.parser"), page, "Usage", old_embed())
        assert len(embeds) == 1
        embed = embeds[0]
        assert embed.title == "Dirt - Usage"
        assert embed.url == "https://minecraft.wiki/w/Dirt#Usage"
        assert embed.description == "A" * 4096
        assert [field.name for field in embed.fields] == ["Usage", "Subsection"]
        assert embed.thumbnail.url == "https://minecraft.wiki/images/Dirt.png"

    def test_long_section_is_split_across_embeds(self):
        page = make_page(sections={"Usage": "A" * 9000})
        embeds = wiki.createSectionEmbed(BeautifulSoup("<html></html>", "html.parser"), page, "Usage", old_embed())
        assert len(embeds) > 1
        assert all(embed.title.startswith("Dirt - Usage") for embed in embeds)
        assert all(wiki._embed_size(embed) <= 6000 for embed in embeds)


class TestWikiSearchCommand:
    async def test_query_too_long(self, ctx):
        await wiki.Wiki.wiki_search.callback(wiki.Wiki(None), ctx, "x" * 201)
        assert ctx.embed.title == "Query Too Long :("
        assert ctx.calls_named("defer")

    async def test_no_results(self, ctx):
        with mock.patch.object(wiki, "wikipedia") as wikipedia:
            wikipedia.search.return_value = []
            await wiki.Wiki.wiki_search.callback(wiki.Wiki(None), ctx, "nonexistent")
        assert ctx.embed.title == "Not Found :("
        assert "nonexistent" in ctx.embed.description

    async def test_wiki_exception(self, ctx):
        with mock.patch.object(wiki, "wikipedia") as wikipedia:
            wikipedia.search.side_effect = MediaWikiException("temporary problem")
            await wiki.Wiki.wiki_search.callback(wiki.Wiki(None), ctx, "Dirt")
        assert ctx.response_content == (
            "We could not complete your search due to a temporary problem. Please try again later."
        )

    async def test_disambiguation_lists_suggestions(self, ctx):
        error = DisambiguationError(
            "Orange",
            ["Orange (fruit)", "Orange (color)"],
            "https://minecraft.wiki/w/Orange",
            details=[{"title": "Orange (fruit)"}, {"title": "Orange (color)"}, {"title": "Orange (fruit)"}],
        )
        with mock.patch.object(wiki, "wikipedia") as wikipedia:
            wikipedia.search.side_effect = error
            await wiki.Wiki.wiki_search.callback(wiki.Wiki(None), ctx, "Orange")
        embed = ctx.embed
        assert embed.title == "Disambiguation Error!"
        assert "- Orange (fruit)" in embed.description
        assert "- Orange (color)" in embed.description
        assert embed.description.count("- Orange (fruit)") == 1

    async def test_successful_search_builds_embed_and_view(self, ctx):
        page = make_page(
            title="Dirt",
            summary="Dirt is a block.",
            html=INFOBOX_HTML,
            toc={"Usage": ["Crafting"]},
        )
        with mock.patch.object(wiki, "wikipedia") as wikipedia:
            wikipedia.search.return_value = ["Dirt"]
            wikipedia.page.return_value = page
            await wiki.Wiki.wiki_search.callback(wiki.Wiki(None), ctx, "dirt")
        embed = ctx.embed
        assert embed.title == "Dirt"
        assert embed.url == "https://minecraft.wiki/w/Dirt"
        assert embed.thumbnail.url == "https://minecraft.wiki/images/Dirt.png"
        assert [field.name for field in embed.fields] == ["Hardness", "Renewable"]
        view = ctx.calls_named("respond")[0][2]["view"]
        assert len(view.children) == 2
        assert any(isinstance(child, wiki.SectionsSelect) for child in view.children)
        assert any(isinstance(child, wiki.CraftingButton) for child in view.children)


class TestSectionsSelect:
    def make_select(self):
        select = wiki.SectionsSelect("<html></html>", make_page(), ["Info"], old_embed())
        select._selected_values = ["Info"]
        view = discord.ui.View()
        view.add_item(select)  # also attaches the select to the view
        return select

    async def test_single_embed_updates_original_message(self, interaction):
        select = self.make_select()
        embed = discord.Embed(title="Info")
        with mock.patch.object(wiki, "createSectionEmbed", return_value=[embed]):
            await select.callback(interaction)
        assert select.original_message is interaction.message
        assert interaction.message.calls_named("edit")[0][2]["embed"] is embed
        assert interaction.message.calls_named("edit")[0][2]["view"] is select.view
        assert interaction.calls_named("edit")[0][2]["embed"] is embed

    async def test_multiple_embeds_send_extra_parts_and_clean_them_up(self, interaction):
        select = self.make_select()
        embeds = [discord.Embed(title="Info"), discord.Embed(title="Info Part 2")]
        with mock.patch.object(wiki, "createSectionEmbed", return_value=embeds):
            await select.callback(interaction)
        assert len(select.parts) == 1
        part = select.parts[0]
        assert part.embed is embeds[-1]
        assert interaction.message.calls_named("edit")[0][2]["view"] is None

        with mock.patch.object(wiki, "createSectionEmbed", return_value=[embeds[0]]):
            await select.callback(interaction)
        assert select.parts == []
        assert part.deleted is True


class TestCraftingButton:
    async def test_sends_files_in_batches_of_ten(self, interaction):
        button = wiki.CraftingButton("<html></html>")
        view = discord.ui.View()
        view.add_item(button)
        files = [SimpleNamespace(name=str(i)) for i in range(12)]
        with mock.patch.object(wiki, "createCraftingGifs", return_value=files):
            await button.callback(interaction)
        sends = interaction.calls_named("followup.send")
        assert len(sends) == 2
        assert [file.name for file in sends[0][2]["files"]] == [str(i) for i in range(10)]
        assert [file.name for file in sends[1][2]["files"]] == ["10", "11"]
        assert button.disabled is True
        assert interaction.message.calls_named("edit")


class TestSectionsView:
    async def test_no_sections_means_no_items(self):
        view = wiki.SectionsView("<html></html>", make_page(toc={}), [], old_embed())
        assert view.children == []

    async def test_crafting_section_adds_button(self):
        view = wiki.SectionsView(
            "<html></html>", make_page(toc={"Usage": ["Crafting"]}), ["Usage"], old_embed()
        )
        assert len(view.children) == 2
        assert isinstance(view.children[0], wiki.SectionsSelect)
        assert isinstance(view.children[1], wiki.CraftingButton)
