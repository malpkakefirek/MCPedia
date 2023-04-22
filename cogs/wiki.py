import discord
import fandom
from bs4 import BeautifulSoup as Soup

from cogs.crafting import createCraftingGif


def createSectionEmbed(data, section_title: str, old_embed: discord.Embed):
    embeds = []
    
    if section_title == 'Info':
        embed = discord.Embed(
            title = old_embed.title,
            description = data['content'],
            url = old_embed.url,
            color = old_embed.color
        )
        embeds.append(embed)
        embed.set_thumbnail(url=old_embed.thumbnail.url)
        
        if 'infobox' in data.keys():
            embed.add_field(
                name = 'Info Box',
                value = data['infobox']
            )
        return embeds
    
    section_data = [section for section in data['sections'] if section['title'] == section_title][0]
    # There are subsections
    if 'sections' in section_data.keys():
        section_content = section_data['content']
        
        if len(section_content) > 4096:
            description = section_content[:4096]
            section_content = section_content[4096:]
        else:
            description = section_content
            section_content = None
        
        embed = discord.Embed(
            title = old_embed.title + " - " + section_data['title'],
            url = old_embed.url + "#" + section_data['title'].replace(" ","_"),
            color = old_embed.color,
            description = description
        )
        embed.set_thumbnail(url=old_embed.thumbnail.url)
        embeds.append(embed)
        print(f"AAA: {len(embed)}")

        # If description is too big, send the rest of it to fields
        if section_content:
            while len(section_content) > 1024:
                embed.add_field(
                    name = section_data['title'],
                    value = section_content[:1024],
                    inline = False
                )
                print(f"222: {len(embed)}")
                if len(embed) > 6000:
                    embed.remove_field(len(embed.fields)-1)
                    print(f"BBB: {len(embed)}")
                    embed = discord.Embed(
                        title = old_embed.title + " - " + section_data['title'],
                        url = old_embed.url + "#" + section_data['title'].replace(" ", "_"),
                        color = old_embed.color
                    )
                    embeds.append(embed)
                    embed.add_field(
                        name = section_data['title'],
                        value = section_content[:1024],
                        inline = False
                    )
                    print(f"CCC: {len(embed)}")
                section_content = section_content[1024:]
            embed.add_field(
                name = section_data['title'],
                value = section_content,
                inline = False
            )
            print(f"DDD: {len(embed)}")
            if len(embed) > 6000:
                embed.remove_field(len(embed.fields)-1)
                print(f"EEE: {len(embed)}")
                embed = discord.Embed(
                    title = old_embed.title + " - " + section_data['title'],
                    url = old_embed.url + "#" + section_data['title'].replace(" ", "_"),
                    color = old_embed.color
                )
                embeds.append(embed)
                embed.add_field(
                    name = section_data['title'],
                    value = section_content,
                    inline = False
                )
                print(f"FFF: {len(embed)}")

        # Send subsections to fields
        for subsection in section_data['sections']:
            subsection_text = subsection['content']
            while len(subsection_text) > 1024:
                embed.add_field(
                    name = subsection['title'],
                    value = subsection_text[:1024],
                    inline = False
                )
                print(f"GGG: {len(embed)}")
                if len(embed) > 6000:
                    embed.remove_field(len(embed.fields)-1)
                    print(f"HHH: {len(embed)}")
                    embed = discord.Embed(
                        title = old_embed.title + " - " + section_data['title'] + " Part 2",
                        url = old_embed.url + "#" + section_data['title'].replace(" ","_"),
                        color = old_embed.color,
                    )
                    embeds.append(embed)
                    embed.add_field(
                        name = subsection['title'],
                        value = subsection_text[:1024],
                        inline = False
                    )
                    print(f"III: {len(embed)}")
                subsection_text = subsection_text[1024:]
            embed.add_field(
                name = subsection['title'],
                value = subsection_text,
                inline = False
            )
            print(f"JJJ: {len(embed)}")
            if len(embed) > 6000:
                embed.remove_field(len(embed.fields)-1)
                print(f"KKK: {len(embed)}")
                embed = discord.Embed(
                    title = old_embed.title + " - " + section_data['title'] + " Part 2",
                    url = old_embed.url + "#" + section_data['title'].replace(" ","_"),
                    color = old_embed.color,
                )
                embeds.append(embed)
                embed.add_field(
                    name = subsection['title'],
                    value = subsection_text,
                    inline = False
                )
                print(f"LLL: {len(embed)}")
    # No subsections
    else:
        section_content = section_data['content']
        
        if len(section_content) > 4096:
            description = section_content[:4096]
            section_content = section_content[4096:]
        else:
            description = section_content
            section_content = None

        embed = discord.Embed(
            title = old_embed.title + " - " + section_data['title'],
            description = description,
            url = old_embed.url + "#" + section_data['title'].replace(" ", "_"),
            color = old_embed.color
        )
        embed.set_thumbnail(url=old_embed.thumbnail.url)
        embeds.append(embed)

        if section_content:
            while len(section_content) > 1024:
                embed.add_field(
                    name = section_data['title'],
                    value = section_content[:1024],
                    inline = False
                )
                if len(embed) > 6000:
                    embed.remove_field(len(embed.fields)-1)
                    embed = discord.Embed(
                        title = old_embed.title + " - " + section_data['title'],
                        url = old_embed.url + "#" + section_data['title'].replace(" ", "_"),
                        color = old_embed.color
                    )
                    embeds.append(embed)
                    embed.add_field(
                        name = section_data['title'],
                        value = section_content[:1024],
                        inline = False
                    )
                section_content = section_content[1024:]
            embed.add_field(
                name = section_data['title'],
                value = section_content,
                inline = False
            )
            if len(embed) > 6000:
                embed.remove_field(len(embed.fields)-1)
                embed = discord.Embed(
                    title = old_embed.title + " - " + section_data['title'],
                    url = old_embed.url + "#" + section_data['title'].replace(" ", "_"),
                    color = old_embed.color
                )
                embeds.append(embed)
                embed.add_field(
                    name = section_data['title'],
                    value = section_content,
                    inline = False
                )
    for embed in embeds:
        print(len(embed))
    return embeds

