import os
import discord
from replit import db
from discord.ext import commands

from keep_alive import keep_alive

print(discord.__version__)

DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
INTENTS = discord.Intents.all()
OWNER_IDS = [336475402535174154, 311117384951791618]
#311117384951791618 - Lukasz
# Give default owners permission, if they don't have it already
#TODO: change database away from replit?
if 'permitted' not in db.keys():
    db['permitted'] = list()
owner_ids = db['permitted']
for owner_id in OWNER_IDS:
    if owner_id not in owner_ids:
        owner_ids.append(owner_id)
        print(f"ADDED {owner_id} AS AN OWNER")
db['permitted'] = owner_ids

bot = commands.Bot(
    command_prefix="m!",
    intents=INTENTS,
    help_command=None,
    owner_ids=owner_ids
)

# ========== LOADING COGS =========== #

if __name__ == '__main__':
    print("\nloading plugins...")
    """
    Loads the cogs from the `./cogs` folder.
    Note:
        The cogs are named in this format `{cog_dir}.{cog_filename_without_extension}`.
    """

    for cog in os.listdir('cogs'):
        if cog.endswith('.py') is True:
            print(f"loading cogs.{cog[:-3]}...")
            bot.load_extension(f'cogs.{cog[:-3]}')
    print("plugins loaded :D")

# ========== ON READY =========== #

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}\n")

    # Print all guilds the bot is in
    print("====== GUILDS ======")
    for guild in bot.guilds:
        print(f"| {guild.name}")

    # Set activity status to "Listening to /help"
    custom_activity = discord.Activity(type=2, name="/help")
    await bot.change_presence(activity=custom_activity)

    matches = db.prefix("")
    print(f"====== DATABASE ======\n{matches}")

# ========== ON MESSAGE =========== #


@bot.event
async def on_message(message):

    # Do nothing if it's a bot
    if message.author == bot.user or message.author.bot is True:
        return

    # Process commands
    await bot.process_commands(message)


# ========== TEXT COMMANDS =========== #


@bot.command(
    name="ping",
    brief="Test connection to bot",
    description="Test connection to bot",
    hidden=True,
)
@commands.is_owner()
async def ping(ctx):
    print("pinged")
    await ctx.send("Pong!")


keep_alive()
bot.run(DISCORD_TOKEN)
