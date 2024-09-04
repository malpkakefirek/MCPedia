import re
import discord
from discord.ext import commands
import json
import requests
from io import BytesIO

from mediawiki import MediaWiki
from discord.ui import Button, View
from bs4 import BeautifulSoup
# from PIL import Image

wikipedia = MediaWiki(
    "https://minecraft.wiki/api.php",
    user_agent="MCPediaDiscordBot/2.1 (https://minecraft.wiki/w/User:Malpkakefirek; https://github.com/malpkakefirek) pymediawiki/0.7.3"
)


def get_villagers():
    page_id = wikipedia.search("Trading", results=1)[0]
    page = wikipedia.page(page_id)

    print(page.table_of_contents)
    villagers = []
    for section_title in page.table_of_contents:
        # if "Bedrock Edition offers" in section_title:  # Skip bedrock villagers until they get fixed.
        #     continue
        if section_title not in ("Non-trading villagers", "Trade offers", "Wandering trader sales"):
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
    # options:
    options = r'&options={"paddingVertical":20,"paddingHorizontal":20,"spacing":10,"backgroundColor":"%2359b731","fontFamily":"mono","cellHeight":40}'  # "%23" = "#"
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
        file, job_site_name = await villager_info(self.name)
        if file is None or job_site_name is None:
            await interaction.followup.send("ERROR!")
            return
        text = '\n'.join((
            f"## {self.name}",
            f"{self.name} needs \"{job_site_name}\""
        ))
        await interaction.respond(
            text,
            file=file
        )


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

    # Find the table corresponding to the profession
    table = None
    for tag in start.next_siblings:
        if tag.name == "p":
            job_site_name = tag.find('a')['title']
        if tag.name == "div":
            table = tag.find('table')
            if table is None:
                continue
            break  # Stop after finding table

    title = table.find('th').string
    columns = [
        {
            "width": 150,
            "title": "Level",
            "dataIndex": "level"
        }, {
            "width": 250,
            "title": "Item wanted",
            "dataIndex": 0
        }, {
            "width": 300,
            "title": "Item given",
            "dataIndex": 1
        }, {
            "width": 150,
            "title": "Trades in stock",
            "dataIndex": 2
        }
    ]

    # find table body rows
    body_rows = table.find('tbody').find_all('tr')

    # extract cell data
    data = []
    current_level = None
    for row in body_rows[3:]:
        try:
            if not row.find('th').get_text().strip().isnumeric():
                current_level = row.find('th').get_text().strip()
        except Exception:
            pass

        # only include items, and trades in stock [2,3,4]
        cells = row.find_all('td')[2:5]
        if not cells:
            continue

        data.append('-')
        data.append({
            'level': current_level,
            **{
                i: re.sub(r'\[t [0-9]+\]', '', td.text.strip()).replace('+', ' %2B')
                for i, td in enumerate(cells)
            }
        })

    url = generate_url(title, columns, data)
    response = requests.get(url, timeout=10)
    with BytesIO(response.content) as image_binary:
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='villager_trade.png')
    return (file, job_site_name)


# Main class
class Villager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    trade_group = discord.commands.SlashCommandGroup(
        name="trades",
        description="Commands about trading",
    )


    @trade_group.command(
        name="villager",
        description="Get trades of a Villager",
    )
    async def villager(
        self,
        ctx,
        profession: discord.commands.Option(
            str,
            description="Enter the villager profession",
            autocomplete=villagers,
            required=True,
        ),
    ):
        if profession not in professions_list:
            await ctx.respond(f"Couldn't find `{profession}`! Make sure to choose from the autocomplete list.")
            return
        if profession in ("Nitwit", "Unemployed villager"):
            await ctx.respond(f"`{profession}` doesn't have any trades :(")
            return
        await ctx.defer()

        file, job_site_name = await villager_info(profession)
        if file is None or job_site_name is None:
            await ctx.respond("ERROR!")
            return

        text = '\n'.join((
            f"## {profession}",
            f"{profession} needs \"{job_site_name}\""
        ))
        await ctx.respond(
            text,
            file=file
        )



    @trade_group.command(
        name="item",
        description="Get the Villager that trades a particular item",
    )
    async def item(
        self,
        ctx,
        item: discord.commands.Option(
            str,
            description="Enter an item you want to search for",
            # autocomplete=items,    # maybe parse a list of traded items on bot start?
            required=True,
        ),
    ):
        await ctx.defer()
        page_id = wikipedia.search("Trading", results=1)[0]
        page = wikipedia.page(page_id)

        name_item = dict()
        soup = BeautifulSoup(page.html, 'html.parser')
        note_pattern = r"\[t \d+\]"
        for subsection_title in page.table_of_contents['Trade offers']:    # Skipping Wandering Traders
            print(subsection_title)
            my_string = []
            table = soup.find(
                'th',
                attrs={'data-description': subsection_title}
            ).parent.parent
            if not table:
                continue
            # Convert table to list of strings
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if cells is None:
                    continue
                if len(cells) < 4:
                    continue

                cell_contents = []
                item_wanted = cells[2].stripped_strings
                for string in item_wanted:
                    if not re.search(note_pattern, string):
                        cell_contents.append(re.sub(r'\[t [0-9]+\]', '', string))
                my_string.append(' '.join(cell_contents))

                cell_contents = []
                item_given = cells[3].stripped_strings
                for string in item_given:
                    if not re.search(note_pattern, string):
                        cell_contents.append(re.sub(r'\[t [0-9]+\]', '', string))
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
                title=f"Couldn't find a villager that has a trade using `{item}`",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)
            return

        listing = ""
        for villager, trade_items in name_item.items():
            listing += f"**{villager}** trades `{', '.join(trade_items.keys())}`\n"

        embed = discord.Embed(
            title=f"Here are your matches for `{item}`",
            color=discord.Color.green(),
            description=listing.strip()
        )

        villagers = name_item.keys()
        view = VillagerInfoView(villagers)
        await ctx.respond(embed=embed, view=view)


def setup(bot):
    bot.add_cog(Villager(bot))
