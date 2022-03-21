import aiohttp
import discord
from discord.ext import commands, tasks
from bs4 import BeautifulSoup
from static_functions import *

class Owner(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.defenseleaderscrape.start()

    @commands.is_owner()
    @commands.command()
    async def awardscrape(self, ctx, url, *, name):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                stats_page = BeautifulSoup(await r.read(), features="lxml")

        table = stats_page.findAll("tbody")[0]

        allstats = []
        for row in table.findAll("tr"):
            if url == "https://www.pro-football-reference.com/awards/ap-coach-of-the-year.htm":
                player = [row.findAll("th")[0].getText()] + [i.getText() for i in row.findAll("td")][:-1]
            else:
                player = [row.findAll("th")[0].getText()] + [i.getText() for i in row.findAll("td")][1:]
            allstats.append(player)

        stat_dict = {}
        for stats in allstats:
            stat_dict[stats[0]] = stats[1:]

        col = self.client.db["awards"]
        col.insert_one({"award": name, "results": stat_dict})
        await ctx.reply("Successfully scraped.")

    @commands.is_owner()
    @commands.command()
    async def deletecol(self, ctx, name):
        col = self.client.db[name]
        for x in col.find(): col.delete_one(x)
        await ctx.reply("Successfully deleted.")

    @commands.is_owner()
    @commands.command()
    async def hofscrape(self, ctx):
        url = f"https://www.pro-football-reference.com/hof/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                stats_page = BeautifulSoup(await r.read(), features="lxml")

        table = stats_page.findAll("tbody")[0]

        stats_dict = {}
        for row in table.findAll("tr"):
            stats = [i.getText() for i in row.findAll("td")][:7]
            if stats[2] in stats_dict:
                stats_dict[stats[2]].append(stats)
            else:
                stats_dict[stats[2]] = [stats]

        col = self.client.db["hof"]
        for year, inductees in stats_dict.items():
            col.insert_one({"year": year, "inductees": inductees})

        await ctx.reply("Successfully scraped.")

    @tasks.loop(hours=24)
    async def defenseleaderscrape(self):
        col = self.client.db["defense"]
        for x in col.find(): col.delete_one(x)

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://www.pro-football-reference.com/years/2021/defense.htm") as r:
                stats_page = BeautifulSoup(await r.read(), features="lxml")

        table = stats_page.findAll("tbody")[0]
        stats_dict = {}
        for row in table.findAll("tr"):
            stats = [i.getText() for i in row.findAll("td")]
            if stats != []:
                stats_dict[stats[0]] = stats[1:]

        col = self.client.db["defense"]
        for player, stats in stats_dict.items():
            col.insert_one({"player": player, "stats": stats})

        channel = self.client.get_channel(908520601155694624)
        await channel.send("Successfully scraped.")

    @defenseleaderscrape.before_loop
    async def before_task(self):
        await self.client.wait_until_ready()
        print("Defensive scrape background task started.")


def setup(client):
    client.add_cog(Owner(client))