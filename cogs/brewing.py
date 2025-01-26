import discord


class Brewing(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(
        name="brewing",
        description="Quickly check all brewing recipes",
    )
    async def brewing(
        self,
        ctx
    ):
        embed = discord.Embed(
            # title=f'{amount} items equals to:',
            color=discord.Color.purple(),
            image="https://minecraft.wiki/images/Minecraft_brewing_en.png"
        )

        await ctx.respond(embed=embed)
        return


def setup(bot):
    bot.add_cog(Brewing(bot))
