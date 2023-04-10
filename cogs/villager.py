import discord
import fandom

class Villager(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        fandom.set_wiki("minecraft")
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(
        name = "villager",
        description = "Lookup trades of a particular villager",
    )
    async def villager(
        self, 
        ctx, 
        profession: discord.commands.Option(
            str,
            description="Shows villagers tradings and info",
            required=True,
        )
    ):
        await ctx.defer()
        page_id = fandom.search("Trading", results=1)[0][1]
        page = fandom.page(pageid=page_id)
        #print(page.title)
        #print(page.summary)
        #print(page.sections)
        msg = "You searched for " + page.title + " \w Villager - " + profession + "\n"
        print(msg)
        #
        data = page.content
        villagers = []
        toPrint = ""
        #print(data)
        foundVillager = False
        for section in data['sections']:
            for sub_section in section.get('sections', []):
                print(sub_section['title'])
                villagers.append(sub_section['title'])
                if profession.lower() in sub_section['title'].lower():
                    foundVillager = True
                    msg = "Found the " + profession + " villager\n"
                    print("Found the " + profession + " villager")
                    print(sub_section['title'])
                    toPrint = sub_section['content']
                    #print("======================")
                    #print(sub_section)
                    #print("======================")
                    #print(section)
                    break
            if foundVillager:
                break
        if not foundVillager:
            msg = "Could not find the villager! Did you mean one of these?: \n" + '\n'.join(villagers)

        msg = msg + toPrint
        await ctx.respond(str(msg))


def setup(bot):
    bot.add_cog(Villager(bot))
