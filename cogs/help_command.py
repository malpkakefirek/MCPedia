import discord
from discord.errors import Forbidden
from replit import db

"""
« HELP COG »
Original concept by Jared Newsom (AKA Jared M.F.)
https://gist.github.com/StudioMFTechnologies/ad41bfd32b2379ccffe90b0e34128b8b

Rewritten and optimized by github.com/nonchris
https://gist.github.com/nonchris/1c7060a14a9d94e7929aa2ef14c41bc2

Rewritten again and modified for my own purposes by github.com/malpkakefirek | Malpkakefirek#0001
"""

async def send_embed(ctx, embed):
    """
    For help visit: https://youtu.be/dQw4w9WgXcQ
    """
    try:
        await ctx.respond(embed=embed)
    except Forbidden:
        try:
            await ctx.send("I can't send embeds. Check my pemissions :)")
        except Forbidden:
            await ctx.author.send(
                f"Hey, it looks like I can't send embeds in channel {ctx.channel.name} in {ctx.guild.name}\n"
                "Could you notify the owner about this? :slight_smile: ",
                embed=embed
            )


class Help(discord.Cog):
    """Help cog"""
    
    def __init__(self, bot):
        self.bot = bot
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(name="help")
    async def help_slash(self, ctx, *, input: discord.commands.Option(str, "A command or category, you want more info on", default=None)):
        """Helpful if you forget how to use commands"""

        prefix = "/"
        secondary_prefix = "m!"
        version = "0.1"
        owner_ids = db['permitted']

        # checks if cog parameter was given
        # if not: sending all modules and commands not associated with a cog
        if not input:
            # checks if owner is on this server - used to 'tag' owner

            # starting to build embed
            emb = discord.Embed(
                title=':sparkles: __All commands__ :sparkles:',
                color=discord.Color.teal(),
                description=f'Use `{prefix}help <command/category>` to get additional info about a command/category'
            )

            # iterating through cogs, gathering descriptions
            for cog in self.bot.cogs:

                commands_desc = ''
                temp_cog = self.bot.get_cog(cog)
                # iterating through commands in cog
                for command in temp_cog.get_commands():
                    # if command in a cog
                    # listing command if cog name is None and command isn't hidden
                    try:
                        for subcommand in command.subcommands:
                            commands_desc += f'`{prefix}{subcommand.qualified_name or subcommand.name}` - {subcommand.description if subcommand.description else "No description provided"}\n'
                    except:
                        try:
                            if not command.hidden or int(ctx.author.id) in owner_ids:
                                commands_desc += f'`{secondary_prefix}{command.name}` - {command.description or "No description provided"}\n'
                        except:
                            commands_desc += f'`{prefix}{command.name}` - {command.description or "No description provided"}\n'

                if commands_desc:
                    emb.add_field(
                        name=f"Category {cog.title()}",
                        value=commands_desc,
                        inline=False
                    )

            commands_desc = ''
            for command in self.bot.walk_application_commands():
                # if command not in a cog
                # listing command if cog is None
                if not command.cog:
                    commands_desc += f'`{prefix}{command.qualified_name}` - {command.description or "No description provided"}\n'
            for command in self.bot.walk_commands():
                # if command not in a cog
                # listing command if cog is None and command isn't hidden
                if (not command.hidden or int(ctx.author.id) in owner_ids) and not command.cog:
                    commands_desc += f'`{secondary_prefix}{command.name}` - {command.description or "No description provided"}\n'

            if commands_desc:
                emb.add_field(
                    name="No category",
                    value=commands_desc,
                    inline=False
                )

            # setting information about author
            emb.set_footer(
                text=f"Version {version}"
            )

            # block called when one cog-name is given
            # trying to find matching cog and it's commands
        else:
            used_prefix = prefix
            found_command = None
            # iterating through cogs
            for cog in self.bot.cogs:
                # check commands first
                if cog.lower() != input.lower():
                    for command in self.bot.get_cog(cog).get_commands():
                        try:
                            for subcommand in command.subcommands:
                                if subcommand.qualified_name.lower() == input.lower():
                                    found_command = subcommand
                                    break
                        except:
                            if command.qualified_name.lower() == input.lower():
                                try:
                                    if command.hidden and int(ctx.author.id) not in owner_ids:
                                        continue
                                except:
                                    found_command = command
                        
                        if found_command:
                            break
                    if found_command:
                        break
                
                # if it's a cog
                else:
                    # making title - getting description from doc-string below class
                    emb = discord.Embed(
                        title=f'{cog} - Commands',
                        description=self.bot.cogs[cog].__doc__,
                        color=discord.Color.teal()
                    )

                    # getting commands from cog
                    for command in self.bot.get_cog(cog).get_commands():
                        try:
                            for subcommand in command.subcommands:
                                emb.add_field(
                                    name=f"{prefix}{subcommand.qualified_name}",
                                    value=subcommand.description or "No description provided",
                                    inline=False
                                )
                        except:
                            try:
                                if command.hidden and int(ctx.author.id) not in owner_ids:
                                    continue
                            except:
                                pass
                            emb.add_field(
                                name=f"{prefix}{command.name}",
                                value=command.description or "No description provided",
                                inline=False
                            )
                    # found cog - breaking loop
                    break
            # if command not found in a cog
            else:
                # check all walk slash commands
                for command in self.bot.walk_application_commands():
                    try:
                        if command.cog or (command.hidden and int(ctx.author.id) not in owner_ids):
                            continue
                    except:
                        if not command.cog and command.qualified_name.lower() == input.lower():
                            found_command = command
                            break
                # if it's not a walk slash command
                else:    
                    # check all walk message commands
                    for command in self.bot.walk_commands():
                        try:
                            if command.cog or (command.hidden and int(ctx.author.id) not in owner_ids):
                                continue
                        except:
                            pass
                        
                        if not command.cog and command.name.lower() == input.lower():
                            found_command = command
                            used_prefix = secondary_prefix
                            break
                    else:
                        emb = discord.Embed(
                            title="What's that?!",
                            description=f"I've never heard of `{input}` :scream:",
                            color=discord.Color.orange()
                        )
            
            if found_command:
                emb = discord.Embed(
                    title=f':sparkles: __{used_prefix}{found_command.qualified_name or found_command.name}__ :sparkles:',
                    color=discord.Color.teal()
                )
                emb.add_field(
                    name="How does it work?",
                    value=found_command.description or "No description provided",
                    inline=False
                )
                
        await send_embed(ctx, emb)



def setup(bot):
    bot.add_cog(Help(bot))
