import discord
from discord.ext import commands, tasks
from itertools import cycle
import pymongo


class EventHandler(commands.Cog, name="Event Handler"):
    def __init__(self, client):
        self.client = client
        self.statuses = cycle(["Madden | s!help", "Retro Bowl | s!help", "Football | s!help"])
        self.change_status.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready.")

    @tasks.loop(minutes=10)
    async def change_status(self):
        await self.client.change_presence(activity=discord.Game(next(self.statuses)))

    @change_status.before_loop
    async def before_change_status(self):
        await self.client.wait_until_ready()
        print("Background task started.")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            doc = self.client.db["servers"].find({"server_id": guild.id})[0]
            self.client.db["servers"].delete_one(doc)
        except IndexError:
            pass

        servers = self.client.db["live-scores"].find()[0]["servers"]
        for x in servers:
            if x[0] == guild.id:
                servers.remove([x[0], x[1]])
                new_points = {"$set": {"servers": servers}}
                self.client.db["live-scores"].update_one({}, new_points)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        c = None
        general_channel = discord.utils.get(guild.text_channels, name="general")
        if general_channel and general_channel.permissions_for(guild.me).send_messages:
            c = general_channel

        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    c = channel
                    break

        if c is None:
            return

        embed = discord.Embed(title="NFL Bot",
                              description="Do `s!help` for info, or `s!stats <player>` to get their current stats! Join our [**support server**](https://discord.gg/edCYbf3QBE), or "
                                          "[**invite the bot**](https://discord.com/api/oauth2/authorize?client_id=911787246783434792&permissions=516037135425&scope=bot) to your server!",
                              color=self.client.color)

        embed.set_thumbnail(url=self.client.avatar_url)
        await c.send(embed=embed)



def setup(client):
    client.add_cog(EventHandler(client))
