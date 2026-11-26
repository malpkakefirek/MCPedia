"""Slash command and helpers for looking up Minecraft Wiki pages."""

import asyncio
import logging
import re

import discord
from bs4 import BeautifulSoup as Soup
from mediawiki import MediaWiki, MediaWikiException, DisambiguationError

from cogs.crafting import createCraftingGifs

logger = logging.getLogger(__name__)

wikipedia = MediaWiki(
    "https://minecraft.wiki/api.php",
    user_agent="MCPediaDiscordBot/2.5 (https://minecraft.wiki/w/User:Malpkakefirek; https://github.com/malpkakefirek) pymediawiki/0.7.3"
)

# Discord's hard limits for embeds.
MAX_EMBED_CHARS = 6000
MAX_DESCRIPTION_CHARS = 4096
MAX_FIELD_CHARS = 1024
MAX_FIELDS = 25

_WHITESPACE_RE = re.compile(r"( ?\n+ +)|( ?\n+ ?)")
_SPECIAL_SPACE_RE = re.compile("\u00A0|\u200B|\u200C")
_SPRITE_ALT_RE = re.compile(r"Sprite image for (.+?) in Minecraft", re.IGNORECASE)


def getEmbedThumbnailUrl(embed):
    if embed.thumbnail:
        return embed.thumbnail.url
    return None


def _clean_text(text):
    """Collapse wiki whitespace and turn injected ``<br>`` markers into newlines."""
    return _SPECIAL_SPACE_RE.sub(" ", _WHITESPACE_RE.sub("", text)).replace("<br>", "\n")


def _image_only_label(element):
    """Readable fallback for cells/links that contain no text, only an image."""
    for image in element.find_all("img"):
        alt = image.get("alt") or ""
        match = _SPRITE_ALT_RE.search(alt)
        if match:
            return match.group(1)
        if image.get("title"):
            return image["title"]
        if alt and len(alt) <= 2:
            return alt
    for tag in element.find_all(attrs={"title": True}):
        if tag.get("title"):
            return tag["title"]
    return ""


def _set_text(tag, text):
    """Replace a tag's contents with plain text, even when it has no single string."""
    if tag.string is not None:
        tag.string.replace_with(text)
    else:
        tag.clear()
        tag.append(text)


def format_infobox_fields(infobox):
    """Convert an ``infobox-rows`` table into Discord field pairs.

    The wiki markup is edited in place to inject markdown, so this works on a
    private copy.  Selecting "Info" repeatedly therefore cannot stack bold or
    link markers on top of each other.
    """
    if infobox is None:
        return []

    table = Soup(str(infobox), "html.parser")
    fields = []

    for row in table.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if th is None or td is None:
            continue
        header = th.get_text(" ", strip=True)
        if not header:
            continue

        # Links -> markdown. get_text handles links with nested spans/icons.
        for link in td.find_all("a"):
            href = link.get("href")
            if not href:
                continue
            label = link.get_text("", strip=True) or _image_only_label(link)
            if not label:
                # Image-only links are left alone so the icon handling below
                # can still turn them into a readable glyph.
                continue
            prefix = "" if href.startswith(("http://", "https://")) else "https://minecraft.wiki"
            link.replace_with(f"[{label}](<{prefix}{href}>)")

        # Footnote markers such as "[note 1]" are noise in a Discord embed.
        for note in td.find_all("sup", class_="reference"):
            note.decompose()

        # Short alt text carries meaning (edition badges, hearts, shields).
        for image in td.find_all("img"):
            alt = image.get("alt") or ""
            if alt and len(alt) <= 2:
                image.append(alt)

        for br in td.find_all("br"):
            br.append("<br>")
        for tag in td.find_all(["p", "li"]):
            tag.append("<br>")

        # Wrap the whole element: italic/bold often contains a link or span,
        # so replacing .string alone silently dropped the formatting.
        for italic in td.find_all(["i", "em"]):
            italic.insert(0, "*")
            italic.append("*")
        for bold in td.find_all(["b", "strong"]):
            bold.insert(0, "**")
            bold.append("**")

        # Hearts and armor icons do not have useful alt text.
        for hearts in row.find_all(class_="mc-hearts"):
            has_empty = False
            for heart in hearts.find_all("img"):
                src = heart.get("src", "").lower()
                if "empty" in src:
                    heart.replace_with("")
                    has_empty = True
                elif "half" in src:
                    heart.replace_with("♡")
                else:
                    heart.replace_with("❤️")
            # Keep the wiki's "× 10" text; only wrap the icons in parentheses.
            if not has_empty:
                hearts.insert(0, " (")
                hearts.append(")")
        for armor in row.find_all(class_="iconbar"):
            if "heart" in armor.get("title", "").lower():
                continue
            for icon in armor.find_all("img"):
                if "half" in icon.get("src", "").lower():
                    _set_text(icon, "½🛡️")

        data_text = "".join(_clean_text(text) for text in td.strings).strip()
        if not data_text:
            data_text = _image_only_label(td) or "—"
        fields.append((header, data_text[:MAX_FIELD_CHARS]))

    return fields


