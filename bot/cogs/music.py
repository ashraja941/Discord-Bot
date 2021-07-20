import discord
import wavelink
from discord.ext import commands

class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)

class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self,bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot = bot)
        self.bot.loop.create_task(self.start_nodes())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

def setup(bot):
    bot.add_cog(Music(bot))