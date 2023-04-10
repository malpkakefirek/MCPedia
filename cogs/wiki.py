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
        page_id = fandom.search(search, results=1)[0][1]
        page = fandom.page(pageid=page_id)
        html = Soup(page.html, 'html.parser')
        print([img['src'] for img in html.find_all('img')])
        images_links = "\n**Links**"
        await ctx.respond(images_links)

def setup(bot):
    bot.add_cog(Wiki(bot))
