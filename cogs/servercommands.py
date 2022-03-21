import aiohttp
from interactions import *
import discord
from discord.ext import commands
import pymongo
import time
from static_functions import *


class ServerCommands(commands.Cog, name="Server Commands"):
    def __init__(self, client):
        self.client = client

    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    @commands.command(description="Change the server's prefix!", aliases=["change-prefix", "prefix"],
                      usage="changeprefix <prefix>",
                      help="`prefix` - The prefix to change to. Use quotes around the new prefix if you are going to add spaces!")
    async def changeprefix(self, ctx, prefix):
        await ctx.trigger_typing()

        if prefix[0] == " ": prefix = prefix[1:]

        if len(prefix) > 10:
            embed = discord.Embed(description="The prefix must be 10 or less characters!", color=discord.Color.red())
            await reply(ctx, embed=embed)
            ctx.command.reset_cooldown(ctx)
            return

        col = self.client.db["servers"]

        docs = col.find({"server_id": ctx.guild.id})
        if len(list(docs)) > 0:
            new_points = {"$set": {"prefix": prefix}}
            col.update_one({"server_id": ctx.guild.id}, new_points)
        else:
            col.insert_one({"server_id": ctx.guild.id, "prefix": prefix})

        embed = discord.Embed(title=f"Prefix changed to `{prefix}`",
                              description="If you ever forget, ping the bot to see the server prefix!",
                              color=self.client.color)
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 600, commands.BucketType.user)
    @commands.command(description="Receive announcements from the support server!", aliases=["subscribe"],
                      usage="follow [channel]",
                      help="`channel` - The channel to send bot announcements to (optional). Defaults to current channel.")
    @commands.has_permissions(manage_guild=True)
    async def follow(self, ctx, channel: discord.TextChannel = None):
        await ctx.trigger_typing()

        if any(x.name == "NFL Bot Support #announcements" for x in await ctx.guild.webhooks()):
            embed = discord.Embed(title="Command Error `follow`",
                                  description="You have already followed NFL Bot!",
                                  color=discord.Color.red())
            embed.add_field(name="How to Change",
                            value="`Server Settings` > `Integrations` > `Channels Followed` > `NFL Bot Support`")
            await ctx.send(embed=embed)
            return

        if channel is None:
            channel = ctx.channel
        await self.client.get_channel(908520971302998016).follow(destination=channel)
        embed = discord.Embed(title="Followed NFL Bot",
                              description="Bot announcements/updates from the support server will now show up here!",
                              color=self.client.color)
        embed.add_field(name="How to Change",
                        value="`Server Settings` > `Integrations` > `Channels Followed` > `NFL Bot Support`")
        await ctx.send(embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the bot, web-scraping, and database latency!", aliases=["pong"],
                      usage="ping")
    async def ping(self, ctx):
        msg = await reply(ctx, content="Pinging..." if ctx.invoked_with == "ping" else "Ponging...")
        url = f"https://www.pro-football-reference.com"

        start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as _:
                pass
        end = time.perf_counter()
        scrape_dur = round((end - start) * 1000)

        start = time.perf_counter()
        db = pymongo.MongoClient("mongodb://localhost:27017/")["sports-bot"]
        _ = db["servers"].find()[0]
        end = time.perf_counter()
        db_dur = round((end - start) * 1000)

        embed = discord.Embed(title=f"Current {'Ping' if ctx.invoked_with == 'ping' else 'Pong'}",
                              description=f"**Bot latency:** `{round(self.client.latency * 1000)}ms`\n"
                                          f"**Web Scrape latency:** `{scrape_dur}ms`\n"
                                          f"**Database latency:** `{db_dur}ms`", color=self.client.color)
        await msg.edit(content=None, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get support server links, invite links, and a link to top.gg voting!", usage="about", aliases=["vote", "server", "invite"])
    async def support(self, ctx):
        buttons = [discord.ui.Button(label="Invite", url="https://discord.com/api/oauth2/authorize?client_id=911787246783434792&permissions=516037135425&scope=bot"),
                   discord.ui.Button(label="Support", url="https://discord.gg/edCYbf3QBE"),
                   discord.ui.Button(label="Vote", url="https://top.gg/bot/911787246783434792/vote")]
        embed = discord.Embed(title="Thank you for supporting NFL Bot!", color=self.client.color,
                              description="Click on one of the buttons below!")
        embed.set_thumbnail(url=self.client.avatar_url)
        await reply(ctx, embed=embed, view=ButtonView(buttons))

def setup(client):
    client.add_cog(ServerCommands(client))
