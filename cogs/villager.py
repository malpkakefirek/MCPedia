import re
import discord
from discord.ext import commands
import fandom
import json
import requests
from io import BytesIO
from discord.ui import Button, View
from bs4 import BeautifulSoup
from PIL import Image


def get_villagers():
    fandom.set_wiki("minecraft")
    page_id = fandom.search("Trading", results=1)[0][1]
    page = fandom.page(pageid=page_id)

    data = page.content
    villagers = []
    for section in data['sections']:
        if "Bedrock Edition offers" in section['title']:  # Skip bedrock villagers until they get fixed.
            continue
        for sub_section in section.get('sections', []):
            # Skip wandering traders until they get fixed.
            if "Java Edition sales" in sub_section['title']:
                # villagers.append("Wandering trader - Java")
                continue
            elif "Bedrock Edition sales" in sub_section['title']:
                # villagers.append("Wandering trader - Bedrock")
                continue
            if "Economics" in sub_section['title']:
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
        "dataSource": data_source,
    }
    table_data_str = json.dumps(table_data, separators=(',', ':'))
    #options:
    options = """&options={"paddingVertical":20,"paddingHorizontal":20,"spacing":10,"backgroundColor":"%23eee","fontFamily":"mono","cellHeight":60}"""
    #
    url = f'https://api.quickchart.io/v1/table?data={table_data_str}{options}'
    return url


class VillagerInfoButton(Button):

    def __init__(self, name: str, **kwargs):
        super().__init__(style=discord.ButtonStyle.green, **kwargs)
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False)
        self.disabled = True
        await interaction.message.edit(view=self.view)
        files = await villager_info(self.name)
        if len(files) != 2:
            await interaction.followup.send("ERROR!")
            return
        embed = discord.Embed(
            title = self.name,
            color = discord.Color(43520),    # 00AA00 (dark green)
        )
        embed.set_image(url=f"attachment://{files[0].filename}")
        embed.set_thumbnail(url=f"attachment://{files[1].filename}")
        await interaction.followup.send(embed=embed, files=files)


class VillagerInfoView(View):
    def __init__(self, name: str):
        super().__init__(timeout=30)
        self.add_item(VillagerInfoButton(name=name, label="View all trades"))


async def villager_info(profession):
    page_id = fandom.search("Trading", results=1)[0][1]
    page = fandom.page(pageid=page_id)
    html = page.html
    soup = BeautifulSoup(html, 'html.parser')

    start = None
    for h3 in soup.find_all("h3"):
        span = h3.find("span")
        if not span:
            continue
        if span.get_text() == profession:
            start = h3

    spritesheet_url = "https://static.wikia.nocookie.net/minecraft_gamepedia/images/d/df/BlockCSS.png/revision/latest?cb=20230409162508&version=1681057515007&format=original"
    response = requests.get(spritesheet_url, timeout=10)
    spritesheet = Image.open(BytesIO(response.content))
    
    # Find the table corresponding to the profession
    table = None
    job_site_style = None
    for tag in start.next_siblings:
        if tag.name == "p":
            job_site_style = tag.find('span', 'sprite block-sprite')['style']
        if tag.name == "table":
            table = tag
            break  # Stop after finding table

    # create job site block image
    position_match = re.search(r'background-position:\s*(-?\d+)px\s*(-?\d+)px', job_site_style)
    x, y = map(int, position_match.groups())
    x = abs(x)
    y = abs(y)
    sprite_size = 16
    job_site_image = spritesheet.crop((x, y, x + sprite_size, y + sprite_size))

    # pass job site block image into a discord.File object
    bytes_image = BytesIO()
    job_site_image.save(bytes_image, format='PNG')
    bytes_image.seek(0)
    job_site_file = discord.File(fp=bytes_image, filename='job_site_block.png')
    
    # extract the title from the data-description attribute of the table tag
    title = table['data-description']

    # find the table header row
    columns = [
        {
            "width": 100,
            "title": "Level",
            "dataIndex": "level"
        }, {
            "width": 150,
            "title": "Item wanted",
            "dataIndex": 0
        }, {
            "width": 140,
            "title": "Amount",
            "dataIndex": 1
        }, {
            "width": 175,
            "title": "Item given",
            "dataIndex": 3
        }, {
            "width": 80,
            "title": "Amount",
            "dataIndex": 4
        }, {
            "width": 185,
            "title": "Trades until disabled",
            "dataIndex": 5
        }
    ]

    # find table body rows
    body_rows = table.find('tbody').find_all('tr')
    
    # extract cell data
    data = []
    current_level = None
    for row in body_rows[2:]:
        try:
            if not row.find('th').get_text().strip().isnumeric():
                current_level = row.find('th').get_text().strip()
        except:
            pass

        cells = row.find_all('td')
        item_cell = cells[0]
        item_links = item_cell.find_all('a')
        
        # Single item
        if len(item_links) == 1:
            data.append('-')
            data.append({
                'level': current_level,
                **{i: re.sub('\[note [0-9]+\]', '', td.text.strip()) for i, td in enumerate(cells) if i not in [2, 6]}
            })
            continue

        # Multiple items with the same name
        data.append('-')
        data.append({
            'level': current_level,
            0: "\n".join([item.text for item in item_links]).strip(),
            1: "\n".join([child for child in cells[1].children if not child.name]).replace('\u2013', '–').strip(),
            **{j+2: re.sub('\[note [0-9]+\]', '', cells[j+2].text.strip()) for j in range(len(cells)-2) if j+2 not in [2, 6]}
        })

    print(title)
    print(columns)
    print(data)
    url = generate_url(title, columns, data)
    
    response = requests.get(url, timeout=10)
    with BytesIO(response.content) as image_binary:
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='villager_trade.png')
    return (file, job_site_file)


