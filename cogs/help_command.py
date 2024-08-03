import discord
from discord.errors import Forbidden

"""
« HELP COG »
Original concept by Jared Newsom (AKA Jared M.F.)
https://gist.github.com/StudioMFTechnologies/ad41bfd32b2379ccffe90b0e34128b8b

Rewritten and optimized by github.com/nonchris
https://gist.github.com/nonchris/1c7060a14a9d94e7929aa2ef14c41bc2

Rewritten again and heavily modified for my own purposes by github.com/malpkakefirek | malpkakefirek#0
"""


async def send_embed(ctx, embed):
    """
    For help visit: https://youtu.be/dQw4w9WgXcQ
    """
    try:
        await ctx.respond(embed=embed)
    except Forbidden:
        try:
            await ctx.send("I can't send embeds. Check my pemissions")
        except Forbidden:
            response = "Hey, it looks like I can't send messages in channel %s in %s\nCould you notify the owner about this? :slight_smile: "
            await ctx.author.send(
                response % (ctx.channel.name, ctx.guild.name),
                embed=embed
            )


class Help(discord.Cog):
    """Help cog"""

    def __init__(self, bot):
        self.bot = bot
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(
        name="help",
        description="Helpful if you forget how to use commands",
    )
    async def help_slash(
        self,
        ctx,
        command_or_category: discord.commands.Option(
            str,
            description="A command or category, you want more info on",
            default=None
        )
    ):
        prefix = "/"
        secondary_prefix = "m!"
        version = "2.2"

        # setting owner name
        owner_name = "MCPedia Team"
        # avatar = self.bot.get_user(owner_id).avatar.ur

        # checks if cog parameter was given
        # if not: sending all modules and commands not associated with a cog
        if not command_or_category:
            # checks if owner is on this server - used to 'tag' owner
            owner = owner_name
            owner_ids = self.bot.owner_ids

            # starting to build embed
            emb = discord.Embed(
                title=":sparkles: __All commands__ :sparkles:",
                color=discord.Color.blue(),
                description="Use `/help <command/category>` to get additional info about a command/category",
            )

            # iterating through cogs, gathering descriptions
            for cog in self.bot.cogs:

                commands_desc = ''
                temp_cog = self.bot.get_cog(cog)
                # iterating through commands in cog
                for command in temp_cog.get_commands():
                    # if command in a cog
                    # listing command if cog name is None and command isn't hidden
                    if isinstance(command, discord.SlashCommandGroup):
                        for subcommand in command.subcommands:
                            mention = f"</{command.name} {subcommand.name}:{command.id}>"
                            description = subcommand.description or "No description"
                            commands_desc += f'{mention} - {description}\n'
                    elif isinstance(command, discord.SlashCommand):
                        description = command.description or "No description"
                        commands_desc += f'{command.mention} - {description}\n'
                    # text command
                    elif isinstance(command, discord.ext.commands.Command):
                        if not command.hidden or int(ctx.author.id) in owner_ids:
                            description = command.brief or "No description"
                            commands_desc += f'`{secondary_prefix}{command.name}` - {description}\n'
                    else:
                        commands_desc += "???"
                        print(command.name)

                # adding those commands to embed
                if commands_desc:
                    emb.add_field(
                        name=f"Category {cog}",
                        value=commands_desc,
                        inline=False,
                    )

            commands_desc = ''
            for command in self.bot.walk_application_commands():
                # if slash command not in a cog
                if not command.cog:
                    description = command.description or "No description"
                    commands_desc += f'{command.mention} - {description}\n'
            for command in self.bot.walk_commands():
                # if text command not in a cog and not hidden
                if (not command.hidden or int(ctx.author.id) in owner_ids) and not command.cog:
                    description = command.brief or "No description"
                    commands_desc += f'`{secondary_prefix}{command.name}` - {description}\n'

            if commands_desc:
                emb.add_field(
                    name="No category",
                    value=commands_desc,
                    inline=False,
                )

            # setting information about author
            emb.set_footer(
                text=f"Made by {owner} | Version {version}",
                # icon_url=avatar,
            )

        # block called when one cog-name or command is given
        # trying to find matching cog and it's commands
        else:
            used_prefix = prefix
            found_command = None
            # iterating through cogs
            for cog in self.bot.cogs:
                # check commands first
                if cog.lower() != command_or_category.lower():
                    for command in self.bot.get_cog(cog).get_commands():
                        try:
                            for subcommand in command.subcommands:
                                if subcommand.qualified_name.lower() == command_or_category.lower():
                                    found_command = subcommand
                                    break
                        except Exception:
                            try:
                                if command.hidden and int(ctx.author.id) not in owner_ids:
                                    continue
                                if command.name.lower() == command_or_category.lower():
                                    used_prefix = secondary_prefix
                                    found_command = command
                            except Exception:
                                if command.qualified_name.lower() == command_or_category.lower():
                                    found_command = command

                        if found_command:
                            break
                    if found_command:
                        break

                # if it's a cog
                else:
                    # making title - getting description from doc-string below class
                    emb = discord.Embed(
                        title=f"{cog} - Commands",
                        description=self.bot.cogs[cog].__doc__,
                        color=discord.Color.blue()
                    )

                    # getting commands from cog
                    for command in self.bot.get_cog(cog).get_commands():
                        try:
                            for subcommand in command.subcommands:
                                emb.add_field(
                                    name=f"</{subcommand.qualified_name}:{command.id}>",
                                    value=subcommand.description or "No description",
                                    inline=False,
                                )
                        except Exception:
                            try:
                                if command.hidden and int(ctx.author.id) not in owner_ids:
                                    continue
                            except Exception:
                                emb.add_field(
                                    name=f"{command.mention}",
                                    value=command.description or "No description",
                                    inline=False,
                                )
                            else:
                                emb.add_field(
                                    name=f"{secondary_prefix}{command.name}",
                                    value=command.brief or "No description",
                                    inline=False,
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
                    except Exception:
                        if not command.cog and command.qualified_name.lower() == command_or_category.lower():
                            found_command = command
                            break
                # if it's not a walk slash command
                else:
                    # check all walk message commands
                    for command in self.bot.walk_commands():
                        try:
                            if command.cog or (command.hidden and int(ctx.author.id) not in owner_ids):
                                continue
                        except Exception:
                            pass

                        if not command.cog and command.name.lower() == command_or_category.lower():
                            found_command = command
                            used_prefix = secondary_prefix
                            break
                    else:
                        emb = discord.Embed(
                            title="What's that?!",
                            description=f"I've never heard of `{command_or_category}` :scream:",
                            color=discord.Color.orange(),
                        )

            if found_command:
                command_name = found_command.qualified_name or found_command.name
                emb = discord.Embed(
                    title=f':sparkles: __{used_prefix}{command_name}__ :sparkles:',
                    color=discord.Color.blue(),
                )
                emb.add_field(
                    name="How does it work?",
                    value=found_command.description or "No description",
                    inline=False,
                )

        # sending reply embed using our own function defined above
        await send_embed(ctx, emb)


def setup(bot):
    bot.add_cog(Help(bot))