def _make_embed(old_embed, title, url=None, description=None):
    embed = discord.Embed(
        title=title[:256],
        url=url,
        color=old_embed.color,
        description=(description or "")[:MAX_DESCRIPTION_CHARS] or None,
    )
    thumbnail = getEmbedThumbnailUrl(old_embed)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed


def _part_title(title, part):
    return title if part == 1 else f"{title} Part {part}"


def _embed_size(embed):
    """py-cord's len() fails when an embed has no description, so measure it here."""
    return (len(embed.title or "") + len(embed.description or "")
            + sum(len(field.name or "") + len(field.value or "") for field in embed.fields))


def _add_field(embeds, old_embed, title, url, name, value):
    """Add a field, starting a new embed when Discord's limits are reached."""
    if not value:
        return
    value = value[:MAX_FIELD_CHARS]
    name = (name or "Info")[:256]
    embed = embeds[-1]
    if (len(embed.fields) >= MAX_FIELDS
            or _embed_size(embed) + len(name) + len(value) + 8 > MAX_EMBED_CHARS):
        embed = _make_embed(old_embed, _part_title(title, len(embeds) + 1), url)
        embeds.append(embed)
    embed.add_field(name=name, value=value, inline=False)


def _chunks(text, size):
    return [text[i:i + size] for i in range(0, len(text), size)]


def createSectionEmbed(html, page, section_title: str, old_embed: discord.Embed):
    """Build one or more embeds for a section chosen from the wiki select menu."""
    if section_title == "Info":
        # The original embed already holds the summary; avoid a second API call.
        summary = old_embed.description or page.summarize() or ""
        embeds = [_make_embed(old_embed, old_embed.title, old_embed.url, summary)]
        infobox = html.find(class_="infobox-rows") if html is not None else None
        for name, value in format_infobox_fields(infobox):
            _add_field(embeds, old_embed, old_embed.title, old_embed.url, name, value)
        return embeds

    title = old_embed.title + " - " + section_title
    url = old_embed.url + "#" + section_title.replace(" ", "_")
    embeds = [_make_embed(old_embed, title, url)]

    section_text = page.section(section_title) or ""
    embeds[0].description = section_text[:MAX_DESCRIPTION_CHARS]
    for chunk in _chunks(section_text[MAX_DESCRIPTION_CHARS:], MAX_FIELD_CHARS):
        _add_field(embeds, old_embed, title, url, section_title, chunk)

    for subsection_title in (page.table_of_contents.get(section_title) or ()):
        subsection_text = page.section(subsection_title) or ""
        for chunk in _chunks(subsection_text, MAX_FIELD_CHARS):
            _add_field(embeds, old_embed, title, url, subsection_title, chunk)

    if len(embeds) > 1:
        embeds[0].title = title + " Part 1"
    return embeds


class SectionsSelect(discord.ui.Select):
    def __init__(self, html, page, sections: list[str], embed: discord.Embed):
        options = [discord.SelectOption(label=section) for section in sections]
        options.insert(0, discord.SelectOption(label='Info'))
        super().__init__(
            options=options,
            min_values=1,
            max_values=1,
            placeholder="Choose a Section"
        )
        self.page = page
        self.embed = embed
        self.html = html
        self.parts = []
        self.original_message = None

    async def callback(self, interaction: discord.Interaction):
        if self.original_message is None:
            self.original_message = interaction.message
        # Section text is parsed locally; keep the loop responsive.
        embeds = await asyncio.to_thread(
            createSectionEmbed, self.html, self.page, self.values[0], self.embed
        )

        # Delete embeds that were part of the partitioning system
        for embed_response in self.parts:
            if isinstance(embed_response, discord.Interaction):
                await embed_response.delete_original_response()
            else:
                await embed_response.delete()
        self.parts = []

        if len(embeds) > 1:
            await self.original_message.edit(embed=embeds[0], view=None)
            # Send additional parts and add them to the parts list
            for embed in embeds[1:-1]:
                self.parts.append(await interaction.respond(embed=embed))
            self.parts.append(await interaction.respond(embed=embeds[-1], view=self.view))
        elif len(embeds) == 1:
            await self.original_message.edit(embed=embeds[0], view=self.view)
            await interaction.edit(embed=embeds[0])
        else:
            await self.original_message.edit(
                "Something went wrong! Couldn't create the embed!", embed=None, view=None
            )


