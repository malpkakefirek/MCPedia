import discord
import fandom
from bs4 import BeautifulSoup as Soup

from cogs.crafting import createCraftingGif


def createSectionEmbed(data, section_title: str, old_embed: discord.Embed):
    if section_title == 'Info':
        embed = discord.Embed(
            title = old_embed.title,
            description = data['content'],
            url = old_embed.url,
            color = old_embed.color
        )
        embed.set_thumbnail(url=old_embed.thumbnail.url)
        
        if 'infobox' in data.keys():
            embed.add_field(
                name = 'Info Box',
                value = data['infobox']
            )
        return embed
    
    section_data = [section for section in data['sections'] if section['title'] == section_title][0]
    if 'sections' in section_data.keys():
        embed = discord.Embed(
            title = old_embed.title + " - " + section_data['title'],
            url = old_embed.url + "#" + section_data['title'].replace(" ","_"),
            color = old_embed.color
        )
        for subsection in section_data['sections']:
            subsection_text = subsection['content']
            while len(subsection_text) > 1024:
                embed.add_field(
                    name = subsection['title'],
                    value = subsection_text[:1024],
                    inline = False
                )
                subsection_text = subsection_text[1024:]
            embed.add_field(
                name = subsection['title'],
                value = subsection_text,
                inline = False
            )
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

        if section_content:
            while len(section_content) > 1024:
                embed.add_field(
                    name = section_data['title'],
                    value = section_content[:1024]
                )
                section_content = section_content[1024:]
            embed.add_field(
                name = section_data['title'],
                value = section_content,
                inline = False
            )
    
    embed.set_thumbnail(url=old_embed.thumbnail.url)
    return embed

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
        embed = createSectionEmbed(self.data, self.values[0], self.embed)
        await interaction.response.edit_message(embed=embed)


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
        self.add_item(SectionsSelect(data, sections, embed))
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
        page_id = fandom.search(search, results=1)[0][1]
        page = fandom.page(pageid=page_id)
        
        data = page.content
        html = Soup(page.html, 'html.parser')
        
        image_a = html.find('a', "image image-thumbnail")
        image_url = image_a.get('href')
        
        embed = discord.Embed(
            title = page.title,
            url = wiki_url + page.title.replace(" ", "_"),
            description = page.summary,
            color = discord.Color(43520),    # 00AA00 (dark green)
        )
        embed.set_thumbnail(url=image_url)

        if 'infobox' in data.keys():
            embed.add_field(
                name = 'Info Box',
                value = data['infobox']
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
        
        sections = [
            section['title'] for section in data['sections'] 
            if section['title'] not in blacklisted_sections
        ]
        view = SectionsView(html, data, sections, embed)
        await ctx.respond(embed=embed, view=view)

def setup(bot):
    bot.add_cog(Wiki(bot))
