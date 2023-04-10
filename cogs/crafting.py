import re
import discord
import fandom
import requests
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup

class Crafting(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        fandom.set_wiki("minecraft")
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(name="crafting")
    async def crafting(
        self, 
        ctx, 
        item: discord.commands.Option(
            str,
            description="Shows crafting",
            required=True,
        ),
    ):
        await ctx.defer()
        page_id = fandom.search(item, results=1)[0][1]
        page = fandom.page(pageid=page_id)
        # data = page.content
        exists_text = "Crafting of " + page.title.lower() + " does not exist"
    
        # placeholder = "NULL"
        # crafting_exists = False
        # for section in data['sections']:
        #     for sub_section in section.get('sections', []):
        #         if 'Crafting' in sub_section['content']:
        #           crafting_exists = True
        #           placeholder = sub_section['content']
        #           break
        #     if (crafting_exists):
        #         break

        crafting_exists = 'Crafting' in page.sections
        
        if crafting_exists:
            html = page.html
            soup = BeautifulSoup(html, 'html.parser')
            
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
                sprites.append(sprite[0])
            
            # Get output item
            output_slots = soup.find_all('span', class_='mcui-output')[0]
            slots = output_slots.find_all('span', class_='invslot')
            for slot in slots:
                sprite = slot.find_all('span', class_='sprite inv-sprite')
                # Slot is empty
                if len(sprite) == 0:
                    sprites.append("---")
                    continue
                sprites.append(sprite[0])
            
            # Create a new blank image to hold the combined sprites
            sprite_size = 32  # size of each sprite
            item_offset = 4  # offset between item slots
            background_size = (256, 132)
            combined_image = Image.new('RGBA', background_size, (0, 0, 0, 0))
            
            # Load the crafting GUI background image
            background_url = "images/crafting_gui.jpg"
            background = Image.open(background_url)
            
            # Add the crafting GUI background as the base layer
            combined_image.paste(background, (0, 0))
            
            # Loop through the sprites and paste each one onto the combined image
            for i, sprite in enumerate(sprites):
                if sprite == '---':
                    continue
            
                style = sprite['style']
                # Download the spritesheet and crop the sprite image based on its position
                spritesheet_url = re.search(r'url\((.*?)\)', style).group(1)
                response = requests.get(spritesheet_url, timeout=60)
                spritesheet = Image.open(BytesIO(response.content))
            
                # extract the sprite's position in the spritesheet to crop them
                position_match = re.search(r'background-position:\s*(-?\d+)px\s*(-?\d+)px', style)
                x, y = map(int, position_match.groups())
                x = abs(x)
                y = abs(y)
                sprite_image = spritesheet.crop((x, y, x + sprite_size, y + sprite_size))
            
                # Create a mask for the sprite image
                alpha = sprite_image.getchannel('A')
                mask = Image.merge('RGBA', (alpha, alpha, alpha, alpha))
            
                # Paste the sprite image onto the combined image
                if i == 9:  # Output slot
                    item_x = 202
                    item_y = 50
                else:   # Input slots
                    row = i // 3
                    col = i % 3
                    item_x = col * (sprite_size + item_offset) + item_offset + 10
                    item_y = row * (sprite_size + item_offset) + item_offset + 10
                position = (item_x, item_y)
                combined_image.paste(sprite_image, position, mask)
                
                image_buffer = BytesIO()
                combined_image.save(image_buffer, format='PNG')
                image_buffer.seek(0)
                # create a discord.File object from the BytesIO object
                image_file = discord.File(fp=image_buffer, filename='combined_image.png')
                
            await ctx.respond(file=image_file)
            return
        else:
            await ctx.respond(exists_text)
            return

def setup(bot):
    bot.add_cog(Crafting(bot))
