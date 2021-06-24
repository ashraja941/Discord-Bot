import discord,os
from discord import message
from discord.channel import VoiceChannel
from dotenv import load_dotenv
from discord.ext import commands
import youtube_dl
import urllib.parse, urllib.request, re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='.',intents=intents)

@bot.command()
async def play(ctx, *,url):
    #check if given search is url or search
    if(url[:6] != "http://"):
        query_string = urllib.parse.urlencode({
        'search_query': url
    })

    html_content = urllib.request.urlopen(
        'http://www.youtube.com/results?' + query_string
    )

    #search_results = re.findall('href=\"\\/watch\\?v=(.{11})',html_content.read().decode())
    search_results = re.findall(r"watch\?v=(\S{11})", html_content.read().decode())
    url = 'http://www.youtube.com/watch?v=' + search_results[0]


    song_there = os.path.isfile("song.mp3")
    try:
        if song_there:
            os.remove("song.mp3")
    except PermissionError:
        await ctx.send("Song is currently playing")
        return

    #voiceChannel = discord.utils.get(ctx.guild.voice_channels, name = 'General' )
    voiceChannel = ctx.author.voice.channel 
    await voiceChannel.connect()
    voice =  discord.utils.get(bot.voice_clients,guild = ctx.guild)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    for file in os.listdir("./"):
        if file.endswith(".mp3"):
            os.rename(file,"song.mp3")
    voice.play(discord.FFmpegPCMAudio("song.mp3"))


@bot.command()
async def leave(ctx):
    voice = discord.utils.get(bot.voice_clients,guild = ctx.guild)
    if voice.is_connected():
        await voice.disconnect()
    else: 
        ctx.send("The bot is not connected to a voice channel")

@bot.command()
async def pause(ctx):
    voice = discord.utils.get(bot.voice_clients,guild = ctx.guild)
    if voice.is_playing():
        voice.pause()
    else:
        ctx.sent("No music is currently playing")

@bot.command()
async def resume(ctx):
    voice = discord.utils.get(bot.voice_clients,guild = ctx.guild)
    if voice.is_paused():
        voice.resume()
    else:
        ctx.sent("The audio is not paused")

@bot.command()
async def stop(ctx):
    voice = discord.utils.get(bot.voice_clients,guild = ctx.guild)
    voice.stop()

bot.run(TOKEN)