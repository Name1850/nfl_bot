import unicodedata
import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands, tasks
import pymongo
from static_functions import *

class LiveScores(commands.Cog, name="Live Scores"):
    def __init__(self, client):
        self.client = client
        self.col = pymongo.MongoClient("mongodb://localhost:27017/")["sports-bot"]["live-scores"]
        self.scores = {}

    async def get_scores(self):
        url = f"https://www.espn.com/nfl/scoreboard"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                soup = BeautifulSoup(await r.read(), features="lxml")
        return soup

    async def send(self, embed):
        servers = self.col.find()[0]["servers"]
        for channel in [x[1] for x in servers]:
            try:
                c = self.client.get_channel(channel)
                await c.send(embed=embed)
            except Exception as e:
                pass

    def check_finished(self, team1, team2):
        win = team1.findAll("svg") + team2.findAll("svg")
        if len(win) > 0:
            if win[0]["class"][0] == "ScoreboardScoreCell__WinnerIcon":
                return True
        return False

    @tasks.loop(seconds=60)
    async def check_scores(self):
        soup = await self.get_scores()

        for gameday in soup.findAll("section", {"class": "Card gameModules"}):
            for game in gameday.findAll("section", {"class": "Scoreboard bg-clr-white flex flex-auto justify-between"}):
                team1, team2 = game.findAll("li")[:2]
                teams = {team1.findAll("div")[0].findAll("a")[0].findAll("div")[0].getText().lower(): team1.findAll("div")[-1].getText(),
                         team2.findAll("div")[0].findAll("a")[0].findAll("div")[0].getText().lower(): team2.findAll("div")[-1].getText(),
                         "finished": False}
                team1emoji = self.client.emoji_dict[self.client.teamconverter.simple_convert(list(teams)[0].lower())]
                team2emoji = self.client.emoji_dict[self.client.teamconverter.simple_convert(list(teams)[1].lower())]

                if self.check_finished(team1, team2):
                    if not self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"]["finished"]:
                        embed = discord.Embed(title=f"Final Score: {team1emoji} {list(teams)[0].title()} vs. {list(teams)[1].title()} {team2emoji}",
                                              color=self.client.color, description=f"||{team1emoji} `{list(teams.values())[0]}` - `{list(teams.values())[1]}` {team2emoji}||")
                        await self.send(embed)
                        self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"]["finished"] = True
                    continue
                if self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"]["finished"]: continue

                if team1.findAll("div")[-1].getText() != "":
                    if list(self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"].values()) != list(teams.values()):
                        if int(list(self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"].values())[0]) > int(list(teams.values())[0]) or \
                           int(list(self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"].values())[1]) > int(list(teams.values())[1]):
                            continue #check if cache had error

                        desc = game.find("p", {"class": "DriveChart2D__PlayText"}).getText()
                        embed = discord.Embed(title=f"Score Update: {team1emoji} {list(teams)[0].title()} vs. {list(teams)[1].title()} {team2emoji}",color=self.client.color,
                                              description=f"||{desc}||" if desc is not None else "")
                        embed.add_field(name="Old Score", value=f"{team1emoji} `{list(self.scores[f'{list(teams)[0]} vs {list(teams)[1]}'].values())[0]} "
                                                                f"- {list(self.scores[f'{list(teams)[0]} vs {list(teams)[1]}'].values())[1]}` {team2emoji}")
                        embed.add_field(name="New Score", value=f"||{team1emoji} `{list(teams.values())[0]} - {list(teams.values())[1]}` {team2emoji}||")
                        await self.send(embed)
                        self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"] = teams

    @commands.is_owner()
    @commands.command()
    async def servers(self, ctx):
        for x in self.col.find():
            await ctx.send(x)

    @commands.is_owner()
    @commands.command()
    async def start_loop(self, ctx):
        soup = await self.get_scores()

        for gameday in soup.findAll("section", {"class": "Card gameModules"}):
            for game in gameday.findAll("section", {"class": "Scoreboard bg-clr-white flex flex-auto justify-between"}):
                team1, team2 = game.findAll("li")[:2]
                teams = {team1.findAll("div")[0].findAll("a")[0].findAll("div")[0].getText().lower(): "0",
                         team2.findAll("div")[0].findAll("a")[0].findAll("div")[0].getText().lower(): "0",
                         "finished": self.check_finished(team1, team2)}
                self.scores[f"{list(teams)[0]} vs {list(teams)[1]}"] = teams

        self.check_scores.start()
        await reply(ctx, content="Live Scores check started!")

    @commands.is_owner()
    @commands.command()
    async def end_loop(self, ctx):
        self.scores = {}
        self.check_scores.cancel()
        await reply(ctx, content="Live scores loop ended.")

    @commands.is_owner()
    @commands.command()
    async def initlivescores(self, ctx):
        self.col.insert_one({"servers": []})
        await reply(ctx, content="Initialized live scores")

    @commands.is_owner()
    @commands.command()
    async def killlivescores(self, ctx):
        for x in self.col.find():
            self.col.delete_one(x)
        await reply(ctx, content="Killed live scores.")

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True, manage_channels=True, manage_messages=True)
    @commands.command(description="Enable or disable live score updates!", usage="getlivescores")
    async def getlivescores(self, ctx):
        servers = self.col.find()[0]["servers"]
        if ctx.guild.id not in [x[0] for x in servers]:
            servers.append([ctx.guild.id, ctx.channel.id])
            embed = discord.Embed(title="I will now send live game updates in this channel!", description=f"Type `{ctx.prefix}getlivescores` again to disable it.")
            await reply(ctx, embed=embed)
        else:
            for x in servers:
                if x[0] == ctx.guild.id:
                    servers.remove([x[0], x[1]])
                    if x[1] == ctx.channel.id:
                        embed = discord.Embed(title="You will no longer be notified for live game updates!",
                                              description=f"Type `{ctx.prefix}getlivescores` again to enable it.")
                    else:
                        servers.append([ctx.guild.id, ctx.channel.id])
                        embed = discord.Embed(title="I will now send live game updates in this channel!",
                                              description=f"Type `{ctx.prefix}getlivescores` again to enable it.\n"
                                                          f"I removed live game updates from <#{x[1]}>.")

                    await reply(ctx, embed=embed)
                    break # should fix https://discord.com/channels/912488796287815750/913594007018434561/925302952216920085

        new_points = {"$set": {"servers": servers}}
        self.col.update_one({}, new_points)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the current live scores!", usage="livescores")
    async def livescores(self, ctx):
        await ctx.trigger_typing()
        soup = await self.get_scores()

        embed = discord.Embed(title="Live Scores", description="", url="https://www.espn.com/nfl/scoreboard",
                              color=self.client.color)
        for gameday in soup.findAll("section", {"class": "Card gameModules"}):
            for game in gameday.findAll("section", {"class": "Scoreboard bg-clr-white flex flex-auto justify-between"}):
                team1, team2 = game.findAll("li")[:2]
                teams = {team1.findAll("div")[0].findAll("a")[0].findAll("div")[0].getText().title(): team1.findAll("div")[-1].getText(),
                         team2.findAll("div")[0].findAll("a")[0].findAll("div")[0].getText().title(): team2.findAll("div")[-1].getText(),
                         "finished": False}

                team1emoji = self.client.emoji_dict[self.client.teamconverter.simple_convert(list(teams)[0].lower())]
                team2emoji = self.client.emoji_dict[self.client.teamconverter.simple_convert(list(teams)[1].lower())]

                if team1.findAll("div")[-1].getText() != "":
                    embed.description += f"{team1emoji} **{list(teams)[0]}** `{list(teams.values())[0]} - " \
                                         f"{list(teams.values())[1]}` **{list(teams)[1]}** {team2emoji}"
                    if self.check_finished(team1, team2): embed.description += " (Final)"
                    id =  game.find("div", {"class": "Scoreboard__Callouts flex flex-column ph4 mv4 items-center"}).find("a")["href"].split("/")[-1]
                    embed.description += f" *ID:* `{id}`\n"


        embed.set_footer(text=f"Type `{ctx.prefix}game <id>` for more in-depth game stats!")
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get in-depth stats for a game!", usage="game <id>",
                      help="`id`- A game ID. Run `livescores` for valid IDs")
    async def game(self, ctx, id):
        await ctx.trigger_typing()
        url = f"https://www.espn.com/nfl/game?gameId={id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                soup = BeautifulSoup(await r.read(), "lxml")

        embed = discord.Embed(title="", url=url, color=self.client.color)
        header = soup.find("div", {"class": "competitors"})
        if header is None:
            return await send_error(ctx, id, "game_id", f"Type `{ctx.prefix}livescores` to find valid game IDs!")

        for x in ["home", "away"]:
            possession = False
            team = header.find("div", {"class": f"team {x}"})
            if team is None:
                team = header.find("div", {"class": f"team {x} possession"})
                possession = True

            team_string = team.find("span", {"class": "short-name"}).getText()
            embed.title += f"{self.client.emoji_dict[self.client.teamconverter.simple_convert(team_string)]} {team_string} "
            embed.title += team.find("div", {"class": "score-container"}).getText() + f"{' •' if possession else ''} vs. "

            value = ""
            for leaders in soup.findAll("div", {'class': "leader-column"}):
                leader = leaders.find("div", {"class": f"{x}-leader"}).find("div", {"class": "player-detail"})
                stats = []
                for span in leader:
                    normalized = unicodedata.normalize("NFKD", span.getText()).replace("&nbsp", " ")
                    if normalized == "--":
                        stats = ["N/A", "N/A"]
                        break
                    stats.append(normalized)
                value += f"**{leaders['data-stat-key'].replace('Yards', '').capitalize()}:** {stats[0]} - `{stats[1]}`\n"
            embed.add_field(name=x.title(), value=value, inline=False)

        embed.title = embed.title[:-4]
        drive_chart = soup.find("article", {"id": "gamepackage-current-drive"})
        if drive_chart is not None:
            details = drive_chart.find("header").find("div").find("div")

            details_list = []
            for span in details.findAll("span")[:-2]:
                if len(span.findAll("span")) == 0:
                    details_list.append(span.getText())
                else:
                    details_list.append(span.findAll("span")[0].getText())

            if details_list != []:
                for detail in list(zip(details_list[::2], details_list[1::2])):
                    embed.add_field(name=detail[0].strip(":"), value=detail[1])

            try:
                embed.description = f'({header.find("span", {"class": "game-time"}).getText().split("-")[1].strip()} - {drive_chart.find("div", {"class": "last-play-text lastPlayDetail"}).getText().strip("(")}'
            except:
                embed.description = f'{header.find("span", {"class": "game-time"}).getText()}'
        await reply(ctx, embed=embed)




def setup(client):
    client.add_cog(LiveScores(client))
