import re
import os
from random import randint
from io import BytesIO

import discord
import fandom
import requests
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup


def is_element_visible(element):
    # Check if the element itself has "display: none" style
    style = element.get('style')
    if style and ('display: none' in style or 'display:none' in style):
        return False

    # Check if any parent element has "display: none" style
    parent = element.parent
    while parent:
        style = parent.get('style')
        if style and ('display: none' in style or 'display:none' in style):
            return False
        parent = parent.parent

    return True


def convert_animated_sprite_to_static_frame(sprite_image):
    try:
        sprite_image.seek(0)  # Go to the first frame
        return sprite_image.copy()
    except EOFError:
        return None  # Return None if there are no frames (shouldn't happen)


def get_crafting_grids_table(page_content):
    element = page_content.find(id='Crafting').parent
    crafting_grid_table = None
    while element.name != 'table':
        element = element.next
    return element


def createCraftingGifs(soup):
    # Download the spritesheet
    spritesheet_url = "https://static.wikia.nocookie.net/minecraft_gamepedia/images/4/44/InvSprite.png/revision/latest?cb=20230403195242&version=1680551568140&format=original"
    response = requests.get(spritesheet_url, timeout=10)
    spritesheet = Image.open(BytesIO(response.content))
    
    files = []
    crafting_grids_table = get_crafting_grids_table(soup)
    crafting_grids_rows = crafting_grids_table.find('tbody').find_all('tr')
    # Sometimes table header is incorrectly inside `tbody` instead of `thead` on the wiki. 
    # So remove the first row if there is no `thead` in the table
    if crafting_grids_table.find('thead') is None:
        crafting_grids_rows.pop(0)
    for crafting_grid_row in crafting_grids_rows:
        crafting_grid = crafting_grid_row.find('span', class_='mcui-Crafting_Table')
        # Skip if crafting grid is hidden on wiki
        if not is_element_visible(crafting_grid):
            continue

        # Skip if not on Java Edition (might cause problems if there are other `sup` texts not relevant to game versions)
        columns = crafting_grid_row.find_all('td')
        if len(columns) >= 3:
            description_element = columns[2]
            sup_text = description_element.find('sup')
            if sup_text and 'Java Edition' not in sup_text.text and 'JE' not in sup_text.text:
                print("Skipping gif, because not on Java Edition")
                continue
        
        sprites = []
        # Get input items
        input = crafting_grid.find('span', class_='mcui-input')
        slots = input.find_all('span', class_='invslot')
        for slot in slots:
            sprite_ordered_list = []
            
            # Go the next slot, if slot is empty (air)
            if len(slot.contents) > 0:
                element = slot.contents[0]
            else:
                sprites.append("---")
                continue

            # Get all sprites, while keeping order
            while element is not None:
                # Single item
                if element['class'][0] == 'invslot-item':
                    item = element.find('span', class_='sprite inv-sprite')
                    if not item:
                        item = element.find('img')
                    sprite_ordered_list.append(item)
                # Multiple items with random combination
                elif element['class'][0] == 'animated-subframe':
                    items = element.find_all('span', class_='sprite inv-sprite')
                    if len(items) == 0:
                        items = element.find_all('img')
                    sprite_ordered_list.append(items)
                element = element.next_sibling

            # Get random subframe starts and longest list length
            random_indexes = dict()
            max_index = 1
            for i in range(len(sprite_ordered_list)):
                element = sprite_ordered_list[i]
                if isinstance(element, list):
                    random_index = randint(0, len(element) - 1)
                    random_indexes[i] = random_index
                    if (len(element) > max_index):
                        max_index = len(element)
            # Convert order to animation order with random subframe starts
            animation_ordered_list = []
            for i in range(max_index):
                for j in range(len(sprite_ordered_list)):
                    element = sprite_ordered_list[j]
                    if isinstance(element, list):
                        animation_ordered_list.append(element[(random_indexes[j] + i) % len(element)])
                    else:
                        animation_ordered_list.append(element)
            sprites.append(animation_ordered_list)
    
        # Get output item
        output = crafting_grid.find('span', class_='mcui-output')
        slots = output.find_all('span', class_='invslot')
        for slot in slots:
            stacksize_element = slot.find('span', class_='invslot-stacksize')
            stacksize = int(stacksize_element.text) if stacksize_element else None
        
            sprite = slot.find_all('span', class_='sprite inv-sprite')
            img_item = slot.find_all('img')
            if len(img_item) > 0:
                sprite = img_item
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
    
        # Create a new list to store the sprite images for each item slot
        item_sprites = [[] for i in range(10)]
    
        # Loop through the sprites and append each one to its corresponding item slot
        for i, sprite_list in enumerate(sprites):
            if sprite_list == '---':
                continue
            for sprite in sprite_list:
                # If item is animated
                if 'data-src' in sprite.attrs:
                    sprite_url = sprite['data-src']
                    response = requests.get(sprite_url, timeout=10)
                    sprite_image = convert_animated_sprite_to_static_frame(Image.open(BytesIO(response.content))).convert('RGBA')
                elif 'src' in sprite.attrs:
                    sprite_url = sprite['src']
                    response = requests.get(sprite_url, timeout=10)
                    sprite_image = convert_animated_sprite_to_static_frame(Image.open(BytesIO(response.content))).convert('RGBA')
                else:
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
        
        # Create a new list to store the sprite images with numbers for each frame of the animation
        frames_with_numbers = []
        # Add the number to each frame of the animation
        for frame in cycle_frames:
            frame_with_numbers = frame.copy()
            draw = ImageDraw.Draw(frame_with_numbers)
            font = ImageFont.truetype("fonts/MinecraftRegular.ttf", 18)  # You can choose a font and size that suits your needs
    
            if stacksize is not None:
                number_x = 225
                number_y = 68
                # Add a black border to the stacksize
                border_size = 1
                draw.text((number_x - border_size, number_y), str(stacksize), font=font, fill='black')
                draw.text((number_x + border_size, number_y), str(stacksize), font=font, fill='black')
                draw.text((number_x, number_y - border_size), str(stacksize), font=font, fill='black')
                draw.text((number_x, number_y + border_size), str(stacksize), font=font, fill='black')
                # Draw stacksize
                draw.text((number_x, number_y), str(stacksize), fill='white', font=font)
        
            frames_with_numbers.append(frame_with_numbers)
        
        # Save the frames to a BytesIO object
        gif_bytes = BytesIO()
        frames_with_numbers[0].save(
            gif_bytes,
            format='gif',
            save_all=True,
            append_images=frames_with_numbers[1:],
            duration=1500,
            loop=0
        )
        gif_bytes.seek(0)
        # Create a discord.File object from the BytesIO object and send it
        file = discord.File(gif_bytes, filename='crafting_animation.gif')
        files.append(file)
    return files


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

        try:
            page.content
        except AttributeError:
            await ctx.respond(f"Couldn't find anything for `{item}`")
            return

        if 'Crafting' not in page.sections:
            exists_text = "Crafting of `" + page.title.lower() + "` does not exist"
            await ctx.respond(exists_text)
            return

        html = page.html
        soup = BeautifulSoup(html, 'html.parser')

        files = createCraftingGifs(soup)
        while len(files) > 10:
            await ctx.respond(files=files[0:9])
            files = files[10:]
        await ctx.respond(files=files)
        return

def setup(bot):
    bot.add_cog(Crafting(bot))
