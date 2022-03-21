import asyncio
import aiohttp
from static_functions import *
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
from converters.dateconverter import DateConverter
from interactions import *


def undefeated_embed(ctx, year, table):
    last_year = ""
    embed = discord.Embed(title=f"Last Undefeated Team in {year}", description="",
                          url=f"https://www.pro-football-reference.com/friv/last-undefeated.htm", color=ctx.bot.color)
    for row in table.findAll("tr"):
        stats = [row.find("th").getText()] + [i.getText() for i in row.findAll("td")]
        if (stats[0] == "" and last_year == str(year)) or str(year) == stats[0]:
            if stats[-2] == "":
                finished = "Season hasn't finished"
            else:
                finished = f"Finished {stats[-2]} "
                if stats[-1] != "": finished += f"({stats[-1]})"
            embed.description += f"{ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(stats[2])]} " \
                                 f"**{stats[2]}**  ({stats[3]}) - {finished}\n"
        if stats[0] != "": last_year = stats[0]

    if len(embed.description.split("\n")) > 2: embed.title = f"Last Undefeated Teams in {year}"
    return embed

class MiscCommands(commands.Cog, name="Misc Commands"):
    def __init__(self, client):
        self.client = client

    @commands.cooldown(1, 5,  commands.BucketType.user)
    @commands.command(description="Get the last undefeated team from a specific year!",
                      usage="undefeated [year]",
                      help="`year`- The year to get the standings for (optional). Defaults to the current year.")
    async def undefeated(self, ctx, year="2021"):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/friv/last-undefeated.htm"
        stats_page = await scrape_and_parse(url)

        table = stats_page.find("tbody")

        embed = undefeated_embed(ctx, year, table)
        if embed.description == "":
            return await send_error(ctx, year, "year")

        view = Toggle(ctx, int(year), 2021, "undefeated", min_value=1920, table=table)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Find the top 25 NFL players born today!",
                      aliases=["birthday"], usage="birthdays")
    async def birthdays(self, ctx, *, date: DateConverter=((0,0), "Today")):
        await ctx.trigger_typing()

        suffix = "" if date is None else f"?month={date[0][0]}&day={date[0][1]}"
        url = f"https://www.pro-football-reference.com/friv/birthdays.cgi{suffix}"
        stats_page = await scrape_and_parse(url)

        table = stats_page.find("tbody")

        allstats = []
        for row in table.findAll("tr"):
            stats = [i.getText() for i in row.findAll("td")]
            allstats.append(stats)

        allstats.sort(key=lambda x: int(x[8]), reverse=True)

        embed = discord.Embed(title=f"Best 25 NFL Players Born {date[1]}", url=url, description="",
                              color=self.client.color)
        for stat in allstats[:25]:
            embed.description += f"**{stat[1]} {stat[0]}** `{stat[3]}-{stat[4]}`\n"

        embed.set_footer(text="Player greatness is based off of PFR's AV stat.")
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.command(description="Get a QB's passer rating based on certain factors!",
                      aliases=["rating", "passerating"], usage="passerrating")
    async def passerrating(self, ctx):
        await ctx.trigger_typing()

        fielddict = {"attempts": 0, "completions": 0, "yards": 0, "touchdowns": 0, "interceptions": 0}

        def check(m):
            try:
                return int(m.content) >= 0 and m.channel == ctx.channel and m.author == ctx.author
            except ValueError:
                return False

        last_message = None
        for factor in fielddict.keys():
            if last_message is not None: await last_message.delete()
            embed = discord.Embed(title=f"How many pass {' '.join(factor.split('_'))} does the quarterback have?",
                                  color=self.client.color, description="Will be 0 if you don't input a valid response.")
            msg = await reply(ctx, embed=embed)
            last_message = msg
            try:
                msg = await self.client.wait_for("message", timeout=10, check=check)
                fielddict[factor] = int(msg.content)

                if int(msg.content) == 0 and factor == "attempts":
                    embed = discord.Embed(description="You can't have 0 attempts!", color=discord.Color.red())
                    await reply(ctx, embed=embed)
                    return

            except asyncio.TimeoutError:
                if factor == "attempts":
                    embed = discord.Embed(description="You can't have 0 attempts!", color=discord.Color.red())
                    await reply(ctx, embed=embed)
                    return
                pass
        await last_message.delete()

        if (fielddict["attempts"] < fielddict["completions"]) or \
                (fielddict["touchdowns"]+fielddict["interceptions"] > fielddict["attempts"]) or\
                (fielddict["touchdowns"] > fielddict["completions"]) or \
                (fielddict["interceptions"] > fielddict["attempts"]-fielddict["completions"]):
            if fielddict["attempts"] < fielddict["completions"]:
                embed = discord.Embed(description="You can't have more completions than attempts!", color=discord.Color.red())
            elif fielddict["touchdowns"]+fielddict["interceptions"] > fielddict["attempts"]:
                embed = discord.Embed(description="You can't have more touchdowns and interceptions combined than attempts!", color=discord.Color.red())
            elif fielddict["interceptions"] > fielddict["attempts"]-fielddict["completions"]:
                embed = discord.Embed(description="You can't have more interceptions than incompletions!", color=discord.Color.red())
            else:
                embed = discord.Embed(description="You can't have more touchdowns than completions!", color=discord.Color.red())
            await reply(ctx, embed=embed)
            return

        factors = {"a": ((fielddict["completions"] / fielddict["attempts"]) - 0.3) * 5,
                   "b": ((fielddict["yards"] / fielddict["attempts"]) - 3) * 0.25,
                   "c": ((fielddict["touchdowns"] / fielddict["attempts"])) * 20,
                   "d": 2.375 - ((fielddict["interceptions"] / fielddict["attempts"]) * 25)}

        for x in factors:
            if factors[x] > 2.375: factors[x] = 2.375
            elif factors[x] < 0: factors[x] = 0

        rating = (sum(list(factors.values())) / 6) * 100
        embed = discord.Embed(title=f"Passer Rating: `{round(rating, 1)}`", color=self.client.color,
                              description=f"**{fielddict['completions']}-{fielddict['attempts']}**, **{fielddict['yards']}** yards")
        if fielddict["touchdowns"] > 0: embed.description += f", **{fielddict['touchdowns']}** TD"
        if fielddict["interceptions"] > 0: embed.description += f", **{fielddict['interceptions']}** INT"
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.command(description="Get the win probability based on certain factors!",
                      aliases=["win", "win-probability"],
                      usage="winprobability")
    async def winprobability(self, ctx):
        await ctx.trigger_typing()

        def split_check(m, split_by, first_content):
            if m.channel == ctx.channel and m.author == ctx.author:
                try:
                    if (is_number(first_content) and is_number(m.content.split(split_by)[1]) and len(m.content.split(split_by)) == 2) \
                            or m.content.lower() == "none":
                        return True
                except BaseException:
                    pass

            return False

        def down_and_distance(m):
            if len(m.content.split("&")) != 2: return False
            return split_check(m, "&", m.content.split("&")[0][0])

        def time(m):
            return split_check(m, ":", m.content.split(":")[0])

        def num_check(m):
            return m.channel == ctx.channel and m.author == ctx.author and (is_number(m.content) or m.content.lower() == "none")

        def field(m):
            return m.channel == ctx.channel and m.author == ctx.author and m.content.lower() in ["team", "opp", "none"]

        fielddict = {"down_and_distance": {"check": down_and_distance, "example": "2nd&10", "input": "1st&10"},
                      "time": {"check": time, "example": "2:00", "input": "0:01"},
                      "quarter": {"check": num_check, "example": "3", "input": ""},
                      "score_differential": {"check": num_check, "example": "10", "input": ""},
                      "field": {"check": field, "example": "Either team or opp", "input": ""},
                      "yards_from_goal": {"check": num_check, "example": "25", "input": ""}}

        last_message = None
        for factor in fielddict.keys():
            if last_message is not None: await last_message.delete()
            embed = discord.Embed(title=f"What is the {' '.join(factor.split('_'))}?",
                                  description=f"**Example:** `{fielddict[factor]['example']}`\n"
                                  f"**Default:** `{'No default' if fielddict[factor]['input'] == '' else fielddict[factor]['input']}` "
                                              f"(what the value will be if you don't input anything)",
                                  color=self.client.color)
            embed.set_footer(text="Type 'none' if you want to skip this element!")
            msg = await reply(ctx, embed=embed)
            last_message = msg
            try:
                msg = await self.client.wait_for("message", timeout=10, check=fielddict[factor]["check"])
                if msg.content.lower() != "none":
                    fielddict[factor]["input"] = msg.content
            except asyncio.TimeoutError:
                pass

        await last_message.delete()

        if len(fielddict["down_and_distance"]["input"].split("&")) == 2:
            down, distance = fielddict["down_and_distance"]["input"].split("&")
            down = down[0]
        else: down = distance = ""

        if len(fielddict["time"]["input"].split(":")) == 2:
            minutes, seconds = fielddict["time"]["input"].split(":")
        else: minutes = seconds = ""


        url = f"https://www.pro-football-reference.com/boxscores/win_prob.cgi?request=1&quarter={fielddict['quarter']['input']}" \
              f"&minutes={minutes}&seconds={seconds}&field={fielddict['field']['input']}&yds_from_goal={fielddict['yards_from_goal']['input']}" \
              f"&down={down}&yds_to_go={distance}&score_differential={fielddict['score_differential']['input']}"

        stats_page = await scrape_and_parse(url)

        table = stats_page.find('div', {'id': 'pi'})

        fields = [i.getText() for i in table.findAll("div")[-2].findAll("h3")]
        for i in range(len(fields)):
            try:
                fields[i] = f"**{fields[i].split(':')[0].strip()}:** {round(float(fields[i].split(':')[1].strip()), 1)}"
            except ValueError:
                fields[i] = f"**{fields[i].split(':')[0].strip()}:** {round(float(fields[i].split(':')[1].strip()[:-1]), 1)}"

        embed = discord.Embed(title=table.find("div", {"id": "form_description"}).getText().strip(), url=url,
                              description="\n".join(fields),
                              color=self.client.color)
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Ask statmuse.com a question through Discord!",
                      aliases=["statmuse"], usage="ask <question>",
                      help="`question`- Your question for statmuse.")
    async def ask(self, ctx, *, question):
        await ctx.trigger_typing()

        url = f"https://www.statmuse.com/nfl/ask/{'-'.join(question.split())}"
        soup = await scrape_and_parse(url)

        embed = discord.Embed(color=self.client.color, url=url)

        player = soup.find("div", {"class": "player-profile-header__content"})
        if player is not None:
            embed.title = player.find("div", {"class": "player-profile-header__name-container"}).getText().strip()
            embed.add_field(name="Bio",value=" ".join(player.find("div", {"class": "player-profile-header__details"}).getText().split()))
            for stat in player.findAll("div", {"class": "stat-item"}):
                embed.add_field(name=f"{stat.findAll('p')[0].getText()}", value=f"`{stat.findAll('p')[1].getText()}`")
            embed.set_footer(text=player.find("p", {"class": "scope"}).getText())

            in_bracket = False
            finished_string = ""
            for char in soup.find("player-profile")["summary-nlg-html"]:
                if char == "<": in_bracket = True
                elif not in_bracket: finished_string += char
                elif char == ">": in_bracket = False

            embed.description = finished_string

        else:
            header = soup.find("p")
            if header is not None:
                embed.title = header.getText()
                interpreted_as = soup.find("div", {"class": "visual-inferred-question"})
                if interpreted_as is not None: embed.set_footer(text=interpreted_as.getText())
            else:
                embed.title = "I didn't understand your question"

        embed.set_thumbnail(url=soup.find("img")["src"])

        await reply(ctx, embed=embed)


def setup(client):
    client.add_cog(MiscCommands(client))