class CraftingButton(discord.ui.Button):
    def __init__(self, html):
        super().__init__(style=discord.ButtonStyle.green, label="Show Crafting")
        self.html = html

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False)
        self.disabled = True
        await interaction.message.edit(view=self.view)
        # GIF generation downloads sprites and uses PIL: keep it off the loop.
        files = await asyncio.to_thread(createCraftingGifs, self.html)
        for start in range(0, len(files), 10):
            await interaction.followup.send(files=files[start:start + 10])


class SectionsView(discord.ui.View):
    def __init__(self, html, page, sections: list[str], embed: discord.Embed):
        # A finite timeout lets the view (and the page HTML it holds) be
        # released. These components have no custom IDs, so they are not
        # persistent across restarts anyway.
        super().__init__(timeout=600)
        if len(sections) > 0:
            self.add_item(SectionsSelect(html, page, sections, embed))

        subsections = [
            subsection_title
            for subsection_titles in page.table_of_contents.values()
            for subsection_title in subsection_titles
        ]
        if 'Crafting' in subsections:
            self.add_item(CraftingButton(html))


class Wiki(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        logger.info("** SUCCESSFULLY LOADED %s **", __name__)

    @discord.slash_command(
        name="wiki",
        description="Search for anything in the Minecraft Wiki",
    )
    async def wiki_search(
        self,
        ctx,
        search: discord.commands.Option(
            str,
            description="Thing you want to search for in the Wiki",
            required=True,
        ),
    ):
        await ctx.defer()
        wiki_url = "https://minecraft.wiki/w/"
        if len(search) > 200:
            embed = discord.Embed(
                title="Query Too Long :(",
                description="Your search query is too long! It must be 200 characters or less in length.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return
        logger.info("Starting a search for '%s'", search)
        try:
            search_results = wikipedia.search(search, results=1)
            if len(search_results) == 0:
                embed = discord.Embed(
                    title="Not Found :(",
                    description=f"Nothing found for `{search}`!",
                    color=discord.Color.red()
                )
                await ctx.respond(embed=embed)
                return
            title = search_results[0]
            page = wikipedia.page(title=title, auto_suggest=False)
        except MediaWikiException:
            await ctx.respond("We could not complete your search due to a temporary problem. Please try again later.")
            return
        except DisambiguationError as e:
            logger.info("Found a Disambiguation '%s' for search '%s'", e.title, search)
            referrals = []
            seen = set()
            for link in e.details:
                label = link.get('title') if isinstance(link, dict) else str(link)
                line = f"- {label}"
                if line not in seen:
                    seen.add(line)
                    referrals.append(line)
            referrals = '\n'.join(referrals) or "Could not find any similar pages :cry:"
            text = '\n'.join((
                f"\"[{e.title}]({e.url})\" may refer to:",
                referrals,
                "You may search any of those using </wiki:1155638492278313051>!"
            ))
            embed = discord.Embed(
                title="Disambiguation Error!",
                description=text,
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            logger.info("Successfully sent a Disambiguation '%s'!", e.title)
            return
        logger.info("Found '%s' for search '%s'", page.title, search)

        html = Soup(page.html, 'html.parser')
        image_area = html.find(class_="infobox-imagearea")
        image_a = (
            image_area.find('a', href=lambda href: href and 'File:' in href)
            if image_area is not None else None
        )

        embed = discord.Embed(
            title=page.title,
            url=wiki_url + page.title.replace(" ", "_"),
            description=page.summarize(),
            color=discord.Color(43520),    # 00AA00 (dark green)
        )
        if image_a is not None:
            image_url = "https://minecraft.wiki/images/" + image_a['href'].split('File:', 1)[1].lstrip('/')
            logger.debug("Thumbnail: %s", image_url)
            embed.set_thumbnail(url=image_url)
        else:
            logger.warning("Couldn't find a thumbnail for '%s'!", page.title)

        for name, value in format_infobox_fields(html.find(class_='infobox-rows')):
            if (len(embed.fields) >= MAX_FIELDS
                    or _embed_size(embed) + len(name) + len(value) + 8 > MAX_EMBED_CHARS):
                logger.warning("Skipping remaining infobox fields for '%s'", page.title)
                break
            embed.add_field(name=name, value=value, inline=False)

        blacklisted_sections = [
            'Data values',
            'Video',
            'History',
            'Issues',
            'Gallery',
            'External links',
            'References',
            'External Links',
            'Sounds',
            'Achievements',
            'Advancements'
        ]
        sections = [
            section_title for section_title in page.table_of_contents
            if section_title not in blacklisted_sections
        ]
        view = SectionsView(html, page, sections, embed)
        await ctx.respond(embed=embed, view=view)
        logger.info("Successfully sent '%s'!", page.title)


def setup(bot):
    bot.add_cog(Wiki(bot))