class SectionsSelect(discord.ui.Select):
    def __init__(self, data, sections: list[str], embed: discord.Embed):
        options = [discord.SelectOption(label=section) for section in sections]
        options.insert(0, discord.SelectOption(label='Info'))
        super().__init__(
            options = options,
            min_values = 1,
            max_values = 1,
            placeholder = "Choose a Section"
        )
        self.data = data
        self.embed = embed

    async def callback(self, interaction: discord.Interaction):
        embeds = createSectionEmbed(self.data, self.values[0], self.embed)
        if len(embeds) > 1:
            await interaction.response.edit_message(embed=embeds[0], view=None)
            for embed in embeds[1:-1]:
                await interaction.followup.send(embed=embed)
            await interaction.followup.send(embed=embeds[-1], view=self.view)
        else:
            await interaction.response.edit_message(embed=embeds[0])


class CraftingButton(discord.ui.Button):
    def __init__(self, html):
        super().__init__(style=discord.ButtonStyle.green, label="Show Crafting")
        self.html = html

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False)
        self.disabled = True
        await interaction.message.edit(view=self.view)
        file = createCraftingGif(self.html)
        await interaction.followup.send(file=file)


class SectionsView(discord.ui.View):
    def __init__(self, html, data, sections: list[str], embed: discord.Embed):
        super().__init__(timeout=None)
        if len(sections) > 0:
            self.add_item(SectionsSelect(data, sections, embed))

        subsections = []
        if 'sections' in data.keys():
            subsections = [
                subsection['title'] for section in data['sections'] 
                if 'sections' in section.keys()
                for subsection in section['sections'] 
            ]
        if 'Crafting' in subsections:
            self.add_item(CraftingButton(html))


class Wiki(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        fandom.set_wiki("minecraft")
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    
    @discord.slash_command(
        name="search",
        description="Search for anything in the Minecraft Wiki",
    )
    async def search(
        self,
        ctx,
        search: discord.commands.Option(
            str,
            description="Thing you want to search for in the Wiki",
            required=True,
        ),
    ):
        await ctx.defer()
        wiki_url = "https://minecraft.fandom.com/wiki/"
        if len(search) > 200:
            embed = discord.Embed(
                title = "Query Too Long :(",
                description = "Your search query is too long! It must be 200 characters or less in length.",
                color = discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return
        search_results = fandom.search(search, results=1)
        if len(search_results) == 0:
            embed = discord.Embed(
                title = "Not Found :(",
                description = f"Nothing found for `{search}`!",
                color = discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return
        page_id = search_results[0][1]
        page = fandom.page(pageid=page_id)
        
        data = page.content
        html = Soup(page.html, 'html.parser')
        
        image_a = html.find('a', "image")
        image_url = image_a.get('href')
        
        embed = discord.Embed(
            title = page.title,
            url = wiki_url + page.title.replace(" ", "_"),
            description = data['content'],
            color = discord.Color(43520),    # 00AA00 (dark green)
        )
        embed.set_thumbnail(url=image_url)

        if 'infobox' in data.keys():
            info_text = data['infobox']
            while len(info_text) > 1024:
                embed.add_field(
                    name = 'Info Box',
                    value = info_text[:1024],
                    inline = False
                )
                info_text = info_text[1024:]
            embed.add_field(
                name = 'Info Box',
                value = info_text,
                inline = False
            )

        blacklisted_sections = [
            'Data values',
            'Video',
            'History',
            'Issues',
            'Gallery',
            'External links',
            'References',
            'External Links'
        ]

        sections = []
        if 'sections' in data.keys():
            sections = [
                section['title'] for section in data['sections']
                if section['title'] not in blacklisted_sections
            ]
        view = SectionsView(html, data, sections, embed)
        await ctx.respond(embed=embed, view=view)

def setup(bot):
    bot.add_cog(Wiki(bot))
