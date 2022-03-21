import inspect
import discord
from discord.ext import commands
from bs4 import Comment
from static_functions import *
from interactions import *
import math

def leaders_embed(ctx, rows, text, url, index, value):
    embed = discord.Embed(title=text, url=url, description="", color=ctx.bot.color)
    for i, row in enumerate(rows[(value*32):32+(value*32)]):
        embed.description += f"**{i+1+(value*32)}. {ctx.bot.emoji_dict[row[1].lower()]} {row[3].upper()} {row[0].strip('+').strip('*')}** - `{row[index]}`\n"

    return embed

def alltimeleaders_embed(ctx, text, table, url, value, filter):
    embed = discord.Embed(title=text, url=url, description="",
                          color=ctx.bot.color)

    for index, player in enumerate(table.findAll("tr")[(value*25):25+(value*25)]):
        stats = [i.getText() for i in player.findAll("td")]
        if stats[-2 if filter == "Single Game" else -1].lower() not in ctx.bot.emoji_dict:
            emoji = ctx.bot.emoji_dict['nfl']
        else:
            emoji = ctx.bot.emoji_dict[stats[-2 if filter == "Single Game" else -1].lower()]

        if filter == "Single Game":
            embed.description += f"**{index+1+(value*25)}. {emoji} {stats[0].strip('+')}** - `{stats[1]}`\n"
        else:
            embed.description += f"**{index+1+(value*25)}. {emoji} {stats[2]} {stats[0].strip('+')}** - `{stats[1]}`\n"

    return embed

def salaryleaders_embed(ctx, text, rows, url, value):
    embed = discord.Embed(title=text, description="",
                          color=ctx.bot.color,
                          url=url)
    for i, row in enumerate(rows[(value*25):25+(value*25)]):
        stats = [i.getText() for i in row.findAll("td")]
        embed.description += f"**{i+1+(value*25)}. {ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(row.find('div', {'class': 'rank-position'}).getText().strip())]} " \
                             f"{stats[2].strip()} {row.find('h3').getText()}** - `{stats[3].strip()}`\n"

    return embed

