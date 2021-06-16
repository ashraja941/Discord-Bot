import discord,os
from discord import message
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='.',intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='test',help='checks if the bot works')
async def test(ctx):
    await ctx.send("Yay the test works! Wooo!!")

@bot.command(name='add', help='helps add 2 numbers.')
async def roll(ctx, a:int, b:int):
    if a+b == 69:
        await ctx.send("nice")
    else:
        await ctx.send(a+b)

@bot.command(name='createChannel',help='create a text channel (only for admins)')
@commands.has_role('admin')
async def create_channel(ctx, channel_name='New Channel'):
    guild = ctx.guild
    existing_channel = discord.utils.get(guild.channels, name=channel_name)
    if not existing_channel:
        print(f'Creating a new channel: {channel_name}')
        await guild.create_text_channel(channel_name)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')

@bot.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Yo {member.name}, why are you here?'
    )

@bot.event
async def on_message(message):
    if str(message.channel) == "donttext" and message.content != "":
            await message.channel.purge(limit=1)

bot.run(TOKEN)