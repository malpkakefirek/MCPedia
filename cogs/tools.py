import json
import discord
import math


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
            print(height)
            print(h)
            if height in h:
                await ctx.respond(f"Falling from {height} blocks takes {d} damage")
                return

        # embed = discord.Embed(
        #     title=f'{amount} items equals to:',
        #     color=0x3498db  # blue color
        # )


def setup(bot):
    bot.add_cog(Tools(bot))