class Leaders(commands.Cog, name="Leader Commands"):
    def __init__(self, client):
        self.client = client

    async def basic_leaders(self, ctx, position, stat):
        if position.lower() not in ["passing", "rushing", "receiving", "defense"]: return await subcommand_error(ctx)
        if stat is None:
            raise commands.MissingRequiredArgument(param=inspect.Parameter(name="stat", kind=inspect.Parameter.KEYWORD_ONLY))

        sort = self.client.sortconverter.leader_convert(position.lower(), stat)
        if sort is None: return await send_error(ctx, stat, "stat")

        url = f"https://www.pro-football-reference.com/years/2021/{position.lower()}.htm"
        if position.lower() in ["passing", "rushing", "receiving"]:
            stats_page = await scrape_and_parse(url)
            table = stats_page.find("tbody")

            column_headers = stats_page.findAll('tr')[1 if position.lower() in ["rushing"] else 0]
            column_headers = [i.getText().lower() for i in column_headers.findAll('th')][1:]
            index = column_headers.index(sort)

            rows = []
            for row in table.findAll("tr"):
                if len(row.findAll("td")) == 0: continue
                if "non_qual" in row.findAll("td")[index].attrs["class"]: continue

                rows.append([i.getText() for i in row.findAll("td")])

        else:
            column_headers = ["player", "tm", "age", "pos", "g", "gs", "int", "yds", "td", "lng", "pd", "ff", "fmb",
                              "fr", "yds", "td", "sk", "comb", "solo", "ast", "tfl", "qbhits", "sfty"]
            rows = [[player["player"]] + player["stats"] for player in self.client.db["defense"].find()]
            index = column_headers.index(sort)

        for row in rows.copy():
            if len(row) == 0: rows.remove(row)
            elif not is_number(row[index]) or math.isnan(float(row[index])): rows.remove(row)
            elif float(row[index]) == 0: rows.remove(row)

        try: rows.sort(key=lambda x: int(x[index]), reverse=True)
        except ValueError: rows.sort(key=lambda x: float(x[index]), reverse=True)

        embed = leaders_embed(ctx, rows, f"{position.title()} Leaders Sorted By {column_headers[index].upper()}", url, index, 0)

        view = None
        if (len(rows)-1)//32 != 0:
            view = Toggle(ctx, 0, (len(rows)-1)//32, "leaders", rows=rows, text=f"{position.title()} Leaders Sorted By {column_headers[index].upper()}",
                          url=url, leader_index=index)

        msg = await reply(ctx, embed=embed, view=view)
        if view:
            view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.group(description="Get the current leaders in a certain category!", aliases=["leaderboard", "lb"],
                      usage="leaders <position> <stat>",
                      help="`position`- A position to check leaders for. Only `rushing`, `receiving`, `passing`, `defense` or `fantasy`.\n"
                           "`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def leaders(self, ctx):
        await ctx.trigger_typing()

        if ctx.invoked_subcommand is None:
            await subcommand_error(ctx)

    @leaders.command(description="Get the current passing leaders for a certain stat!", aliases=["p"],
                     usage="leaders passing <stat>",
                     help="`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def passing(self, ctx, stat=None):
        await self.basic_leaders(ctx, "passing", stat)

    @leaders.command(description="Get the current rushing leaders for a certain stat!", aliases=["rush"],
                     usage="leaders rushing <stat>",
                     help="`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def rushing(self, ctx, stat=None):
        await self.basic_leaders(ctx, "rushing", stat)

    @leaders.command(description="Get the current receiving leaders for a certain stat!", aliases=["rec"],
                     usage="leaders receiving <stat>",
                     help="`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def receiving(self, ctx, stat=None):
        await self.basic_leaders(ctx, "receiving", stat)

    @leaders.command(description="Get the current defensive leaders for a certain stat!", aliases=["d"],
                     usage="leaders defense <stat>",
                     help="`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def defense(self, ctx, stat=None):
        await self.basic_leaders(ctx, "defense", stat)

    @leaders.command(description="Get the current salary leaders for a certain stat!", aliases=["s"],
                     usage="leaders salary <stat>",
                     help="`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def salary(self, ctx, ranking_type="value"):
        if ranking_type.lower() not in ["bonus", "length", "value", "guaranteed", "gtd", "avg", "average"]:
            return await send_error(ctx, ranking_type, "ranking_type", "Please choose either `bonus`, `length`, `value`, `average` (`avg`), or `guaranteed` (`gtd`).")

        ranking_type = {"bonus": "signing-bonus", "length": "contract-length", "value": "contract-value", "guaranteed": "guaranteed",
                             "gtd": "guaranteed", "avg": "average", "average": "average"}[ranking_type.lower()]
        url = f"https://www.spotrac.com/nfl/rankings/{ranking_type}/"
        soup = await scrape_and_parse(url)

        table = soup.find("tbody")
        rows = table.findAll("tr")[:100]

        embed = salaryleaders_embed(ctx, f"Salary Leaders Sorted By {' '.join(ranking_type.split('-')).title()}", rows, url, 0)
        view = Toggle(ctx, 0, (len(rows)-1)//25, "salary leaders", rows=rows, text=f"Salary Leaders Sorted By {' '.join(ranking_type.split('-')).title()}", url=url)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    @leaders.command(description="Get the current fantasy leaders!", aliases=["f"],
                     usage="leaders fantasy")
    async def fantasy(self, ctx):
        url = f'https://www.pro-football-reference.com/years/2021/fantasy.htm'
        soup = await scrape_and_parse(url)

        stats_page = soup.find('tbody')

        allstats = []
        for row in stats_page.findAll("tr"):
            stats = [i.getText() for i in row.findAll("td")]
            if stats != [] and stats[-7] != "":
                allstats.append(stats)

        allstats = sorted(allstats, key=lambda x: int(x[-7]), reverse=True)[:25]
        embed = discord.Embed(title="Fantasy Leaders", url=url, description="", color=self.client.color)
        for i, player in enumerate(allstats):
            embed.description += f"**{i + 1}. {self.client.emoji_dict[player[1].lower()]} {player[0]}** - `{player[-7]}`\n"

        await reply(ctx, embed=embed)

    @leaders.command(description="Get the current team defense leaders for a certain stat!", aliases=["td"],
                     usage="leaders teamdefense <stat>",
                     help="`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def teamdefense(self, ctx, stat):
        stat, sort = self.client.sortconverter.teamdefense_convert(stat)
        if not stat: return await send_error(ctx, stat, "stat")

        print(stat, sort)
        url = f"https://www.pro-football-reference.com/years/2021/opp.htm"
        soup = await scrape_and_parse(url)

        embed = discord.Embed(title=f"Team Defense leaders sorted by {stat.upper()}", url=url,
                              color=self.client.color, description="")
        if sort == "advanced":
            table = soup.findAll("tbody")[1]
            column_headers = [i.getText().lower() for i in soup.findAll("thead")[1].findAll("th")]
            rows = [[row.find("th").getText()]+[i.getText() for i in row.findAll("td")] for row in table.findAll("tr")]

            try: rows.sort(key=lambda x: int(x[column_headers.index(stat.lower())]), reverse=True)
            except ValueError:
                try: rows.sort(key=lambda x: float(x[column_headers.index(stat.lower())]), reverse=True)
                except ValueError: rows.sort(key=lambda x: float(str(x[column_headers.index(stat.lower())])[:-1]), reverse=True)

            for i, row in enumerate(rows):
                embed.description += f"**{i + 1}. {self.client.emoji_dict[self.client.teamconverter.simple_convert(row[0])]} {row[0]}** - " \
                                     f"`{row[column_headers.index(stat.lower())]}`\n"
        elif sort == "normal":
            table = soup.find("tbody")
            column_headers = [i.getText().lower() for i in soup.find("thead").findAll("tr")[1].findAll("th")][1:]
            rows = [[i.getText() for i in row.findAll("td")] for row in table.findAll("tr")]
            try: rows.sort(key=lambda x: int(x[column_headers.index(stat.lower())]), reverse=True)
            except ValueError: rows.sort(key=lambda x: float(x[column_headers.index(stat.lower())]), reverse=True)

            for i, row in enumerate(rows):
                embed.description += f"**{i + 1}. {self.client.emoji_dict[self.client.teamconverter.simple_convert(row[0])]} {row[0]}** - " \
                                     f"`{row[column_headers.index(stat.lower())]}`\n"

        else:
            i = 0
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                if '<table' in comment:
                    if i == sort:
                        soup_table = BeautifulSoup(comment, "lxml")
                        table = soup_table.find('tbody')

                        column_headers = [i.getText().lower() for i in soup_table.find("thead").findAll("th")]
                        rows = [[player.find("th").getText()] + [j.getText() for j in player.findAll("td")] for player in table.findAll("tr")][:-3]

                        try: rows.sort(key=lambda x: int(x[column_headers.index(stat.lower())]), reverse=True)
                        except ValueError: rows.sort(key=lambda x: float(x[column_headers.index(stat.lower())]), reverse=True)

                        for j, row in enumerate(rows):
                            embed.description += f"**{j + 1}. {self.client.emoji_dict[self.client.teamconverter.simple_convert(row[1])]} {row[1]}** - " \
                                                 f"`{row[column_headers.index(stat.lower())]}`\n"
                        break

                    i += 1
                    if i == 2: break

        await reply(ctx, embed=embed)

    async def lookup_leaders(self, ctx, look_up_term, filter):
        term = self.client.sortconverter.all_time_leader_convert(look_up_term)
        if term is None:
            await send_error(ctx, look_up_term, "stat", "Type `help sort` for valid `stats`!")
            return
        url = f"https://www.pro-football-reference.com/leaders/{term}_{'_'.join(i.lower() for i in filter.split(' '))}.htm"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                soup = BeautifulSoup(await r.read(), "lxml")

        table = soup.findAll("tbody")[-1]
        if table is None:
            filters = ["career", "single game", "single season"]
            filters.remove(filter.lower())
            embed = discord.Embed(title="Command Error `alltimeleaders`", color=discord.Color.red(),
                                  description=f"No {filter} leaders for `{look_up_term}`. "
                                              f"Maybe try other filters, such as: {', '.join([f'`{x}`' for x in filters])}?")
            await reply(ctx, embed=embed)
            return

        embed = alltimeleaders_embed(ctx, f"{filter} {look_up_term.title()} Records", table, url, 0, filter)
        view = Toggle(ctx, 0, (len(table.findAll("tr"))-1)//25, "alltimeleaders", text=f"{filter} {look_up_term.title()} Records", table=table, url=url)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.group(description="Get the all time leaders for a certain category!", aliases=["all-time-leaders", "atl"],
                    usage="alltimeleaders <filter> <stat>",
                    help="`filter`- The filter. See `help alltimeleaders singleseason`, `help alltimeleaders singlegame`, or `help alltimeleaders career`.\n"
                         "`stat`- What stat to sort by. See `help sort` to see valid stats.")
    async def alltimeleaders(self, ctx):
        await ctx.trigger_typing()

        if ctx.invoked_subcommand is None:
            await subcommand_error(ctx)

    @alltimeleaders.command(description="Get the single season leaders!", aliases=["single-season", "season", "s"],
                            usage="alltimeleaders singleseason [stat]",
                            help="`stat` - What stat to sort by. See `help sort` to see valid stats to sort by.")
    async def singleseason(self, ctx, *, stat):
        await self.lookup_leaders(ctx, stat, "Single Season")

    @alltimeleaders.command(description="Get the single game leaders!", aliases=["single-game", "game", "g"],
                            usage="alltimeleaders singlegame [stat]",
                            help="`stat` - What stat to sort by. See `help sort` to see valid stats to sort by.")
    async def singlegame(self, ctx, *, stat):
        await self.lookup_leaders(ctx, stat, "Single Game")

    @alltimeleaders.command(description="Get the career leaders!", aliases=["c"],
                            usage="alltimeleaders career [stat]",
                            help="`stat` - What stat to sort by. See `help sort` to see valid stats to sort by.")
    async def career(self, ctx, *, stat):
        await self.lookup_leaders(ctx, stat, "Career")


def setup(client):
    client.add_cog(Leaders(client))
