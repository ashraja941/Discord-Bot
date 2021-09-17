from asyncio.events import TimerHandle
import asyncio
import re
import datetime as dt
import typing as t
import random
from enum import Enum

import discord
from discord import embeds
from discord.colour import Color
from discord.raw_models import RawReactionClearEmojiEvent
import wavelink
from discord import player
from discord.ext import commands
from discord.ext.commands.core import command
from discord.utils import _URL_REGEX

import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
}

class AlreadyConnectedToChannel(commands.CommandError):
    pass

class NoVoiceChannel(commands.CommandError):
    pass

class QueueIsEmpty(commands.CommandError):
    pass

class NoTracksFound(commands.CommandError):
    pass

class PlayerIsAlreadyPaused(commands.CommandError):
    pass

class NoMoreTracks(commands.CommandError):
    pass

class NoPreviousTracks(commands.CommandError):
    pass

class InvalidRepeatMode(commands.CommandError):
    pass

class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2

class s2y:
    def __init__(self):
        with open("bot\config.json", encoding='utf-8-sig') as json_file:
            self.APIs = json.load(json_file)


    def getTracks(self,playlistURL):
        client_credentials_manager = SpotifyClientCredentials(self.APIs["spotify"]["client_id"], self.APIs["spotify"]["client_secret"])
        spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

        results = spotify.user_playlist_tracks(user="",playlist_id=playlistURL)
        

        trackList = []
        for i in results["items"]:
            if (i["track"]["artists"].__len__() == 1):
                trackList.append(i["track"]["name"] + " - " + i["track"]["artists"][0]["name"])
            else:
                nameString = ""
                for index, b in enumerate(i["track"]["artists"]):
                    nameString += (b["name"])
                    if (i["track"]["artists"].__len__() - 1 != index):
                        nameString += ", "
                trackList.append(i["track"]["name"] + " - " + nameString)

        return trackList



class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.NONE

    @property
    def first_track(self):
        if not self._queue:
            raise QueueIsEmpty
        return self._queue[0]

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty
        return self._queue[self.position + 1:]
    
    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty
        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue)

    def empty(self):
        self._queue.clear()
        self.position=0

    def add(self,*args):
        self._queue.extend(args)

    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty
        
        self.position += 1
         
        if self.position < 0:
            return None

        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.ALL:
                self.position = 0
            else:
                return None

        return self._queue[self.position]

    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty

        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self,mode):
        if mode =="none":
            self.repeat_mode = RepeatMode.NONE
        elif mode == "1":
            self.repeat_mode = RepeatMode.ONE
        elif mode == "all":
            self.repeat_mode = RepeatMode.ALL   
        

class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.queue = Queue()

    async def connect(self, ctx, channel=None):
        if self.is_connected:
            raise AlreadyConnectedToChannel
        if(channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        await super().connect(channel.id)
        return channel

    async def teardown(self):
        try: 
            await self.destroy()
        except KeyError:
            pass

    async def add_searched_tracks(self,ctx,tracks):
        if not tracks:
            raise NoTracksFound

        if (track := await self.choose_track(ctx,tracks)) is not None:
            self.queue.add(track)
            await ctx.send(f"Added {track.title} to the queue.")

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()
        

    async def add_tracks(self,ctx,tracks):
        if not tracks:
            raise NoTracksFound
        
        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)
        else:
            self.queue.add(tracks[0])
            msg = await ctx.send(f"Added {tracks[0].title} to the queue.")  #make into an embed

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()

    async def add_spotify_tracks(self,ctx,tracks):
        if not tracks:
            raise NoTracksFound
        self.queue.add(tracks[0])
        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()


    async def choose_track(self,ctx,tracks):
        def _check(r,u):
            return (
                r.emoji in OPTIONS.keys()
                and u == ctx.author
                and r.message.id == msg.id
            )
        embed = discord.Embed(
            title="Choose a song",
            description=(
                "\n".join(
                    f"**{i+1}.** {t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
                    for i, t in enumerate(tracks[:5])
                )
            ),
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )
        embed.set_author(name="Query Result")
        embed.set_footer(text=f"Invoked by {ctx.author.display_name}",icon_url=ctx.author.avatar_url)


        msg = await ctx.send(embed=embed)
        for emoji in list(OPTIONS.keys())[:min(len(tracks),len(OPTIONS))]:
            await msg.add_reaction(emoji)

        try:
            reaction,_=await self.bot.wait_for("reaction_add", timeout=60.0, check=_check)
        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.message.delete()
        else:
            await msg.delete()
            return tracks[OPTIONS[reaction.emoji]]
            

    async def start_playback(self):
        await self.play(self.queue.current_track)

    async def advance(self):
        try:
            if (track := self.queue.get_next_track()) is not None:
                await self.play(track)
        except QueueIsEmpty:
            pass

    async def repeat_track(self):
        await self.play(self.queue.current_track)


        

