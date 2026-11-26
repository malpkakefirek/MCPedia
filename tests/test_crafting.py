"""Tests for crafting helpers and the crafting slash command."""

from io import BytesIO
from types import SimpleNamespace
from unittest import mock

from bs4 import BeautifulSoup
from PIL import Image

from cogs import crafting
from conftest import FakeContext, make_page


CRAFTING_HTML = (
    "<table><tbody><tr><th>Header</th></tr><tr><td>"
    '<span class="mcui-Crafting_Table">'
    '<span class="mcui-input"><span class="invslot"><span class="invslot-item">'
    '<span class="sprite inv-sprite" style="background-position: -0px -0px;"></span>'
    "</span></span></span>"
    '<span class="mcui-output"><span class="invslot">'
    '<span class="invslot-stacksize">4</span>'
    '<span class="sprite inv-sprite" style="background-position: -32px -0px;"></span>'
    "</span></span></span>"
    "</td><td>Recipe</td><td>Description</td></tr></tbody></table>"
)


class TestIsElementVisible:
    def test_visible_without_style(self):
        element = BeautifulSoup("<div><span>visible</span></div>", "html.parser").span
        assert crafting.is_element_visible(element) is True

    def test_hidden_by_own_style(self):
        element = BeautifulSoup('<span style="display: none">hidden</span>', "html.parser").span
        assert crafting.is_element_visible(element) is False

    def test_hidden_by_parent_style(self):
        element = BeautifulSoup('<div style="display:none"><span>hidden</span></div>', "html.parser").span
        assert crafting.is_element_visible(element) is False


class TestConvertAnimatedSprite:
    def test_returns_first_frame_copy(self):
        first = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
        second = Image.new("RGBA", (2, 2), (0, 255, 0, 255))
        buffer = BytesIO()
        first.save(buffer, format="GIF", save_all=True, append_images=[second])
        buffer.seek(0)
        image = Image.open(buffer)
        frame = crafting.convert_animated_sprite_to_static_frame(image)
        assert frame is not None
        assert frame.size == (2, 2)
        assert frame is not image

    def test_returns_none_for_empty_image(self):
        image = mock.Mock()
        image.seek.side_effect = EOFError
        assert crafting.convert_animated_sprite_to_static_frame(image) is None


class TestGetCraftingGridsTable:
    def test_finds_table_after_crafting_heading(self):
        soup = BeautifulSoup(
            "<div><div id='Crafting'>Crafting</div><table id='target'></table></div>", "html.parser"
        )
        assert crafting.get_crafting_grids_table(soup)["id"] == "target"


class TestCreateCraftingGifs:
    def test_builds_gif_file_from_crafting_table(self):
        soup = BeautifulSoup(CRAFTING_HTML, "html.parser")
        sprite_sheet = BytesIO()
        Image.new("RGBA", (64, 64), (200, 100, 50, 255)).save(sprite_sheet, format="PNG")
        response = SimpleNamespace(content=sprite_sheet.getvalue())
        with (
            mock.patch.object(crafting, "get_crafting_grids_table", return_value=soup.table),
            mock.patch.object(crafting.requests, "get", return_value=response) as request,
        ):
            files = crafting.createCraftingGifs(soup)
        assert len(files) == 1
        assert files[0].filename == "crafting_animation.gif"
        assert files[0].fp.read(6) in (b"GIF87a", b"GIF89a")
        request.assert_called_once()


class TestCraftingCommand:
    async def test_no_search_results(self, ctx):
        with mock.patch.object(crafting, "wikipedia") as wikipedia:
            wikipedia.search.return_value = []
            await crafting.Crafting.crafting.callback(crafting.Crafting(None), ctx, "unknown")
        assert ctx.embed.title == "Not Found :("

    async def test_page_without_content(self, ctx):
        page = SimpleNamespace(title="Unknown", sections=[])
        with mock.patch.object(crafting, "wikipedia") as wikipedia:
            wikipedia.search.return_value = ["Unknown"]
            wikipedia.page.return_value = page
            await crafting.Crafting.crafting.callback(crafting.Crafting(None), ctx, "unknown")
        assert ctx.response_content == "Couldn't find anything for `unknown`"

    async def test_page_without_crafting_section(self, ctx):
        page = make_page(title="Dirt", toc={"Usage": []})
        with mock.patch.object(crafting, "wikipedia") as wikipedia:
            wikipedia.search.return_value = ["Dirt"]
            wikipedia.page.return_value = page
            await crafting.Crafting.crafting.callback(crafting.Crafting(None), ctx, "dirt")
        assert ctx.response_content == "Crafting of `dirt` does not exist"

    async def test_sends_recipe_files(self, ctx):
        page = make_page(title="Dirt", toc={"Crafting": []})
        files = [SimpleNamespace(name=str(i)) for i in range(12)]
        with (
            mock.patch.object(crafting, "wikipedia") as wikipedia,
            mock.patch.object(crafting, "createCraftingGifs", return_value=files),
        ):
            wikipedia.search.return_value = ["Dirt"]
            wikipedia.page.return_value = page
            await crafting.Crafting.crafting.callback(crafting.Crafting(None), ctx, "dirt")
        responses = ctx.calls_named("respond")
        assert len(responses) == 2
        assert [file.name for file in responses[0][2]["files"]] == [str(i) for i in range(10)]
        assert [file.name for file in responses[1][2]["files"]] == ["10", "11"]
