import re
import discord
from mediawiki import MediaWiki, MediaWikiException
from bs4 import BeautifulSoup as Soup

from cogs.crafting import createCraftingGifs

wikipedia = MediaWiki("https://minecraft.wiki/api.php", user_agent="MCPediaDiscordBot/2.3 (https://minecraft.wiki/w/User:Malpkakefirek; https://github.com/malpkakefirek) pymediawiki/0.7.3")


def getEmbedThumbnailUrl(embed):
    if embed.thumbnail:
        return embed.thumbnail.url
    return None


def createSectionEmbed(html, page, section_title: str, old_embed: discord.Embed):
    embeds = []

    if section_title == 'Info':
        embed = discord.Embed(
            title=old_embed.title,
            description=page.summarize(),
            url=old_embed.url,
            color=old_embed.color
        )
        embeds.append(embed)
        embed.set_thumbnail(url=getEmbedThumbnailUrl(old_embed))

        # Experimental infobox
        infobox = html.find(class_='infobox-rows')
        if infobox:
            # info_text = ""
            info_rows = infobox.find_all('tr')
            for row in info_rows:
                th = row.find('th')
                header_text = th.get_text(' ', strip=True)
                # print(th)

                td = row.find('td')

                # String manipulation
                sprite = td.find(class_='sprite')
                if sprite and "title" in sprite.attrs:
                    data_text = sprite['title']
                else:
                    data_text = ''.join([
                        re.sub("( ?\n+ +)|( ?\n+ ?)", "", text).replace("<br>", "\n") for text in td.strings
                        if text.strip()
                    ]).strip()
                # print(repr(data_text))

                embed.add_field(
                    name=header_text,
                    value=data_text,
                    inline=False
                )
                # if "🛡" in data_text:
                #     embed.set_footer(text="Note: There is no 'half an armor' emoji, so it is represented the same as full!")
        return embeds

    # There are subsections
    if page.table_of_contents[section_title]:
        section_content = page.section(section_title)
        if not section_content:
            section_content = ""

        if len(section_content) > 4096:
            description = section_content[:4096]
            section_content = section_content[4096:]
        else:
            description = section_content
            section_content = None

        embed = discord.Embed(
            title=old_embed.title + " - " + section_title,
            url=old_embed.url + "#" + section_title.replace(" ", "_"),
            color=old_embed.color,
            description=description
        )
        embed.set_thumbnail(url=getEmbedThumbnailUrl(old_embed))
        embeds.append(embed)
        # print(f"AAA: {len(embed)}")

        embed_number = 2
        # If description is too big, send the rest of it to fields
        if section_content:
            while len(section_content) > 1024:
                embed.add_field(
                    name=section_title,
                    value=section_content[:1024],
                    inline=False
                )
                # print(f"222: {len(embed)}")
                if len(embed) > 6000:
                    embed.remove_field(len(embed.fields)-1)
                    # print(f"BBB: {len(embed)}")
                    embed = discord.Embed(
                        title=old_embed.title + " - " + section_title + " Part " + embed_number,
                        url=old_embed.url + "#" + section_title.replace(" ", "_"),
                        color=old_embed.color
                    )
                    embeds.append(embed)
                    embed.add_field(
                        name=section_title,
                        value=section_content[:1024],
                        inline=False
                    )
                    embed_number += 1
                    # print(f"CCC: {len(embed)}")
                section_content = section_content[1024:]
            embed.add_field(
                name=section_title,
                value=section_content,
                inline=False
            )
            # print(f"DDD: {len(embed)}")
            if len(embed) > 6000:
                embed.remove_field(len(embed.fields)-1)
                # print(f"EEE: {len(embed)}")
                embed = discord.Embed(
                    title=old_embed.title + " - " + section_title,
                    url=old_embed.url + "#" + section_title.replace(" ", "_"),
                    color=old_embed.color
                )
                embeds.append(embed)
                embed.add_field(
                    name=section_title,
                    value=section_content,
                    inline=False
                )
                # print(f"FFF: {len(embed)}")

        # Send subsections to fields
        for subsection_title in page.table_of_contents[section_title]:
            subsection_text = page.section(subsection_title)
            if not subsection_text:
                continue
            while len(subsection_text) > 1024:
                embed.add_field(
                    name=subsection_title,
                    value=subsection_text[:1024],
                    inline=False
                )
                # print(f"GGG: {len(embed)}")
                if len(embed) > 6000:
                    embed.remove_field(len(embed.fields)-1)
                    # print(f"HHH: {len(embed)}")
                    embed = discord.Embed(
                        title=old_embed.title + " - " + section_title + " Part " + str(embed_number),
                        url=old_embed.url + "#" + section_title.replace(" ", "_"),
                        color=old_embed.color,
                    )
                    embeds.append(embed)
                    embed.add_field(
                        name=subsection_title,
                        value=subsection_text[:1024],
                        inline=False
                    )
                    embed_number += 1
                    # print(f"III: {len(embed)}")
                subsection_text = subsection_text[1024:]
            embed.add_field(
                name=subsection_title,
                value=subsection_text,
                inline=False
            )
            # print(f"JJJ: {len(embed)}")
            if len(embed) > 6000:
                embed.remove_field(len(embed.fields)-1)
                # print(f"KKK: {len(embed)}")
                embed = discord.Embed(
                    title=old_embed.title + " - " + section_title + " Part " + str(embed_number),
                    url=old_embed.url + "#" + section_title.replace(" ", "_"),
                    color=old_embed.color,
                )
                embeds.append(embed)
                embed.add_field(
                    name=subsection_title,
                    value=subsection_text,
                    inline=False
                )
                embed_number += 1
                # print(f"LLL: {len(embed)}")

        # Add " Part 1" to the title of the first embed, if there are multiple embeds
        if len(embeds) > 1:
            embeds[0].title = embeds[0].title + " Part 1"
    # No subsections
    else:
        section_content = page.section(section_title)

        if len(section_content) > 4096:
            description = section_content[:4096]
            section_content = section_content[4096:]
        else:
            description = section_content
            section_content = None

        embed = discord.Embed(
            title=old_embed.title + " - " + section_title,
            description=description,
            url=old_embed.url + "#" + section_title.replace(" ", "_"),
            color=old_embed.color
        )
        embed.set_thumbnail(url=getEmbedThumbnailUrl(old_embed))
        embeds.append(embed)

        if section_content:
            while len(section_content) > 1024:
                embed.add_field(
                    name=section_title,
                    value=section_content[:1024],
                    inline=False
                )
                if len(embed) > 6000:
                    embed.remove_field(len(embed.fields)-1)
                    embed = discord.Embed(
                        title=old_embed.title + " - " + section_title,
                        url=old_embed.url + "#" + section_title.replace(" ", "_"),
                        color=old_embed.color
                    )
                    embeds.append(embed)
                    embed.add_field(
                        name=section_title,
                        value=section_content[:1024],
                        inline=False
                    )
                section_content = section_content[1024:]
            embed.add_field(
                name=section_title,
                value=section_content,
                inline=False
            )
            if len(embed) > 6000:
                embed.remove_field(len(embed.fields)-1)
                embed = discord.Embed(
                    title=old_embed.title + " - " + section_title,
                    url=old_embed.url + "#" + section_title.replace(" ", "_"),
                    color=old_embed.color
                )
                embeds.append(embed)
                embed.add_field(
                    name=section_title,
                    value=section_content,
                    inline=False
                )
    for embed in embeds:
        print(len(embed))
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
        embeds = createSectionEmbed(self.html, self.page, self.values[0], self.embed)

        # Delete embeds that were part of the partitioning system
        if len(self.parts) > 0:
            for embed_response in self.parts:
                if isinstance(embed_response, discord.Interaction):
                    await embed_response.delete_original_response()
                else:
                    await embed_response.delete()
            self.parts = []

        # Send embeds
        # original_response = await interaction.original_response()
        if len(embeds) > 1:
            await self.original_message.edit(embed=embeds[0], view=None)
            for embed in embeds[1:-1]:
                # Send additional parts and add them to the parts list
                middle = await interaction.respond(embed=embed)
                print(f"middle: {middle} {type(middle)}")
                self.parts.append(middle)
            self.parts.append(await interaction.respond(embed=embeds[-1], view=self.view))
        elif len(embeds) == 1:
            await self.original_message.edit(embed=embeds[0], view=self.view)
            await interaction.edit(embed=embeds[0])
        else:
            await self.original_message.edit("Something went wrong! Couldn't create the embed!", embed=None)
            await interaction.edit(embed=embeds[0])


