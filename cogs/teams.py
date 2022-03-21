import datetime
from interactions import *
import discord
from bs4 import Comment
from discord.ext import commands
from static_functions import *
from converters.teamconverter import TeamConverter


def roster_embed(ctx, team, splice_dict, url, choice):
    embed = discord.Embed(
        title=f"{ctx.bot.emoji_dict[team.lower()]} {ctx.bot.teamconverter.simple_convert(team, 'reverse').title()} Roster",
        url=url, description="", color=ctx.bot.color)

    for k, v in {k: v for k, v in splice_dict[choice]}.items():
        value = ""
        for player in v:
            experience = "Rookie" if player[-3].lower() == "rook" else f"{player[-3]} years"
            value += f"`#{player[0]}` {player[3]} **{player[1]}** from **{player[8]}** ({experience})\n"

        embed.add_field(name=k.upper(), value=value, inline=False)

    embed = add_thumbnail(ctx, team, embed)
    return embed

def team_draft_embed(ctx, team, year, table, url):
    found_year = False

    embed = discord.Embed(
        title=f"{ctx.bot.emoji_dict[team.lower()]} {ctx.bot.teamconverter.simple_convert(team, 'reverse').title()} {year} Draft Picks",
        url=url, description="", color=ctx.bot.color)

    for row in table.findAll("tr"):
        stats = [i.getText() for i in row.findAll("td")]
        if stats == [] and found_year:
            break

        if row.find("th").getText() == str(year):
            embed.description += f"**{stats[3]} {stats[1]}** from **{stats[-1]}** (Round `{stats[0]}`)\n"
            found_year = True

    embed = add_thumbnail(ctx, team, embed)
    return embed

