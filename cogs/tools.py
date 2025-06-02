import json
import discord
import math
import uuid
import hashlib
import aiohttp
import asyncio


def generate_minecraft_offline_uuid(username: str) -> uuid.UUID:
    name = f"OfflinePlayer:{username}"
    md5_hash = hashlib.md5(name.encode('utf-8')).digest()
    # Set the UUID version to 3 (name-based MD5)
    md5_hash = bytearray(md5_hash)
    md5_hash[6] = (md5_hash[6] & 0x0F) | 0x30  # Version 3
    md5_hash[8] = (md5_hash[8] & 0x3F) | 0x80  # Variant RFC 4122
    return uuid.UUID(bytes=bytes(md5_hash))


async def get_minecraft_profile(username: str) -> str:
    url = f"https://api.minecraftservices.com/minecraft/profile/lookup/name/{username}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None


class Tools(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(
        name="calculate",
        description="Convert items to stacks",
    )
    async def calculate(
        self,
        ctx,
        amount: discord.commands.Option(
            int,
            description="Amount of items",
            required=True,
        ),
        stack_size: discord.commands.Option(
            int,
            description="Stack size",
            choices=[64, 16, 1],
            default=64,
        )
    ):
        stacks = math.floor(amount / stack_size)
        remaining = amount - stacks * stack_size
        chests = round(amount / (stack_size * 27), 2)
        doubleChests = round(amount / (stack_size * 27 * 2), 2)

        embed = discord.Embed(
            title=f'{amount} items equals to:',
            color=0x3498db  # blue color
        )
        embed.add_field(name=f'Stacks (x{stack_size})', value=stacks, inline=True)
        embed.add_field(name='Remaining Items', value=remaining, inline=True)
        embed.add_field(name='Chests / Shulkers', value=chests, inline=False)
        embed.add_field(name='Double Chests', value=doubleChests, inline=False)

        await ctx.respond(embed=embed)
        return


    @discord.slash_command(
        name="fall",
        description="Calculate fall damage",
    )
    async def fall(
        self,
        ctx,
        damage: discord.commands.Option(
            int,
            description="Amount of damage (1 heart = 2 damage)",
            min_value=1,
            max_value=20,
            default=0,
        ),
        height: discord.commands.Option(
            float,
            description="Height from which the entity is falling (rounded to 0.5 blocks)",
            min_value=3,
            max_value=23.5,
            default=0,
        )
    ):
        if (damage == 0 and height == 0) or (damage != 0 and height != 0):
            await ctx.respond(
                "You have to input one of: damage or height",
                ephemeral=True
            )
            return

        with open('fall_data.json') as f:
            fall_data = json.load(f)

        if damage != 0:
            heights = fall_data[str(damage)]
            if not heights:
                await ctx.respond(f"It's impossible to take {damage} damage from falling :(")
                return
            await ctx.respond(f"You take {damage} damage from these heights:\n{', '.join(heights)}")
            return

        height = round(2 * height) / 2  # round to 0.5
        if height.is_integer():  # remove trailing ".0"
            height = int(height)
        height = str(height)

        for d, h in fall_data.items():
            if height in h:
                await ctx.respond(f"Falling from {height} blocks takes {d} damage")
                return

        # embed = discord.Embed(
        #     title=f'{amount} items equals to:',
        #     color=0x3498db  # blue color
        # )


    @discord.slash_command(
        name="uuid",
        description="Get UUID of a Minecraft player",
    )
    async def uuid(
        self,
        ctx,
        username: discord.commands.Option(
            str,
            description="Username of the player",
            required=True,
        )
    ):
        hyphen_offline_uuid = str(generate_minecraft_offline_uuid(username))
        clean_offline_uuid = hyphen_offline_uuid.replace('-', '')

        online_profile = await get_minecraft_profile(username)
        if online_profile is None:
            clean_online_uuid = None
            hyphen_online_uuid = None
        else:
            clean_online_uuid = online_profile['id']
            hyphen_online_uuid = f"{clean_online_uuid[0:8]}-{clean_online_uuid[8:12]}-{clean_online_uuid[12:16]}-{clean_online_uuid[16:20]}-{clean_online_uuid[20:]}"
            username = online_profile['name']

        description = ""
        description += f":green_circle: **Online UUID:** `{clean_online_uuid}`\n" if clean_online_uuid else ""
        description += f":green_circle: **Online UUID hyphenated:** `{hyphen_online_uuid}`\n" if hyphen_online_uuid else ""
        description += f":white_circle: **Offline UUID:** `{clean_offline_uuid}`\n"
        description += f":white_circle: **Offline UUID hyphenated:** `{hyphen_offline_uuid}`\n"
        description.strip()

        embed = discord.Embed(
            title=f"{username}" if clean_online_uuid else f"{username} (Offline)",
            description=description,
            color=0x3498db  # blue color
        )

        if clean_online_uuid:
            embed.set_thumbnail(url=f"https://api.mineatar.io/face/{clean_online_uuid}")
        else:
            embed.set_thumbnail(url="https://api.mineatar.io/face/00000000000000000000000000000000")

        await ctx.respond(embed=embed)
        return


def setup(bot):
    bot.add_cog(Tools(bot))
