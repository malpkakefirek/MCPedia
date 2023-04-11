import discord
from discord.ext import commands
import fandom
import json
import requests
from io import BytesIO
from discord.ui import Button, View


def get_villagers():
    fandom.set_wiki("minecraft")
    page_id = fandom.search("Trading", results=1)[0][1]
    page = fandom.page(pageid=page_id)

    data = page.content
    villagers = []
    for section in data['sections']:
        for sub_section in section.get('sections', []):
            if "Java Edition sales" in sub_section['title']:
                villagers.append("Wandering trader - Java")
            elif "Bedrock Edition sales" in sub_section['title']:
                villagers.append("Wandering trader - Bedrock")
            elif "Economics" in sub_section['title']:
                continue
            else:
                villagers.append(sub_section['title'])
    print("Loaded villagers:\n" + "\n".join(villagers))
    return villagers


professions_list = get_villagers()
print(professions_list)


async def villagers(ctx):
    return [
        profession for profession in professions_list
        if ctx.value.lower() in profession.lower()
    ]


def generate_url(title, columns, data_source):
    table_data = {
        "title": title,
        "columns": columns,
        "dataSource": data_source
    }
    table_data_str = json.dumps(table_data, separators=(',', ':'))
    url = f'https://api.quickchart.io/v1/table?data={table_data_str}'
    return url


class VillagerInfoButton(Button):

    def __init__(self, name: str, **kwargs):
        super().__init__(style=discord.ButtonStyle.green, **kwargs)
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False)
        self.disabled = True
        await interaction.message.edit(view=self.view)
        file = await villager_info(self.name)
        await interaction.followup.send(file=file)


class VillagerInfoView(View):

    def __init__(self, name: str):
        super().__init__(timeout=30)
        self.add_item(
            VillagerInfoButton(name=name, label="View all trades"))


async def villager_info(profession):
    print(profession in professions_list)

    page_id = fandom.search("Trading", results=1)[0][1]
    page = fandom.page(pageid=page_id)
    data = page.content
    #print(data)
    print("Checking the info")
    url = "ERROR"
    finished = False
    for section in data['sections']:
        for sub_section in section.get('sections', []):
            my_string = sub_section['content'].split("\n")
            if "Job site block" in my_string[0] and profession in my_string[2]:
                headers = [{
                    "width": 100,
                    "title": "Level",
                    "dataIndex": "level"
                }, {
                    "width": 150,
                    "title": "Item wanted",
                    "dataIndex": "item"
                }, {
                    "width": 150,
                    "title": "Default quantity",
                    "dataIndex": "default_amount"
                }, {
                    "width": 130,
                    "title": "Price multiplier",
                    "dataIndex": "price_mult"
                }, {
                    "width": 200,
                    "title": "Item given",
                    "dataIndex": "item_given"
                }, {
                    "width": 100,
                    "title": "Quantity",
                    "dataIndex": "quantity"
                }, {
                    "width": 200,
                    "title": "Trades until disabled",
                    "dataIndex": "max_trades"
                }, {
                    "width": 200,
                    "title": "XP to villager",
                    "dataIndex": "xp"
                }]
                title = my_string[2]

                data_source = []
                row = {}
                level_now = "Novice"
                row[headers[0]['dataIndex']] = level_now
                index = 0
                for i, value in enumerate(my_string[12:]):
                    if value.strip() == "":
                        continue
                    if value.strip() in [
                            "Novice", "Apprentice", "Journeyman", "Expert",
                            "Master"
                    ]:
                        level_now = value.strip()
                    else:
                        if index == 7:
                            index = 0
                            data_source.append(row)
                            row = {}
                            row[headers[index]['dataIndex']] = level_now
                        #
                        row[headers[index + 1]['dataIndex']] = value.strip()
                        #
                        index = index + 1

                data_source.append(row)  # Append the last row

                url = generate_url(title, headers, data_source)
                #print(f"\n{title}\n{url}\n")
                finished = True
                break
        if finished:
            break

    response = requests.get(url, timeout=10)
    with BytesIO(response.content) as image_binary:
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='villager_trade.png')
        return file
    #await ctx.respond(url)


async def find_who_trades_this(ctx, profession):
    if (profession in professions_list):
        ctx.respond(profession + " CANNOT be traded with any villager")

    page_id = fandom.search("Trading", results=1)[0][1]
    page = fandom.page(pageid=page_id)
    data = page.content

    item = profession
    name = "ERROR"
    finished = False
    for section in data['sections']:
        for sub_section in section.get('sections', []):
            my_string = sub_section['content'].split("\n")
            #print(my_string[12:])
            if item in my_string[11:]:
                name = sub_section['title']
                finished = True
        if finished:
            break
    embed = discord.Embed(
        title=f"{name} is the villager that has a trade using {item}",
        color=discord.Color.green())
    view = VillagerInfoView(name)
    await ctx.respond(embed=embed, view=view)
    #await ctx.respond(msg + " has ")
    pass


#Main class
class Villager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        fandom.set_wiki("minecraft")
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @commands.slash_command(
        name="villager",
        description=
        "Choose the information you want to get about a villager profession",
    )
    async def villager(
        self,
        ctx,
        choice: discord.commands.Option(
            str,
            description="Choose the information you want to get",
            choices=["Villager info", "Find who trades this item"],
            required=True,
        ),
        profession: discord.commands.Option(
            str,
            description="Enter the villager profession",
            autocomplete=villagers,
            required=True,
        ),
    ):
        await ctx.defer()
        if choice == ctx.command.options[0].choices[0].name:
            file = await villager_info(profession)
            await ctx.respond(file=file)
        elif choice == ctx.command.options[0].choices[1].name:
            await find_who_trades_this(ctx, profession)
        else:
            await ctx.respond("Error")


def setup(bot):
    bot.add_cog(Villager(bot))