#Main class
class Villager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        fandom.set_wiki("minecraft")
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    trade_group = discord.commands.SlashCommandGroup(
        name = "trades",
        description = "Commands about trading",
    )

    @trade_group.command(
        name = "villager",
        description = "Get trades of a Villager",
    )
    async def villager(
        self,
        ctx,
        # choice: discord.commands.Option(
        #     str,
        #     description = "Choose the information you want to get",
        #     choices = ["Villager info", "Find who trades this item"],
        #     required = True,
        # ),
        profession: discord.commands.Option(
            str,
            description = "Enter the villager profession",
            autocomplete = villagers,
            required = True,
        ),
    ):
        if profession not in professions_list:
            await ctx.respond(f"Couldn't find `{profession}`! Make sure to choose from the autocomplete list.")
            return
        if profession in ("Nitwit", "Unemployed villager"):
            await ctx.respond(f"`{profession}` doesn't have any trades :(")
            return
        await ctx.defer()

        files = await villager_info(profession)
        if len(files) != 2:
            await ctx.respond("ERROR!")
            return
        embed = discord.Embed(
            title = profession,
            color = discord.Color(43520),    # 00AA00 (dark green)
        )
        embed.set_image(url=f"attachment://{files[0].filename}")
        embed.set_thumbnail(url=f"attachment://{files[1].filename}")
        await ctx.respond(files=files, embed=embed)


    @trade_group.command(
        name = "item",
        description = "Get the Villager that trades a particular item",
    )
    async def item(
        self,
        ctx,
        item: discord.commands.Option(
            str,
            description = "Enter the villager profession",
            # autocomplete = villagers,
            required = True,
        ),
    ):
        await ctx.defer()
        page_id = fandom.search("Trading", results=1)[0][1]
        page = fandom.page(pageid=page_id)
        data = page.content

        name = "ERROR"
        finished = False
        for section in data['sections']:
            for sub_section in section.get('sections', []):
                my_string = sub_section['content'].split("\n")
                #print(my_string[12:])
                if item.lower() in [string.lower() for string in my_string[11:]]:
                    name = sub_section['title']
                    finished = True
            if finished:
                break

        if name == "ERROR":
            embed = discord.Embed(
                title = f"Couldn't find a villager that has a trade using {item}",
                color = discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return

        embed = discord.Embed(
            title = f"{name} is the villager that has a trade using {item.title()}",
            color = discord.Color.green()
        )
        view = VillagerInfoView(name)
        await ctx.respond(embed=embed, view=view)


def setup(bot):
    bot.add_cog(Villager(bot))
