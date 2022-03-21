import inspect
import typing
from interactions import *
import aiohttp
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
from static_functions import *

async def stats_embed(ctx, soup, name, first_season, url, column_headers, value_index, parsed_table, career=False):
    values = [i.getText() for i in parsed_table.findAll("tr")[value_index-1].findAll("td")]

    format_dicts = {"passing": {"info": ["Age", "Tm", "Pos"], "games": ["GS", "QBrec", "4QC", "GWD"],
                                "general": ["Cmp%", "Yds", "TD", "Int", "Sk", "Rate"],
                                "averages": ["Y/A", "Y/C", "Y/G"]},
                    "rushing & receiving": {"info": ["Age", "Tm", "Pos"],
                                            "rushing": ["Rush", "Yds", "TD", "Y/A", "Y/G", "A/G"],
                                            "receiving": ["Rec", "Yds 2", "Y/R", "TD 2", "R/G", "Y/G 2"],
                                            "total": ["Touch", "Y/Tch", "YScm", "RRTD", "Fmb"]},
                    "receiving & rushing": {"info": ["Age", "Tm", "Pos"],
                                            "receiving": ["Rec", "Yds", "Y/R", "TD", "R/G", "Y/G"],
                                            "rushing": ["Rush", "Yds 2", "TD 2", "Y/A", "Y/G 2", "A/G"],
                                            "total": ["Touch", "Y/Tch", "YScm", "RRTD", "Fmb"]},
                    "defense & fumbles": {"info": ["Age", "Tm", "Pos"],
                                          "turnovers": ["Int", "PD", "FF", "FR"],
                                          "tackles": ["Sk", "Comb", "Solo", "Ast", "TFL", "QBHits", "Sfty"]},
                    "games": {"info": ["Age", "Tm", "Pos"]},
                    "kicking & punting": {"info": ["Age", "Tm", "Pos"],
                                          "kicking": ["FGA 6", "FGM 6", "Lng", "FG%"],
                                          "extra points": ["XPA", "XPM", "XP%"],
                                          "punting": ["Pnt", "Lng 2", "Blck", "Y/P"]}}
    position = soup.find("h2").getText()
    if position.lower() not in format_dicts:
        position = soup.findAll("h2")[1].getText()

    try:
        format_dict = format_dicts[position.lower()]
    except KeyError:
        await send_error(ctx, name, "name")
        return False


    embed = discord.Embed(title=f"{soup.find('h1').getText().strip()} ({int(first_season)+value_index-1 if not career else 'Career'})", url=url, color=ctx.bot.color)

    for field in format_dict:
        if field == "info":
            if career:
                continue

        value = ""
        for stat in format_dict[field]:
            try:
                if len(stat.split(" ")) == 2:
                    index = [i for i, n in enumerate(column_headers) if n == stat.split(" ")[0]][
                        int(stat.split(" ")[1]) - 1]
                    stat = stat.split(" ")[0]
                else:
                    index = column_headers.index(stat)

                if career:
                    index -= 1

                v = '0' if values[index] == '' else values[index].upper()
                value += f"**{stat}:** `{'N/A' if field == 'info' and v == '0' else v}`\n"
            except BaseException:
                continue
        embed.add_field(name=field.title(), value=value, inline=False)

    try: embed.set_thumbnail(url=soup.find('div', {"class": "media-item"}).find("img")["src"])
    except BaseException: pass

    return embed

def gamelog_embed(ctx, soup, format_dict, column_headers, url, face, game_index):
    values = [i.getText() for i in soup.find("tbody").findAll("tr")[game_index - 1].findAll("td")]

    embed = discord.Embed(
        title=f"Week {values[0]}- {soup.find('h1').getText().strip()} vs. {values[3]} ({values[4]})",
        description="", color=ctx.bot.color, url=url)
    for stat in format_dict:
        if stat not in column_headers: continue

        if "-" in stat:
            indexes = [column_headers.index(x) for x in stat.split("-")]
            v = "-".join(['0' if values[index] == '' else values[index].upper() for index in indexes])
        else:
            index = column_headers.index(stat)
            v = '0' if values[index] == '' else values[index].upper()
        embed.description += f"**{stat}:** `{v}`\n"

    embed.set_thumbnail(url=face)
    return embed

