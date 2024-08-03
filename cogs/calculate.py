import discord
import math


class Calculate(discord.Cog):

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


def setup(bot):
    bot.add_cog(Calculate(bot))
