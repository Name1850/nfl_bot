import aiohttp
from bs4 import BeautifulSoup
from discord.ext import commands
import discord
from static_functions import *
from converters.positionconverter import PositionConverter
from interactions import *

def award_embed(ctx, year):
    col = ctx.bot.db["awards"]

    embed = discord.Embed(title=f"{year} NFL Awards", url="https://www.pro-football-reference.com/awards/",
                          color=ctx.bot.color)
    for a in ["mvp", "dpoy", "opoy", "oroy", "droy", "cpoy", "walter payton award"]:
        results = col.find({"award": a})[0]["results"]
        if str(year) in results:
            result = results[str(year)]
            embed.add_field(name=f"{a.title() if a == 'walter payton award' else a.upper()}",
                            value=f"{ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(result[2])]} **{result[0]} {result[1]}**")

    results = col.find({"award": "coy"})[0]["results"]
    if str(year) in results:
        result = results[str(year)]
        embed.add_field(name=f"COY",
                        value=f"{ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(result[-1])]} **{result[0]}**")

    return embed

async def hof_embed(ctx, year):
    col = ctx.bot.db["hof"]
    embed = discord.Embed(title=f"{year} Hall of Fame Inductees",
                          url=f"https://www.pro-football-reference.com/hof/",
                          description="", color=ctx.bot.color)

    if str(year) not in [x["year"] for x in list(col.find())]:
        await send_error(ctx, year, "year")
        return

    doc = col.find({"year": str(year)})[0]

    for stats in doc["inductees"]:
        embed.description += f"**{stats[3]}-{stats[4]} {stats[1]} {stats[0]}** - `{stats[-1]}` Pro Bowls\n"

    return embed