class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self,bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot = bot)
        self.bot.loop.create_task(self.start_nodes())
 
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            #can have a timer in here using asyncio.sleep
            if not [m for m in before.channel.members if not m.bot]:
                await self.get_player(member.guild).teardown()

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f" Wavelink node '{node.identifier}' ready.")


    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self,node,payload):
        if payload.player.queue.repeat_mode == RepeatMode.ONE:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()

    
    async def cog_check(self,ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Music commands are not available in DMs.")
            return False
        return True

    async def start_nodes(self):
        await self.bot.wait_until_ready()

         
        #free server
        nodes = {
            "MAIN": {
                "host": "lava.link",
                "port": 80,
                "rest_uri": "http://lava.link:80",
                "password": "anything as a password",
                "identifier": "MAIN",
                "region": "europe",
            }
        }

        #local server
        
        """      
        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "india",
            }
        }
        
        
        #my heroku server
        nodes = {
            "MAIN": {
                "host": "lfshlavalink.herokuapp.com",
                "port": 80,
                "rest_uri": "https://lfshlavalink.herokuapp.com/",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "europe"
            }
        }
        """ 
        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    @commands.command(name="restart")
    async def restart_command(self,ctx):
        await self.bot.wait_until_ready()
        #free server
        nodes = {
            "MAIN": {
                "host": "lava.link",
                "port": 80,
                "rest_uri": "http://lava.link:80",
                "password": "anything as a password",
                "identifier": "MAIN",
                "region": "europe",
            }
        }
        await self.wavelink.destroy_node(identifier="MAIN")
        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    @commands.command(name="connect", aliases=["join"])
    async def connect_command(self,ctx,*, channel:t.Optional[discord.VoiceChannel]):
        player = self.get_player(ctx)
        channel = await player.connect(ctx,channel)
        await ctx.send(f"Connected to {channel.name}.")

    @connect_command.error
    async def connect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyConnectedToChannel):
            await ctx.send("Already connected to a voice channel.")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was found.")

    @commands.command(name="disconnect", aliases = ["leave","dc"])
    async def disconnect_command(self,ctx):
        player = self.get_player(ctx)
        await player.teardown()
        await ctx.send("Disconnected.")

    @commands.command(name="search")
    async def search_command(self,ctx,*,query: str):
        player = self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)
        
        if query is None:
            pass 

        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
                query = f"ytsearch:{query}"

            await player.add_searched_tracks(ctx, await self.wavelink.get_tracks(query))

    @search_command.error
    async def search_command_error(self, ctx, exc):
        if isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")

    @commands.command(name="play", aliases=["p"])
    async def play_command(self,ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)

        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty
        
            await player.set_pause(False)

        elif query.find('spotify') != -1:
            if query.find('playlist') != -1:
                change = s2y()
                spotifyList = change.getTracks(query)
                for i in spotifyList:
                    search = f"ytsearch:{i}"
                    await player.add_spotify_tracks(ctx, await self.wavelink.get_tracks(search))
            else:
                await ctx.send("Only spotify playlists are currently supported. Try searching for the song using the .p or .search command")

        elif query.lower() in ["rick roll","Rickroll","rick astley","never gonna give you up"]:
            await ctx.send(f"Nice try {ctx.author.display_name}")

        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
                query = f"ytsearch:{query}"

            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))

    @play_command.error
    async def play_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("No songs to play as the queue is empty.")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")

    @commands.command(name="pause")
    async def pause_command(self,ctx):
        player = self.get_player(ctx)
        if player.is_paused:
            raise PlayerIsAlreadyPaused
        await player.set_pause(True)
        await ctx.send("Playback Paused.")

    @pause_command.error
    async def pause_command_error(self,ctx,exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            await ctx.send("Playback is already paused.")

    @commands.command(name="stop")
    async def stop_command(self,ctx):
        player = self.get_player(ctx)
        player.queue.empty()
        await player.stop()
        await ctx.send("Playback stopped.")

    @commands.command(name="next", aliases=["skip"])
    async def next_command(self, ctx):
        player = self.get_player(ctx)

        if not player.queue.upcoming and player.queue.repeat_mode != RepeatMode.ALL:
            raise NoMoreTracks
        if player.queue.repeat_mode == RepeatMode.ONE:
            player.queue.position += 1

        await player.stop()
        await ctx.send("Playing next track in queue.")

    @next_command.error
    async def next_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("This could not be executed as the queue is currently empty.")
        elif isinstance(exc, NoMoreTracks):
            await ctx.send("There are no more tracks in the queue.")

    @commands.command(name="previous")
    async def previous_command(self, ctx):
        player = self.get_player(ctx)

        if not player.queue.history:
            raise NoPreviousTracks

        player.queue.position -= 2
        await player.stop()
        await ctx.send("Playing previous track in queue.")

    @previous_command.error
    async def previous_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("This could not be executed as the queue is currently empty.")
        elif isinstance(exc, NoPreviousTracks):
            await ctx.send("There are no previous tracks in the queue.")

    @commands.command(name="shuffle")
    async def shuffle_command(self, ctx):
        player = self.get_player(ctx)
        player.queue.shuffle()
        await ctx.send("Queue shuffled.")

    @shuffle_command.error
    async def shuffle_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("The queue could not be shuffled as it is currently empty.")

    @commands.command(name="repeat")
    async def repeat_command(self,ctx, mode: str):
        if mode not in ("none","1","all"):
            raise InvalidRepeatMode
        
        player = self.get_player(ctx)
        player.queue.set_repeat_mode(mode)
        await ctx.send(f"The repeat mode had been set to {mode}.")


    @commands.command(name="queue",aliases=["q"])
    async def queue_command(self,ctx, show: t.Optional[int] = 10):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty
        
        embed = discord.Embed(
            title="Queue",
            color = ctx.author.color,
            timestamp=dt.datetime.utcnow()
        )
        embed.set_author(name="Query Result")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(
            name="Currently playing",
            value=getattr(player.queue.current_track,"title","No tracks"),
             inline=False
            )
        if upcoming := player.queue.upcoming:
            embed.add_field(
                name="Next up",
                value="\n".join(t.title for t in upcoming[:show]),
                inline=False
            )
        msg = await ctx.send(embed=embed)

    @queue_command.error
    async def queue_command_error(self,ctx,exc):
        if isinstance(exc,QueueIsEmpty):
            await ctx.send("The Queue is currently empty.")



def setup(bot):
    bot.add_cog(Music(bot))

