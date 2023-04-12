import re
from io import BytesIO

import discord
import fandom
import requests
from PIL import Image
from bs4 import BeautifulSoup


def createCraftingGif(soup):
    # Get input items
    sprites = []
    input_slots = soup.find_all('span', class_='mcui-input')[0]
    slots = input_slots.find_all('span', class_='invslot')
    for slot in slots:
        sprite = slot.find_all('span', class_='sprite inv-sprite')
        # Slot is empty
        if len(sprite) == 0:
            sprites.append("---")
            continue
        sprites.append(sprite)

    # Get output item
    output_slots = soup.find_all('span', class_='mcui-output')[0]
    slots = output_slots.find_all('span', class_='invslot')
    for slot in slots:
        sprite = slot.find_all('span', class_='sprite inv-sprite')
        # Slot is empty
        if len(sprite) == 0:
            sprites.append("---")
            continue
        sprites.append(sprite)

    # Create a new blank image to hold the combined sprites
    sprite_size = 32  # size of each sprite
    item_offset = 4  # offset between item slots
    background_size = (256, 132)
    combined_image = Image.new('RGBA', background_size, (0, 0, 0, 0))

    # Load the crafting GUI background image
    background_url = "./images/crafting_gui.jpg"
    background = Image.open(background_url)

    # Add the crafting GUI background as the base layer
    combined_image.paste(background, (0, 0))

    # Download the spritesheet
    spritesheet_url = "https://static.wikia.nocookie.net/minecraft_gamepedia/images/4/44/InvSprite.png/revision/latest?cb=20230403195242&version=1680551568140&format=original"
    response = requests.get(spritesheet_url, timeout=10)
    spritesheet = Image.open(BytesIO(response.content))

    # Create a new list to store the sprite images for each item slot
    item_sprites = [[] for i in range(10)]

    # Loop through the sprites and append each one to its corresponding item slot
    for i, sprite_list in enumerate(sprites):
        if sprite_list == '---':
            continue
        for sprite in sprite_list:
            # Extract the sprite's position in the spritesheet to crop them
            style = sprite['style']
            position_match = re.search(r'background-position:\s*(-?\d+)px\s*(-?\d+)px', style)
            x, y = map(int, position_match.groups())
            x = abs(x)
            y = abs(y)
            sprite_image = spritesheet.crop((x, y, x + sprite_size, y + sprite_size))

            # Append the sprite image to the corresponding item slot
            item_sprites[i].append(sprite_image)

    # Calculate the number of frames in the animation
    # (use the length of the item slot with the most sprites)
    num_frames = max(len(item_sprite) for item_sprite in item_sprites)
    cycle_frames = []
    # Create a new list to store the sprite images for each frame of the animation
    for i in range(num_frames):
        frame_image = Image.new('RGBA', background.size, (0, 0, 0, 0))
        # Paste the crafting GUI background onto the frame
        frame_image.paste(background, (0, 0))
        for j, item_sprite in enumerate(item_sprites):
            if not item_sprite:
                continue
            # Calculate the position of the item sprite in the item slot
            if j == 9:  # Output slot
                item_x = 202
                item_y = 50
            else:   # Input slots
                row = j // 3
                col = j % 3
                item_x = col * (sprite_size + item_offset) + item_offset + 10
                item_y = row * (sprite_size + item_offset) + item_offset + 10
            # Paste the corresponding sprite image onto the frame
            # (use `i % len(item_sprite)` to cycle through the sprites)
            frame_image.alpha_composite(item_sprite[i % len(item_sprite)], dest=(item_x, item_y))
        cycle_frames.append(frame_image)
        
    # Save the frames to a BytesIO object
    gif_bytes = BytesIO()
    cycle_frames[0].save(
        gif_bytes,
        format='gif',
        save_all=True,
        append_images=cycle_frames[1:],
        duration=1500,
        loop=0
    )
    gif_bytes.seek(0)
    # Create a discord.File object from the BytesIO object and send it
    file = discord.File(gif_bytes, filename='crafting_animation.gif')
    return file


class Crafting(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        fandom.set_wiki("minecraft")
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(
        name = "crafting",
        description = "Lookup a crafting recipe for an item",
    )
    async def crafting(
        self, 
        ctx, 
        item: discord.commands.Option(
            str,
            description = "Shows crafting",
            required = True,
        ),
    ):
        await ctx.defer()
        page_id = fandom.search(item, results=1)[0][1]
        page = fandom.page(pageid=page_id)

        crafting_exists = 'Crafting' in page.sections
        if not crafting_exists:
            exists_text = "Crafting of " + page.title.lower() + " does not exist"
            await ctx.respond(exists_text)
            return

        html = page.html
        soup = BeautifulSoup(html, 'html.parser')

        file = createCraftingGif(soup)
        await ctx.respond(file=file)
        return

def setup(bot):
    bot.add_cog(Crafting(bot))
