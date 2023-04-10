import discord
import fandom


class Crafting(discord.Cog):

  def __init__(self, bot):
    self.bot = bot
    fandom.set_wiki("minecraft")
    print(f"** SUCCESSFULLY LOADED {__name__} **")

  @discord.slash_command(name="crafting")
  async def crafting(self, ctx, item: discord.commands.Option(
    str,
    description="Shows crafting",
    required=True,
  )):
    await ctx.defer()
    page_id = fandom.search(item, results=1)[0][1]
    page = fandom.page(pageid=page_id)
    #print(page.title)
    #print(page.summary)
    #print(page.sections)
    data = page.content
    exists = "Crafting of " + page.title.lower() + " does not exist"

    placeholder = "NULL"
    crafting_exists = False
    for section in data['sections']:
      for sub_section in section.get('sections', []):
        if 'Crafting' in sub_section['content']:
          crafting_exists = True
          placeholder = sub_section['content']
          break
      if (crafting_exists):
        break

    if crafting_exists:
      #index = placeholder.index('Description\n')
      #substring = placeholder[index + len('Description\n'):]

      exists = "Crafting of " + page.title + " exists : \n" + placeholder  #substring
    #else:
    #  print(page.content)

    ##
    print(exists)
    await ctx.respond(exists)


def setup(bot):
  bot.add_cog(Crafting(bot))