class CraftingButton(discord.ui.Button):
    def __init__(self, html):
        super().__init__(style=discord.ButtonStyle.green, label="Show Crafting")
        self.html = html

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False)
        self.disabled = True
        await interaction.message.edit(view=self.view)
        files = createCraftingGifs(self.html)
        while len(files) > 10:
            await interaction.followup.send(files=files[0:9])
            files = files[10:]
        await interaction.followup.send(files=files)


class SectionsView(discord.ui.View):
    def __init__(self, html, page, sections: list[str], embed: discord.Embed):
        super().__init__(timeout=None)
        if len(sections) > 0:
            self.add_item(SectionsSelect(html, page, sections, embed))

        subsections = [
            subsection_title for subsection_title in page.table_of_contents.values()
            if subsection_title
        ]
        if 'Crafting' in subsections:
            self.add_item(CraftingButton(html))


class Wiki(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        print(f"** SUCCESSFULLY LOADED {__name__} **")

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
        print(f"[INFO] Starting a search for '{search}'")
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
            page_id = search_results[0]
            page = wikipedia.page(page_id)
        except MediaWikiException:
            await ctx.respond("We could not complete your search due to a temporary problem. Please try again later.")
            return
        print(f"[INFO] Found '{page.title}' for search '{search}'")

        html = Soup(page.html, 'html.parser')
        image_area = html.find(class_="infobox-imagearea")
        image_a = None
        if image_area is not None:
            image_a = image_area.find('a')

        embed = discord.Embed(
            title=page.title,
            url=wiki_url + page.title.replace(" ", "_"),
            description=page.summarize(),
            color=discord.Color(43520),    # 00AA00 (dark green)
        )
        if image_a is not None:
            image_url = "https://minecraft.wiki/images/" + image_a.get('href').split('File:')[1]
            print(image_url)
            embed.set_thumbnail(url=image_url)
        else:
            print(f"[WARN] Couldn't find a thumbnail for '{page.title}'!")

        # Experimental infobox
        infobox = html.find(class_='infobox-rows')
        if infobox:
            # info_text = ""
            info_rows = infobox.find_all('tr')
            for row in info_rows:
                th = row.find('th')
                header_text = th.get_text(' ', strip=True)
                # print(th)

                td = row.find('td')

                # One time replacements
                # links
                for link_element in td.find_all('a'):
                    if 'href' not in link_element.attrs:
                        print(f"No link found in: {link_element}")
                        continue
                    sprite_text = link_element.find(class_='sprite-text')
                    link_prefix = "https://minecraft.wiki"
                    if link_element['href'].startswith(link_prefix):
                        link_prefix = ""

                    if sprite_text:
                        sprite_text.string.replace_with(f"[{sprite_text.string}](<{link_prefix}{link_element['href']}>)")
                    elif link_element.string:
                        link_element.string.replace_with(f"[{link_element.string}](<{link_prefix}{link_element['href']}>)")
                    # else:
                    #     sprite = td.find(class_='sprite')
                    #     if sprite and "title" in sprite.attrs:
                    #         link_element.append(f"[{sprite['title']}](<{link_prefix}{link_element['href']}>)")
                    #     else:
                    #         link_element.append(f"[{link_element['title']}](<{link_prefix}{link_element['href']}>)")
                    # print(link_element)
                # images
                images = td.find_all('img')
                for image in images:
                    # Add alt to fix hearts and shields, but block all other alts
                    if 'alt' in image.attrs and len(image['alt']) <= 2:
                        image.append(image['alt'])
                # new-lines
                for br in td.find_all('br'):
                    br.append("<br>")
                for p in td.find_all('p'):
                    p.append("<br>")
                for li in td.find_all('li'):
                    li.append("<br>")
                # italics
                for italic in td.find_all('i'):
                    if italic.string:
                        italic.string.replace_with(f"*{italic.string}*")
                    # elif italic.strings:    # doesn't work for some reason
                    #     for string in italic.strings:
                    #         string.replace_with(f"_{string}_")
                    else:
                        print("skipping italicizing, because idk how to do it")
                        print(italic)
                # bold text
                for bold in td.find_all('b'):
                    # print(bold)
                    # if bold.a:
                    #     for a_elem in bold.find_all('a', text=True):
                    #         a_elem.string.replace_with(f"**{bold.a.string}**")
                    # else:
                    #     bold.string.replace_with(f"**{bold.string}**")
                    bold.insert(0, "**")
                    bold.append("**")
                # hearts
                mc_hearts = row.find_all(class_='mc-hearts')
                for mc_heart in mc_hearts:
                    for single_heart in mc_heart.find_all('img'):
                        if "half" in single_heart['src'].lower():
                            single_heart.string.replace_with("♡")
                        elif "empty" in single_heart['src'].lower():
                            single_heart.string.replace_with("")
                            break
                    else:   # (no empty hearts)
                        mc_heart.append(") ")
                        previous = mc_heart.previous_sibling
                        previous.string.replace_with(f"{previous.string} (")
                # armor
                mc_armors = row.find_all(class_='iconbar')
                for mc_armor in mc_armors:
                    if "heart" in mc_armor['title'].lower():
                        continue
                    for single_armor in mc_armor.find_all('img'):
                        if "half" in single_armor['src'].lower():
                            single_armor.string.replace_with("½🛡️")

                # remove new-lines (from strings)
                # replace some special space characters with normal spaces
                # change "<br>" to new-lines
                data_list = [
                    new_text for text in td.strings
                    if (
                        (new_text := re.sub(
                            "\u00A0|\u200B|\u200C",
                            " ",
                            re.sub(
                                r"( ?\n+ +)|( ?\n+ ?)",
                                "",
                                text
                            )
                        ).replace("<br>", "\n")) != ''
                    )
                ]
                data_text = ''.join(data_list).strip("\n")

                embed.add_field(
                    name=header_text,
                    value=data_text,
                    inline=False
                )
                # if "🛡" in data_text:
                #     embed.set_footer(text="Note: There is no 'half an armor' emoji, so it is represented the same as full!")

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
        print(f"[INFO] Successfully sent '{page.title}'!")


def setup(bot):
    bot.add_cog(Wiki(bot))
