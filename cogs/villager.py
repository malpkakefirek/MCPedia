import re
import discord
from discord.ext import commands
import json
import requests
from io import BytesIO

from mediawiki import MediaWiki
from discord.ui import Button, View
from bs4 import BeautifulSoup
from PIL import Image

wikipedia = MediaWiki("https://minecraft.wiki/api.php", user_agent="MCPediaDiscordBot/2.1 (https://minecraft.wiki/w/User:Malpkakefirek; https://github.com/malpkakefirek) pymediawiki/0.7.3")


def get_villagers():
    page_id = wikipedia.search("Trading", results=1)[0]
    page = wikipedia.page(page_id)

    print(page.table_of_contents)
    villagers = []
    for section_title in page.table_of_contents:
        # if "Bedrock Edition offers" in section_title:  # Skip bedrock villagers until they get fixed.
        #     continue
        if section_title not in ("Non-trading villagers", "Java Edition offers", "Wandering trader sales"):
            continue
        for sub_section_title in page.table_of_contents[section_title]:
            # Skip wandering traders until they get fixed.
            if "Java Edition sales" in sub_section_title:
                # villagers.append("Wandering trader - Java")
                continue
            if "Bedrock Edition sales" in sub_section_title:
                # villagers.append("Wandering trader - Bedrock")
                continue
            villagers.append(sub_section_title)
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
    def __init__(self, villagers: list[str]):
        super().__init__(timeout=30)
        for villager in villagers:
            self.add_item(VillagerInfoButton(name=villager, label=f"View {villager} trades"))


async def villager_info(profession):
    page_id = wikipedia.search("Trading", results=1)[0]
    page = wikipedia.page(page_id)
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
    job_site_image = None
    for tag in start.next_siblings:
        if tag.name == "p":
            job_site_name = tag.find('a')['title']
            job_site_url = "https://minecraft.wiki" + tag.find('img')['src']
            response = requests.get(job_site_url, timeout=10)
            job_site_image = Image.open(BytesIO(response.content)).convert('RGBA')
        if tag.name == "table":
            table = tag
            break  # Stop after finding table

    # create job site block image
    # position_match = re.search(r'background-position:\s*(-?\d+)px\s*(-?\d+)px', job_site_image)
    # x, y = map(int, position_match.groups())
    # x = abs(x)
    # y = abs(y)
    # sprite_size = 16
    # job_site_image = spritesheet.crop((x, y, x + sprite_size, y + sprite_size))

    # pass job site block image into a discord.File object
    bytes_image = BytesIO()
    job_site_image.save(bytes_image, format='PNG')
    bytes_image.seek(0)
    job_site_file = discord.File(fp=bytes_image, filename=f'{job_site_name}.png')
    
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

    # print(title)
    # print(columns)
    # print(data)
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
            description = "Enter an item you want to search for",
            # autocomplete = items,    # maybe parse a list of traded items on bot start?
            required = True,
        ),
    ):
        await ctx.defer()
        page_id = wikipedia.search("Trading", results=1)[0]
        page = wikipedia.page(page_id)

        name_item = dict()
        soup = BeautifulSoup(page.html, 'html.parser')
        note_pattern = r"\[note \d+\]"
        for subsection_title in page.table_of_contents['Java Edition offers']:    # Skipping Bedrock Edition and Wandering Traders
            print(subsection_title)
            my_string = []
            table = soup.find('table', attrs={'data-description': f'{subsection_title} trades'})
            if not table:
                continue
            # Convert table to list of strings
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                item_wanted = cells[0].stripped_strings
                cell_contents = []
                for string in item_wanted:
                    if not re.search(note_pattern, string):
                        cell_contents.append(string)
                my_string.append(' '.join(cell_contents))

                cell_contents = []
                item_given = cells[3].stripped_strings
                for string in item_given:
                    if not re.search(note_pattern, string):
                        cell_contents.append(string)
                        
                my_string.append(' '.join(cell_contents))
            for string in my_string:
                # # skip wandering traders
                # if subsection_title in ['Java Edition sales', 'Bedrock Edition sales']:
                #     continue
                if not (item.lower() in string.lower()):
                    continue

                if subsection_title in name_item.keys():
                    name_item[subsection_title][string.strip()] = None    # add to the dict
                else:
                    name_item[subsection_title] = {string.strip(): None}    # make a python dict (ordered, no duplicates)

        if not name_item:
            embed = discord.Embed(
                title = f"Couldn't find a villager that has a trade using `{item}`",
                color = discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return

        listing = ""
        for villager, trade_items in name_item.items():
            listing += f"**{villager}** trades `{', '.join(trade_items.keys())}`\n"
        
        embed = discord.Embed(
            title = f"Here are your matches for `{item}`",
            color = discord.Color.green(),
            description = listing.strip()
        )
        
        villagers = name_item.keys()
        view = VillagerInfoView(villagers)
        await ctx.respond(embed=embed, view=view)


def setup(bot):
    bot.add_cog(Villager(bot))