class Stats(commands.Cog, name="Player Stats"):
    def __init__(self, client):
        self.client = client

    async def scrape(self, ctx, name, fantasy=False):
        if len(name.split(" ")) < 2:
            await send_error(ctx, name, "name", "Please provide a first and last name!")
            return None, None

        first, last = name.split(" ")[:2]
        pre_url = f"https://www.pro-football-reference.com/search/search.fcgi?search={first.lower()}+{last.lower()}"
        async with aiohttp.ClientSession() as session:
            async with session.get(pre_url) as r:
                page_not_found = await check_404(ctx, r, name, "name")
                if page_not_found:
                    return None, None

                soup = BeautifulSoup(await r.read(), features="lxml")

        soup, url = await self.check_results(soup, ctx, name, fantasy=fantasy)
        if soup is None:
            return None, None

        return soup, pre_url if url is None else url

    async def check_results(self, soup, ctx, name, fantasy=False):
        if soup.find("h1").getText() == "Search Results":
            try:
                if soup.findAll("div", {"id": "content"})[0].findAll("div")[0].findAll("p")[
                    0].getText().strip() == "Found 0 hits that match your search.":
                    await send_error(ctx, name, "name")
                    return None, None
            except IndexError:
                pass
            new_dict = {}

            x = 0
            found_player = False
            while True:
                pre_url = f"https://www.pro-football-reference.com/search/search.fcgi?search={'+'.join(name.split())}&offset={x}"
                soup = await scrape_and_parse(pre_url)

                if soup.find("div", {"id": "content"}).find("div").find("p"): break

                div = soup.find("div", {"id": "players"})
                if not div:
                    await send_error(ctx, name, "name")
                    return None, None

                player = [i.getText().strip() for i in div.findAll("div", {"class": "search-item-name"})]
                team = [i.getText().strip() for i in div.findAll("div", {"class": "search-item-league"})]
                url = [i.getText().strip() for i in div.findAll("div", {"class": "search-item-url"})]

                if any(name.lower() in x.lower() for x in player):
                    found_player = True
                else:
                    if found_player:
                        break

                new_dict.update({i.split("\n")[0]: [j, k] for i, j, k in zip(player, team, url)})
                if name.lower() not in player[-1].lower() and found_player: break
                x += 100

            if len(new_dict) == 1:
                msg = await reply(ctx, content="Sent bad request for stats, sending new request. This will take a couple more seconds!")
                url = f"https://www.pro-football-reference.com{new_dict[list(new_dict)[0]][1]}{'/fantasy/2021' if fantasy else ''}"
                await ctx.trigger_typing()
                soup = await scrape_and_parse(url)

                await msg.delete()
                return soup, url

            elif len(new_dict) == 0:
                await send_error(ctx, name, "name")
                return None, None

            not_found = []
            for k in new_dict.keys():
                if " ".join(k.split("(")[0].split()[:-1]).lower() != name.lower():
                    not_found.append(k)

            if len(new_dict)-len(not_found) >= 1:
                for x in not_found: new_dict.pop(x)

            if len(new_dict) == 1:
                msg = await reply(ctx, content="Sent bad request for stats, sending new request. This will take a couple more seconds!")
                url = f"https://www.pro-football-reference.com{new_dict[list(new_dict)[0]][1]}{'/fantasy/2021' if fantasy else ''}"
                await ctx.trigger_typing()
                soup = await scrape_and_parse(url)
                await msg.delete()
                return soup, url

            labels = [k.split('\n')[0] for k in new_dict]
            descs = [new_dict[k][0] for k in new_dict]
            options = [discord.SelectOption(label=x[0], description=x[1]) for x in list(zip(labels, descs))]
            view = DropdownView(ctx, options, "Did you mean...", "stats")

            embed = discord.Embed(title="Multiple results found", color=self.client.color)
            view.message = await reply(ctx, embed=embed, view=view)

            timed_out = await view.wait()
            if timed_out: return None, None
            option = view.children[0].value

            url_suffix = new_dict[option][1]
            url = f"https://www.pro-football-reference.com{url_suffix}{'/fantasy/2021' if fantasy else ''}"
            await ctx.trigger_typing()
            soup = await scrape_and_parse(url)
            return soup, url
        else:
            first, last = name.split(" ")[:2]

            if soup.find("div", {"class": "search"}).find("form")["action"].startswith("/cfb"):
                url = f"https://www.pro-football-reference.com/players/{last[0].upper()}/{last[:4].capitalize()}{first[:2].capitalize()}00.htm{'/fantasy/2021' if fantasy else ''}"
                msg = await reply(ctx,
                                  content="Sent bad request for stats, sending new request. This will take a couple more seconds!")
                await ctx.trigger_typing()
                soup = await scrape_and_parse(url)
                await msg.delete()
                return soup, url

            if fantasy:
                url = f"https://www.pro-football-reference.com/players/{last[0].upper()}/{last[:4].capitalize()}{first[:2].capitalize()}00.htm/fantasy/2021"
                soup = await scrape_and_parse(url)
                return soup, url

            return soup, f"https://www.pro-football-reference.com/search/search.fcgi?search={first}+{last}"

    async def get_stats(self, ctx, name, type, year=None):
        soup, url = await self.scrape(ctx, name)
        if soup is None: return

        stats_page = soup.find('table')
        if stats_page is None:
            embed = discord.Embed(description=f"`{soup.find('h1').getText().strip()}` has no stats!",
                                  color=discord.Color.red())
            return await reply(ctx, embed=embed)

        if stats_page["id"] == "stats":
            stats_page = soup.findAll('table')[1]

        value_index = None
        if type == "current":
            parsed_table = stats_page.find("tbody")  # last season stats
            season = parsed_table.findAll("tr")[0].find("th").getText()
            value_index = len(parsed_table.findAll("tr"))
        elif type == "year":
            parsed_table = stats_page.find("tbody")
            if int(year) > 0:
                for index, row in enumerate(parsed_table.findAll("tr")):
                    stats = [row.find("th").getText()] + [i.getText() for i in row.findAll("td")]
                    if stats[0][:4] == year or index == int(year) - 1:
                        value_index = index+1
                if not value_index:
                    return await send_error(ctx, year, "year", f"This player did not play in the year `{year}`!")

            else:
                if len(parsed_table.findAll("tr")) < abs(int(year) - 1):
                    await send_error(ctx, year, "year", f"This player did not play `{abs(int(year + 1))}` years ago!")
                    return
                value_index = len(parsed_table.findAll("tr"))+int(year)

            season = parsed_table.findAll("tr")[0].find("th").getText()
        else:
            parsed_table = stats_page.find("tfoot")
            value_index = 1
            season = "Career"

        if len(stats_page.find("thead").findAll("tr")) > 1: head = stats_page.find("thead").findAll("tr")[1]
        else: head = stats_page.find("thead").find("tr")

        season = season.strip("+").strip("*")
        column_headers = [i.getText() for i in head.findAll("th")][1:]

        embed = await stats_embed(ctx, soup, name, season, url, column_headers, value_index, parsed_table, career=season=="Career")
        if not embed: return

        view = None
        if season != "Career":
            view = Toggle(ctx, value_index, len(parsed_table.findAll("tr")), "stats", soup=soup, name=name, season=season, url=url,
                          column_headers=column_headers, parsed_table=parsed_table)

        msg = await reply(ctx, embed=embed, view=view)

        if view: view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.group(description="Get the stats for a certain player!", aliases=["statistics"],
                    usage="stats [type] <name>",
                    help="`type` - The type of stat to be returned. See `help stats career`, `help stats playoffs`, `help stats current`, or `help stats fantasy` for valid types.\n"
                         "`name`- An NFL player.")
    async def stats(self, ctx):
        await ctx.trigger_typing()

        if ctx.invoked_subcommand is None:
            name = " ".join(ctx.message.content.split(" ")[len((ctx.prefix + "stats").split(" ")):])
            if name == "":
                raise commands.MissingRequiredArgument(
                    param=inspect.Parameter(name="name", kind=inspect.Parameter.KEYWORD_ONLY))

            cmd = self.client.get_command("stats current")
            await ctx.invoke(cmd, name=name)

    @stats.command(description="Get career stats!", usage="stats career <name>", aliases=["c"],
                   help="`name`- An NFL player.")
    async def career(self, ctx, *, name):
        await self.get_stats(ctx, name, "career")

    @stats.command(description="Get current stats!", usage="stats current <name>",
                   help="`name`- An NFL player.")
    async def current(self, ctx, *, name):
        await self.get_stats(ctx, name, "current")

    @stats.command(description="Get the stats from a specific year!", usage="stats year <year> <name>",
                   aliases=["years", "y"],
                   help="`year` - The year to get stats for.\n"
                        "`name`- An NFL player.")
    async def year(self, ctx, year, *, name):
        if not is_int(year):
            await send_error(ctx, year, "year")
            return
        await self.get_stats(ctx, name, "year", year)

    @stats.command(description="Get fantasy stats!", usage="stats fantasy <name>", aliases=["f"],
                   help="`name`- An NFL player.")
    async def fantasy(self, ctx, *, name):
        soup, url = await self.scrape(ctx, name, fantasy=True)
        if soup is None: return

        embed = discord.Embed(title=f"{soup.find('h1').getText().strip()}", url=url, description="",
                              color=self.client.color)

        stats_page = soup.find('tfoot').find("tr")
        total_stats = [i.getText() for i in stats_page.findAll("td")]

        stats_page = soup.find('tbody')
        for row in stats_page.findAll("tr"):
            stats = [i.getText() for i in row.findAll("td")]
            embed.description += f"**{stats[6]} {stats[1]} vs. {self.client.emoji_dict[stats[4].lower()]} {stats[4]} ({stats[5]})**\n" \
                                 f"**FantPt:** `{stats[-3]}` | **DKPt:** `{stats[-2]}` | **FDPt:** `{stats[-1]}`\n\n"

        if embed.description == "":
            n = name if soup.find('h1').getText().strip() == "" else soup.find('h1').getText().strip()
            embed = discord.Embed(description=f"`{n}` has no fantasy stats for this current season!",
                                  color=discord.Color.red())
            await reply(ctx, embed=embed)
            return

        embed.description += f"**FantPt:** `{total_stats[-3]}` | **DKPt:** `{total_stats[-2]}` | **FDPt:** `{total_stats[-1]}`"

        try:
            face = soup.find('div', {"class": "media-item"}).find("img")["src"]
            embed.set_thumbnail(url=face)
        except BaseException:
            pass

        await reply(ctx, embed=embed)

    @stats.command(description="Get playoff stats!", aliases=["playoff", "p", "pf"], usage="stats playoffs <name>",
                   help="`name`- An NFL player.")
    async def playoffs(self, ctx, *, name):
        await ctx.trigger_typing()

        soup, url = await self.scrape(ctx, name)
        if soup is None: return

        stats_page = soup.find('table')

        if stats_page["id"] == "stats":
            index = 2
        else:
            index = 1

        if not soup.findAll("table")[index]["id"].endswith("_playoffs"):
            embed = discord.Embed(description=f"`{soup.find('h1').getText().strip()}` has not played in the playoffs!",
                                  color=discord.Color.red())
            await reply(ctx, embed=embed)
            return

        if len(soup.findAll("thead")[index].findAll("tr")) > 1:
            head = soup.findAll("thead")[index].findAll("tr")[1]
        else:
            head = soup.findAll("thead")[index].find("tr")

        column_headers = [i.getText() for i in head.findAll("th")]

        table = soup.findAll("tbody")[index]

        format_dicts = {"passing": ["Cmp%", "Yds", "TD", "Int", "Rate"],
                        "rushing & receiving": ["Rush", "Yds", "TD"],
                        "receiving & rushing": ["Rec", "Yds", "TD"],
                        "defense & fumbles": ["Int", "Sk", "Comb"]}

        position = soup.find("h2").getText()
        if position.lower() not in format_dicts:
            position = soup.findAll("h2")[1].getText()
        stat_list = format_dicts[position.lower()]

        embed = discord.Embed(title=f"{soup.find('h1').getText().strip()}", description="",
                              url=url, color=self.client.color)
        for row in table.findAll("tr"):
            stats = [row.find("th").getText()] + [i.getText() for i in row.findAll("td")]
            value = ""
            for stat in stat_list:
                try:
                    value += f" **{stat}:** `{'0' if stats[column_headers.index(stat)] == '' else stats[column_headers.index(stat)]}` |"
                except:
                    pass

            year = stats[0]
            if year.endswith("+"): year = year[:-1]
            if year.endswith("*"): year = year[:-1]
            embed.add_field(name=f"{self.client.emoji_dict[stats[2].lower()]} {year}", value=value)

        try:
            face = soup.find('div', {"class": "media-item"}).find("img")["src"]
            embed.set_thumbnail(url=face)
        except BaseException:
            pass

        if len(embed.fields) % 3 != 0:
            for i in range(3 - (len(embed.fields) % 3)):
                embed.add_field(name="\u200b", value="\u200b")
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get basic information on a player!", aliases=["bio"], usage="playerinfo <name>",
                      help="`name`- An NFL player.")
    async def playerinfo(self, ctx, *, name):
        await ctx.trigger_typing()

        soup, url = await self.scrape(ctx, name)
        if soup is None: return

        embed = discord.Embed(title=f"{soup.find('h1').getText().strip()}", url=url,
                              color=self.client.color, description="")

        stats_page = soup.find('div', {"itemtype": "https://schema.org/Person"})
        for p in stats_page.findAll("p")[1:]:
            bio = p.getText().strip().split("\n")
            value = ""
            for x in bio:
                if ":" in x:
                    i = x.split(":")
                    value += f"**{i[0]}:** {' '.join(i[1:])}"
                else:
                    value += f" {x.strip()}"
            embed.description += value + "\n"

        try:
            face = soup.find('div', {"class": "media-item"}).find("img")["src"]
            embed.set_thumbnail(url=face)
        except BaseException:
            pass

        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the career awards for a player!", aliases=["pawards"],
                      usage="playerawards <name>",
                      help="`name`- An NFL player.")
    async def playerawards(self, ctx, *, name):
        await ctx.trigger_typing()

        soup, url = await self.scrape(ctx, name)
        if soup is None: return

        embed = discord.Embed(title=f"{soup.find('h1').getText().strip()}'s Awards", url=url,
                              color=self.client.color, description="")

        awards = soup.find("ul", {"id": "bling"})
        if awards is None:
            embed = discord.Embed(description=f"`{soup.find('h1').getText().strip()}` has no awards!",
                                  color=discord.Color.red())
            return await reply(ctx, embed=embed)

        for award in awards.findAll("a"):
            text = award.getText().split('x')[::-1]
            if len(text) > 1:
                embed.description += f"**{text[0]}s:** `{text[1]}`\n"
            else:
                embed.description += f"**{text[0]}**\n"

        try:
            face = soup.find('div', {"class": "media-item"}).find("img")["src"]
            embed.set_thumbnail(url=face)
        except BaseException:
            pass

        await reply(ctx, embed=embed)


    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get basic game stats for a certain player!", aliases=["game-log"],
                      usage="gamelog [week] <name>",
                      help="`week`- The week to get the game log for (optional). Defaults to 1.\n"
                           "`name`- An NFL player.")
    async def gamelog(self, ctx, week: typing.Optional[int] = None, *, name):
        await ctx.trigger_typing()

        soup, url = await self.scrape(ctx, name)
        if soup is None: return

        table = soup.find("table")
        if table["id"] != "stats":
            embed = discord.Embed(description=f"`{soup.find('h1').getText().strip()}` has not played this season!",
                                  color=discord.Color.red())
            return await reply(ctx, embed=embed)

        format_dicts = {"passing": ["Cmp-Att", "Yds", "Y/A", "TD", "Int", "Sk", "Rate"],
                        "rushing & receiving": ["Rush", "Yds", "Y/A", "TD", "Fmb"],
                        "receiving & rushing": ["Rec", "Tgt", "Yds", "Y/R", "TD"],
                        "defense & fumbles": ["Comb", "Solo", "Sk", "TFL", "Int", "PD"]}

        column_headers = [i.getText() for i in soup.find("thead").findAll("tr")[1].findAll("th")][1:]
        position = soup.findAll("h2")[1].getText()
        format_dict = format_dicts[position.lower()]

        try:
            face = soup.find('div', {"class": "media-item"}).find("img")["src"]
        except BaseException:
            face = ""

        game_index = 1
        if week is not None:
            for i, row in enumerate(soup.find("tbody").findAll("tr")):
                if row.find("td").getText() == str(week):
                    game_index = i+1
                    break

        length = 0
        for row in soup.find("tbody").findAll("tr"):
            if "Upcoming Games" in row.getText(): break
            length += 1

        embed = gamelog_embed(ctx, soup, format_dict, column_headers, url, face, game_index)
        view = Toggle(ctx, game_index, length, "gamelog", format_dict=format_dict,
                      column_headers=column_headers, face=face, url=url, soup=soup)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg


def setup(client):
    client.add_cog(Stats(client))

#leetcode and hackerrank for data structures stuff!