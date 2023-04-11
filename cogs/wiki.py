import discord
import fandom
from bs4 import BeautifulSoup as Soup


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
        # html = Soup(page.html, 'html.parser')
        embed = discord.Embed(
            title = page.title,
            url = wiki_url + page.title.replace(" ", "_"),
            description = page.summary,
            color = discord.Color(43520),    # 00AA00 (dark green)
        )
        # view = discord.ui.View()
        # section_select = discord.ui.Select() # TODO: ~~create custom select class~~ NEVERMIND! There are too many sections to fit into a select menu! Convert to command option + pagination arrows?
        # for section in page.sections:
            # try:
                # section_select.add_option(label=section)
            # except:
                # break
        # view.add_item(section_select)
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Wiki(bot))