class TeamStats(commands.Cog, name="Team Stats"):
    def __init__(self, client):
        self.client = client

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get a team's schedule!", aliases=["calendar"], usage="schedule <team>",
                      help="`team`- An NFL team. See `help team` for valid teams.")
    async def schedule(self, ctx, *, team: TeamConverter):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/teams/{team}/2021.htm"

        stats_page = await scrape_and_parse(url)

        embed = discord.Embed(description="", url=url, color=self.client.color)
        table = stats_page.find('table', {"id": "games"}).find("tbody")
        last_record = ""
        playoffs = False
        for i, week in enumerate(table.findAll("tr")):
            game = [j.getText() for j in week.findAll("td")]
            if game[8].lower() == "bye week":
                embed.description += f"**{i + 1}. Bye Week**\n"
                continue
            if game[1].lower() == "playoffs":
                playoffs = "\u200b"
                continue

            if game[10] != "":
                score = f"`{game[9]}-{game[10]} {game[4]}`"
            else:
                score = ""
            if game[6] != "":
                last_record = "(" + game[6] + ")"

            game_info = f"**{'vs' if game[7] == '' else '@'} {self.client.emoji_dict[self.client.teamconverter.simple_convert(game[8])]} {game[8]}** {score}"
            if playoffs:
                playoffs += f"**{week.find('th').getText()}.** {game_info}\n"
            else:
                embed.description += f"**{i + 1}.** {game_info}\n"

            if game[3].lower() == "preview":
                months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
                month = months.index(game[1].split(" ")[0].lower())+1
                day = int(game[1].split(" ")[1])
                year = 2021 if month != 1 else 2022

                hours, minutes = game[2][:-5].split(":")
                if int(hours) != 12: hours = int(hours) + 12
                ts = int(datetime.datetime(year, month, day, int(hours), int(minutes)).timestamp())

                embed.description = embed.description.strip()
                if playoffs:
                    playoffs += f" <t:{ts}:R>\n"
                else:
                    embed.description += f" <t:{ts}:R>\n"

        embed.title = f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Schedule {last_record}"

        if playoffs:
            embed.add_field(name="Playoffs", value=playoffs)

        embed = add_thumbnail(ctx, team, embed)
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get a team's injury report!", aliases=["ir"],
                      usage="injuries <team>",
                      help="`team`- An NFL team. See `help team` for valid teams.")
    async def injuries(self, ctx, *, team: TeamConverter):
        await ctx.trigger_typing()

        url = f"https://www.espn.com/nfl/team/injuries/_/name/{self.client.teamconverter.simple_convert(team, 'espn').lower()}"
        soup = await scrape_and_parse(url)

        embed = discord.Embed(title=f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Injury Report",
                              url=url, color=self.client.color)

        section = soup.find("div", {"class": "Wrapper Card__Content"})
        for i, injury_date in enumerate(section.findAll("div", {"class": "ContentList"})):
            value = ""
            for injury in injury_date.findAll("a"):
                name = " ".join([i.getText() for i in injury.find("h3").findAll("span")][::-1])
                status = injury.find("div", {"class": "flex n9"}).findAll("span")[1].getText()

                reason = injury.find("div", {"class": "pt3 clr-gray-04 n8"})
                if reason is not None:
                    reason = reason.getText().split(",")[0].lower()
                    update_dict = {"covid": "(COVID-19)", "diagnosed": reason[reason.find("diagnosed"):], "(": reason[reason.find("("):reason.find(")")+1].title(), "": ""}
                    for k, v in update_dict.items():
                        if k in reason:
                            reason = v
                            break

                value += f"**{name}** {reason if reason is not None else ''} - {status}\n"

            date = section.findAll("div", {"class": f"pb3 bb bb--dotted brdr-clr-gray-07 n8 fw-medium mb2{'' if i == 0 else ' mt6'}"})[i-1].getText()
            embed.add_field(name=date, value=value, inline=False)

        embed = add_thumbnail(ctx, team, embed)
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get a team's roster!", aliases=["depth-chart", "depthchart"], usage="roster <team>",
                      help="`team`- An NFL team. See `help team` for valid teams.")
    async def roster(self, ctx, *, team: TeamConverter):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/teams/{team}/2021_roster.htm"
        soup = await scrape_and_parse(url)

        positions = {"qb": [], "rb": [], "wr": [], "te": [], "ol": [], "dl": [], "lb": [], "db": [], "st": []}

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            if '<table' in comment:
                soup_table = BeautifulSoup(comment, "lxml")
                table = soup_table.find('table')

                for player in table.findAll("tr")[1:-1]:
                    stats = [player.find("th").getText()] + [i.getText() for i in player.findAll("td")]
                    if self.client.positionconverter.simple_convert(stats[3]) in positions:
                        positions[self.client.positionconverter.simple_convert(stats[3])].append(stats)
                break

        splice_dict = {"offense": list(positions.items())[:5],
                       "defense": list(positions.items())[5:-1],
                       "special teams": list(positions.items())[-1:]}
        embed = roster_embed(ctx, team, splice_dict, url, "offense")
        view = RosterButton(ctx, team, splice_dict, url, "roster")
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get a team's general information!", aliases=["team-info", "info"],
                      usage="teaminfo <team>",
                      help="`team`- An NFL team. See `help team` for valid teams.")
    async def teaminfo(self, ctx, *, team: TeamConverter):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/teams/{team}/2021.htm"
        soup = await scrape_and_parse(url)

        info = soup.find("div", {"data-template": "Partials/Teams/Summary"})

        embed = discord.Embed(title=f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Info", url=url,
                              description="", color=self.client.color)
        for p in info.findAll("p"):
            text = p.getText().strip()
            splittext = text.split(":")
            if len(splittext) == 2:
                embed.description += f"**{splittext[0]}:** {splittext[1]}\n"
            elif len(splittext) == 1:
                embed.description += "**" + splittext[0] + ":**\n"
            else:
                embed.description += "**" + splittext[0] + f":** {splittext[1]} {splittext[2]}\n"

        embed = add_thumbnail(ctx, team, embed)
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get a team's defensive stats!", aliases=["team-defense", "td"],
                      usage="teamdefense <team>",
                      help="`team`- An NFL team. See `help team` for valid teams.")
    async def teamdefense(self, ctx, *, team: TeamConverter):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/years/2021/opp.htm"
        soup = await scrape_and_parse(url)

        embed = discord.Embed(title=f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Team Defense",
                              url=url,color=self.client.color)
        i = 0

        important_stats = {0: ["Cmp%", "Yds", "TD", "Int", "PD", "Y/G", "Rate", "Sk"],
                           1: ["Yds", "TD", "Y/A", "Y/G"],
                           4: ["Pts/G", "RecTD", "RshTD"],
                           "advanced": ["YAC", "Bltz%", "Prss%", "MTkl"]}

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            if '<table' in comment:
                if i in important_stats:
                    soup_table = BeautifulSoup(comment, "lxml")
                    table = soup_table.findAll('table')[0]

                    column_headers = [i.getText() for i in table.find("thead").findAll("th")]
                    for player in table.findAll("tr"):
                        stats = [player.find("th").getText()] +  [i.getText() for i in player.findAll("td")]
                        if stats == ["Rk"] or stats == [""]: continue
                        if stats[1].lower() == self.client.teamconverter.simple_convert(team, 'reverse').lower():
                            value = ""
                            for stat in important_stats[i]:
                                value += f"**{stat}:** `{stats[column_headers.index(stat)]}`\n"
                            value += f"\n**Rank:** `{stats[0]}`"

                            n = ["Passing", "Rushing", "", "", "Scoring"]
                            embed.add_field(name=n[i], value=value)
                            break

                i += 1
                if i == 5: break

        table = soup.findAll("table")[1]
        column_headers = [i.getText() for i in table.find("thead").findAll("th")]
        for row in table.findAll("tr"):
            stats = [row.find("th").getText()] + [i.getText() for i in row.findAll("td")]
            if stats == ["Tm"]: continue
            if stats[0].lower() == self.client.teamconverter.simple_convert(team, 'reverse').lower():
                value = ""
                for stat in important_stats["advanced"]:
                    value += f"**{stat}:** `{stats[column_headers.index(stat)]}` | "
                embed.description = value.strip("| ")
                break

        embed = add_thumbnail(ctx, team, embed)
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get a team's starters!",
                      usage="starters <team>",
                      help="`team`- An NFL team. See `help team` for valid teams.")
    async def starters(self, ctx, *, team: TeamConverter):
        await ctx.trigger_typing()

        url = f"https://www.espn.com/nfl/team/depth/_/name/{self.client.teamconverter.simple_convert(team, 'espn').lower()}"
        soup = await scrape_and_parse(url)

        players = []
        positions = []

        for i in range(3):
            tables = soup.findAll("table", {"style": "border-collapse:collapse;border-spacing:0"})
            for row in tables[1 + (i * 2)].findAll("tr"):
                if row.find("td") is not None: players.append(row.find("td").getText().strip())

            for row in tables[(i * 2)].findAll("tr"):
                if row.find("td") is not None: positions.append("**"+row.find("td").getText().strip()+":**")

            players.append('')
            positions.append("")

        embed = discord.Embed(title=f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Starters",
                              url=url, description="", color=self.client.color)
        starters = list(zip(positions, players))
        for position, starter in starters:
            embed.description += f"{position} {starter}\n"

        embed = add_thumbnail(ctx, team, embed)
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the latest transactions for a team!", aliases=["trades"],
                      usage="transactions <team>",
                      help="`team`- An NFL team. See `help team` for valid teams.")
    async def transactions(self, ctx, *, team: TeamConverter):
        await ctx.trigger_typing()

        url = f"https://www.espn.com/nfl/team/transactions/_/name/{self.client.teamconverter.simple_convert(team, 'espn').lower()}"
        soup = await scrape_and_parse(url)

        embed = discord.Embed(title=f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Latest Transactions",
                              url=url, description="", color=self.client.color)
        for i, td in enumerate(soup.findAll("tr", {"class": "Table__TR Table__TR--sm Table__even"})):
            if i == 10: break
            transaction = [i.getText() for i in td.findAll("td")]
            embed.add_field(name=transaction[0], value=transaction[1], inline=False)

        embed = add_thumbnail(ctx, team, embed)

        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get who a specific team drafted for a specific year!", aliases=["tdraft"],
                      usage="teamdraft <team> [year]",
                      help="`team`- An NFL team. See `help team` for valid teams.\n"
                           "`year`- The year to get the draft results from.")
    async def teamdraft(self, ctx, team: TeamConverter, year=2021):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/teams/{team}/draft.htm"
        soup = await scrape_and_parse(url)

        table = soup.find("tbody")
        embed = team_draft_embed(ctx, team, year, table, url)

        if embed.description == "":
            return await send_error(ctx, year, "year")

        view = Toggle(ctx, year, 2021, "team draft", min_value=int(table.findAll("tr")[-1].find("th").getText()), team=team, table=table, url=url)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

def setup(client):
    client.add_cog(TeamStats(client))
