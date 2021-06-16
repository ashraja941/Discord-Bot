import discord,os
from discord import message
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents().all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    '''
    for guild in client.guilds:
        if guild.name == GUILD:
            break
    
    guild = discord.utils.find(lambda g: g.name == GUILD, client.guilds)
    '''
    guild = discord.utils.get(client.guilds, name=GUILD)

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )
    
    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')

@client.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Yo {member.name}, why are you here?'
    )

@client.event
async def on_message(message):
    if message.author == client.user:      #makes sure that there isn't recursion called
        return

    if message.content == '.help':
        await message.channel.send("use .help to get help, oh wait")
    elif message.content == '.raiseException':
        raise discord.DiscordException

@client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

client.run(TOKEN)