class Accolades(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the Pro Bowl roster from a certain year!", aliases=["pro-bowl", "pb"],
                      help="`position`- The position to get the roster for.\n"
                           "`year`- The year to get the roster for (optional). Defaults to the last year.",
                      usage="probowl <position> [year]")
    async def probowl(self, ctx, position: PositionConverter, year="2020"):
        await ctx.trigger_typing()
        url = f"https://www.pro-football-reference.com/years/{year}/probowl.htm"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                page_not_found = await check_404(ctx, r, year, "year")
                if page_not_found:
                    return

                stats_page = BeautifulSoup(await r.read(), features="lxml")

        table = stats_page.find("tbody")
        if table is None:
            return await send_error(ctx, year, "year")

        embed = discord.Embed(title=f"{year} Pro Bowl {position.upper()}s", url=url, description="", color=self.client.color)

        afc = []
        nfc = []
        allplayers = []
        for player in table.findAll("tr"):
            stats = [player.find("th").getText()] + [i.getText() for i in player.findAll("td")][:3]
            if self.client.positionconverter.simple_convert(stats[0].lower()) == position:
                if stats[1][-1] in ["%", "+"]:
                    stats[1] = stats[1][:-1]
                if stats[2].lower() == "afc":
                    afc.append(stats)
                elif stats[2].lower() == "nfc":
                    nfc.append(stats)
                else:
                    allplayers.append(stats)

        if len(nfc) == 0 or len(afc) == 0:
            embed.description += "\n".join(
                [f"{self.client.emoji_dict[i[-1].lower()]} **{i[0]} {i[1]}**" for i in allplayers])

        else:
            embed.add_field(name="<:nfc:908543554408820776> NFC", value="\n".join(
                [f"{self.client.emoji_dict[i[-1].lower()]} **{i[0]} {i[1]}**" for i in nfc]))
            embed.add_field(name="<:afc:908543522943152138> AFC", value="\n".join(
                [f"{self.client.emoji_dict[i[-1].lower()]} **{i[0]} {i[1]}**" for i in afc]))

        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the All-Pro roster from a certain year!", aliases=["all-pro", "ap"],
                      usage="allpro <position> [year]",
                      help="`position`- The position to get the roster for.\n"
                           "`year`- The year to get the roster for (optional). Defaults to the last year.")
    async def allpro(self, ctx, pos: PositionConverter, year="2020"):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/years/{year}/allpro.htm"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                page_not_found = await check_404(ctx, r, year, "year")
                if page_not_found:
                    return

                stats_page = BeautifulSoup(await r.read(), features="lxml")

        table = stats_page.find("tbody")
        if table is None:
            return await send_error(ctx, year, "year")

        embed = discord.Embed(title=f"{year} All Pro {pos.upper()}s", url=url, description="", color=self.client.color)

        for player in table.findAll("tr"):
            stats = [player.find("th").getText()] + [i.getText() for i in player.findAll("td")][:2]
            if self.client.positionconverter.simple_convert(stats[0].lower()) == pos:
                embed.description += f"{self.client.emoji_dict[stats[-1].lower()]} **{stats[0]} {stats[1]}**\n"

        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get All-Rookie roster from a certain year!", aliases=["all-rookie", "ar"],
                      usage="allrookie [year]",
                      help="`year`- The year to get the roster for (optional). Defaults to the last year.")
    async def allrookie(self, ctx, year=2020):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/awards/nfl-all-rookie-{year}.htm"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                page_not_found = await check_404(ctx, r, year, "year")
                if page_not_found:
                    return

                stats_page = BeautifulSoup(await r.read(), features="lxml")

        table = stats_page.find("tbody")

        embed = discord.Embed(title=f"{year} All Rookie Team", url=url, description="", color=self.client.color)

        for player in table.findAll("tr"):
            stats = [player.find("th").getText()] + [i.getText() for i in player.findAll("td")][:2]
            embed.description += f"{self.client.emoji_dict[stats[-1].lower()]} **{stats[0]} {stats[1]}**\n"

        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get NFL awards from a certain year!", usage="awards [year]",
                      help="`year`- The year to get the awards for (optional). Defaults to the last year.")
    async def awards(self, ctx, year="2020"):
        await ctx.trigger_typing()
        embed = award_embed(ctx, year)

        if len(embed.fields) == 0:
            return await send_error(ctx, year, "year")

        view = Toggle(ctx, int(year), 2020, "awards", min_value=1961)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the NFL Top 100 roster from a certain year!", aliases=["top-100", "top"],
                      usage="top100 [year]",
                      help="`year`- The year to get the roster for (optional). Defaults to the last year.")
    async def top100(self, ctx, year="2021"):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/awards/{year}-nfl-top-100.htm"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                page_not_found = await check_404(ctx, r, year, "year")
                if page_not_found:
                    return

                stats_page = BeautifulSoup(await r.read(), features="lxml")

        table = stats_page.find("tbody")
        all_stats = [[i.getText() for i in player.findAll("td")][:3] for player in table.findAll("tr")]

        embed = discord.Embed(title=f"{year} NFL Top 100", url=url, color=self.client.color)

        for i in range(8):
            if len(embed.fields) == 2 or len(embed.fields) == 5 or len(embed.fields) == 8:
                embed.add_field(name="\u200b", value="\u200b")
            embed.add_field(name="\u200b", value="\n".join(
                f"**{100 - (index + (12 * i))}. {self.client.emoji_dict[stats[2].lower()]} {stats[0]} {stats[1]}**" for
                index, stats in
                enumerate(all_stats[::-1][(i * 12):12 + (i * 12)])))

        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="\u200b",
                        value=f"**4. {self.client.emoji_dict[all_stats[3][2].lower()]} {all_stats[3][0]} {all_stats[3][1]}**\n"
                              f"**3. {self.client.emoji_dict[all_stats[2][2].lower()]} {all_stats[2][0]} {all_stats[2][1]}**")
        embed.add_field(name="\u200b",
                        value=f"**2. {self.client.emoji_dict[all_stats[1][2].lower()]} {all_stats[1][0]} {all_stats[1][1]}**\n"
                              f"**1. {self.client.emoji_dict[all_stats[0][2].lower()]} {all_stats[0][0]} {all_stats[0][1]}**")
        embed.add_field(name="\u200b", value="\u200b")
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get Hall of Fame inductees from a certain year!",
                      aliases=["hallofame", "hof"], usage="halloffame [year]",
                      help="`year`- The year to get inductees for (optional). Defaults to the last year.")
    async def halloffame(self, ctx, year=2021):
        await ctx.trigger_typing()

        embed = await hof_embed(ctx, year)
        if not embed:
            return

        view = Toggle(ctx, year, 2021, "hof", min_value=1963)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg


def setup(client):
    client.add_cog(Accolades(client))
