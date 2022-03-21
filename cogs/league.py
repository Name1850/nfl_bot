import re
import typing
from interactions import *
import aiohttp
import datetime
import discord
from bs4 import BeautifulSoup, Comment
from discord.ext import commands
from static_functions import *
from converters.teamconverter import TeamConverter

def draft_embed(ctx, year, value, players):
    embed = discord.Embed(title=f"{year} Draft Results Round {value}",
                          url=f"https://www.pro-football-reference.com/years/{year}/draft.htm", description="",
                          color=ctx.bot.color)
    for player in players.findAll("tr"):
        if player.find("th").getText() == str(value):
            stats_list = [i.getText() for i in player.findAll("td")]
            embed.description += f"{ctx.bot.emoji_dict[stats_list[1].lower()]} **{stats_list[0]}. {stats_list[3]} {stats_list[2]}** from {stats_list[-2]}\n"
        if player.find("th").getText() == str(int(value) + 1):
            break

    return embed

def espn_embed(ctx, soup, conf, conf_dict):
    conference = soup.findAll("div", {"class": "ResponsiveTable ResponsiveTable--fixed-left standings-subgroups is-color-controlled"})[conf_dict["index"]]
    embed = discord.Embed(title=f"{ctx.bot.emoji_dict[conf.lower()]} {conf} Conference", color=conf_dict["color"], url=f"https://www.espn.com/nfl/standings")

    table = conference.find("tbody")
    table2 = conference.findAll("tbody")[1]
    current_div, teams = ("", "")
    for i, row in enumerate(table.findAll("tr")):
        name = row.find("span", {"class": "hide-mobile"})
        team = name.getText() if name is not None else row.getText()
        if name is None:
            if teams != "":
                if len(embed.fields) % 3 == 2: embed.add_field(name="\u200b", value="\u200b")
                embed.add_field(name=current_div, value=teams)
            current_div = team
            teams = ""
        else:
            record = [i.getText() for i in table2.findAll("tr")[i].findAll("td")][:3]
            record = record[:2] if record[2] == '0' else record
            teams += f"{ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(team)]} **{team} ({'-'.join(record)})**\n"

    embed.add_field(name=current_div, value=teams)
    if len(embed.fields) % 3 == 2: embed.add_field(name="\u200b", value="\u200b")
    return embed

def pfr_loop(ctx, soup, conf, conf_dict, year):
    info = soup.findAll("tbody")[conf_dict["index"]]
    standings = {}
    standing = ""
    for row in info.findAll("tr"):
        if len([i.getText() for i in row.findAll("td")]) == 1:
            standing = row.find("td").getText()
            continue
        team = [row.find("th").getText()] + [i.getText() for i in row.findAll("td")]
        if standing.strip() in standings:
            standings[standing.strip()].append(team)
        else:
            standings[standing.strip()] = [team]

    embed = discord.Embed(title=f"{ctx.bot.emoji_dict[conf.lower()]} {year} {conf} Conference", url=f"https://www.pro-football-reference.com/years/{year}/",
                          color=conf_dict['color'])

    for division in standings:
        value = ""
        for team in standings[division]:
            if len(embed.fields) % 3 == 2:
                embed.add_field(name="\u200b", value="\u200b")
            if "*" in team[0] or "+" in team[0]:
                team[0] = team[0][:-1]

            value += f"{ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(team[0])]} **{team[0]} ({team[1]}-{team[2]}{'-' + team[3] if team[3] != '0' else ''})**\n"
        embed.add_field(name=division, value=value)

    embed.add_field(name="\u200b", value="\u200b")
    return embed

def playoff_embed(ctx, soup, conf_dict, conf):
    allstats = []
    index = 0
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if '<table' in comment:
            if index != conf_dict["index"]:
                index += 1
                continue
            soup_table = BeautifulSoup(comment, "lxml")
            table = soup_table.find('table')

            for player in table.findAll("tr")[1:]:
                allstats.append([player.find("th").getText()] + [i.getText() for i in player.findAll("td")])
            break

    embed = discord.Embed(title=f"{ctx.bot.emoji_dict[conf.lower()]} {conf.upper()} Playoff Picture", url=f"https://www.pro-football-reference.com/years/2021/",
                          description="", color=conf_dict["color"])
    for i, team in enumerate(allstats):
        if allstats.index(team) == 7:
            embed.description += "\n"
        emoji = ctx.bot.emoji_dict[
            ctx.bot.teamconverter.simple_convert(' '.join(team[0].split(' ')[:-1]))] if allstats.index(team) < 7 else \
            ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(team[0])]
        name = " ".join(team[0].split(" ")[:-1]) if allstats.index(team) < 7 else team[0]
        embed.description += f"**{str(i + 1) + '. ' if allstats.index(team) < 7 else ''}{emoji} {name} ({team[1]}-{team[2]}{'-' + team[3] if team[3] != '0' else ''})** {team[-1]}\n"
    return embed

async def dropdown_embed(ctx, index, options):
    embed = discord.Embed(title=f"{options[index][3]}", url=options[index][2], description=options[index][1], color=ctx.bot.color)

    emoji_id = str(options[index][0].emoji).split(":")[-1].strip(">")
    embed.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/{emoji_id}.png?v=1")

    return embed

def superbowl_embed(ctx, year, table):
    for row in table.findAll("tr"):
        stats = [row.find("th").getText()] + [i.getText() for i in row.findAll("td")]
        if stats == ["Date"]: continue
        superbowlnumber = stats[1][stats[1].find("(") + 1:stats[1].find(")")].lower(), stats[1].split()[0].lower()
        if stats[0].split(" ")[-1] == str(year) or str(year).lower() in superbowlnumber:
            embed = discord.Embed(title=f"Super Bowl {stats[1]}", url=f"https://www.pro-football-reference.com/super-bowl/", color=ctx.bot.color,
                                  description=f"{ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(stats[2])]} **{stats[2]}** `{stats[3]}` - "
                                              f"`{stats[5]}` **{stats[4]}** {ctx.bot.emoji_dict[ctx.bot.teamconverter.simple_convert(stats[4])]}")
            embed.add_field(name="Date", value=stats[0])
            embed.add_field(name="MVP", value=stats[6].strip("+"))
            embed.add_field(name="Stadium", value=f"{stats[7]} in {stats[8]}, {stats[9]}", inline=False)
            return embed, int(stats[0].split(" ")[-1])

    return None, None

class League(commands.Cog, name="League Stats"):
    def __init__(self, client):
        self.client = client

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get results from the last draft!",
                      usage="draft [round] [year]",
                      help="`round`- The draft round (optional). Defaults to 1.\n"
                           "`year`- The draft year (optional). Defaults to the last year.")
    async def draft(self, ctx, round="1", year="2021"):
        await ctx.trigger_typing()

        if not round.isdigit(): return await send_error(ctx, round, "round")
        if int(round) <= 0 or int(round) > 7: return await send_error(ctx, round, "round")

        url = f"https://www.pro-football-reference.com/years/{year}/draft.htm"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                page_not_found = await check_404(ctx, r, year, "year")
                if page_not_found:
                    return

                stats_page = BeautifulSoup(await r.read(), features="lxml")

        if stats_page.find("h2").getText() == "Draft Order":
            table = stats_page.find('tbody')
            embed = discord.Embed(title=f"{year} Draft Order", url=url, color=self.client.color, description="")
            for row in table.findAll("tr"):
                stats = [i.getText() for i in row.findAll("td")]

                extra = f"({stats[2]})"
                embed.description += f"**{stats[0]}. {self.client.emoji_dict[self.client.teamconverter.simple_convert(stats[1])]} " \
                                     f"{self.client.teamconverter.simple_convert(stats[1], 'full').title()}** {extra if extra != '()' else ''}\n"

            return await reply(ctx, embed=embed)


        table = stats_page.find('table')
        players = table.find('tbody')

        view = Toggle(ctx, int(round), 7, "draft", year=year, players=players)
        embed = draft_embed(ctx, year, view.value, players)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    async def espn_scrape(self, ctx, conf_dicts, soup, conf):
        embed = espn_embed(ctx, soup, conf, conf_dicts[conf])
        view = ConferenceButton(ctx, conf_dicts, soup, conf)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    async def pfr_scrape(self, ctx, conf_dicts, soup, year, conf):
        if len(soup.findAll("tbody")) == 1:
            return await send_error(ctx, year, "year")

        embed = pfr_loop(ctx, soup, conf, conf_dicts[conf], year)
        view = ConferenceButton(ctx, conf_dicts, soup, conf, year)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the standings for a conference from a specific year!", aliases=["standing", "rankings"],
                      usage="standings [year] [conference]",
                      help="`year`- The year to get the standings for (optional). Defaults to the current year.\n"
                           "`conference`- The conference, NFC or AFC.")
    async def standings(self, ctx, year: typing.Optional[int] = 2021, conf="NFC"):
        await ctx.trigger_typing()

        conf_dicts = {"AFC": {"color": 0xD50A0A, "index": 0}, "NFC": {"color": 0x013369, "index": 1}}
        if conf.upper() not in conf_dicts:
            await send_error(ctx, conf, "conference", "Must be either `NFC` or `AFC`.")
            return

        url = f"https://www.pro-football-reference.com/years/{year}/" if year != 2021 else f"https://www.espn.com/nfl/standings"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                page_not_found = await check_404(ctx, r, year, "year")
                if page_not_found:
                    return
                soup = BeautifulSoup(await r.read(), "lxml")

        if year == 2021: await self.espn_scrape(ctx, conf_dicts, soup, conf.upper())
        else: await self.pfr_scrape(ctx, conf_dicts, soup, year, conf.upper())

    async def playoff_pictures(self, ctx, year, soup=None):
        url = f"https://www.pro-football-reference.com/years/{year}/"
        if not soup:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    page_not_found = await check_404(ctx, r, year, "year")
                    if page_not_found: return
                    soup = BeautifulSoup(await r.read(), "lxml")

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            if '<table' in comment:
                soup_table = BeautifulSoup(comment, "lxml")
                table = soup_table.find('table')
                rounds = {}

                for row in table.findAll("tr")[1:]:
                    game = [row.find("th").getText()] + [i.getText() for i in row.findAll("td")]
                    game[0] = " ".join(re.findall('[A-Z][^A-Z]*', game[0]))
                    if game[0] in rounds:
                        rounds[game[0]].append(game[1:])
                    else:
                        rounds[game[0]] = [game[1:]]

                embed = discord.Embed(title=f"{year} Playoff Results", url=url, color=self.client.color)
                for k, v in rounds.items():
                    value = ""
                    for game in v:
                        value += f"{self.client.emoji_dict[self.client.teamconverter.simple_convert(game[2])]} **{game[2]}** `{game[-2]} - " \
                                 f"{game[-1]}` **{game[4]}** {self.client.emoji_dict[self.client.teamconverter.simple_convert(game[4])]}\n"
                    embed.add_field(name=k, value=value, inline=False)

                return await reply(ctx, embed=embed)

        await send_error(ctx, year, "year")

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the playoff picture for a certain year for a certain conference!", aliases=["playoff"],
                      usage="playoffs [year] [conference]",
                      help="`year`- The year to get the playoff picture for (optional). Defaults to the current year.\n"
                           "`conference`- The conference, NFC or AFC (optional).")
    async def playoffs(self, ctx, year: typing.Optional[int] = 2021, conf="NFC"):
        await ctx.trigger_typing()

        if year < 1967:
            return await send_error(ctx, year, "year")

        if year != 2021:
            return await self.playoff_pictures(ctx, year)

        conf_dicts = {"AFC": {"color": 0xD50A0A, "index": 0}, "NFC": {"color": 0x013369, "index": 1}}
        if conf.upper() not in conf_dicts:
            await send_error(ctx, conf, "conference", "Must be either `NFC` or `AFC`.")
            return

        url = f"https://www.pro-football-reference.com/years/{year}/"
        soup = await scrape_and_parse(url)

        if any("Playoff Results" in header.text for header in soup.findAll("h2")):
            return await self.playoff_pictures(ctx, year, soup)


        embed = playoff_embed(ctx, soup, conf_dicts[conf.upper()], conf)
        view = ConferenceButton(ctx, conf_dicts, soup, conf, playoff=True)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg


    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.group(description="Get the betting lines for the upcoming games!",
                      aliases=["betting-lines", "betting", "bets", "lines", "odds"], usage="bettinglines")
    async def bettinglines(self, ctx):
        return await ctx.send("No betting lines available.") #take away once season starts

        await ctx.trigger_typing()

        if ctx.invoked_subcommand is None:
            url = f'https://www.espn.com/nfl/lines'
            soup = await scrape_and_parse(url)

            embed = discord.Embed(title=soup.find("h1").getText(), url=url, description="", color=self.client.color)
            for i, table in enumerate(soup.findAll('tbody')):
                if len(embed.fields) % 3 == 2:
                    embed.add_field(name="\u200b", value="\u200b")
                teams = []
                for row in table.findAll("tr"):
                    teams.append([i.getText() for i in row.findAll("td")])

                if str(teams[0][2]).startswith("-"): spread, overunder = (teams[0][2], teams[1][2])
                else: overunder, spread = (teams[0][2], teams[1][2])
                embed.add_field(
                    name=f"{self.client.emoji_dict[self.client.teamconverter.simple_convert(teams[0][0])]} {teams[0][0]} ({teams[0][-2]}) vs. "
                         f"{teams[1][0]} ({teams[1][-2]}) {self.client.emoji_dict[self.client.teamconverter.simple_convert(teams[1][0])]}",
                    value=f"**O/U:** {overunder}\n**Spread:** {spread}\n")

            if len(embed.fields) % 3 != 0:
                for i in range(3 - (len(embed.fields) % 3)):
                    embed.add_field(name="\u200b", value="\u200b")

            if len(embed.fields) == 0: embed.description = "No lines available for the upcoming week."

        else: #bettinglines superbowl was invoked
            url = f"https://www.espn.com/nfl/futures"
            soup = await scrape_and_parse(url)

            table = soup.find("tbody")
            teams = [i.getText() for i in table.findAll("a")][1:][::2]

            table = soup.findAll("tbody")[1]
            odds = [i.getText() for i in table.findAll("td")]

            bettingodds = dict(zip(teams, odds))

            embed = discord.Embed(title="Super Bowl Odds", description="", url=url, color=self.client.color)
            for team, odd in bettingodds.items():
                embed.description += f"{self.client.emoji_dict[self.client.teamconverter.simple_convert(team)]} **{team}** - `{odd}`\n"

            if embed.description == "": embed.description = "No lines available for the Super Bowl."

        await reply(ctx, embed=embed)

    @bettinglines.command(description="Get the betting odds for the super bowl!",
                      aliases=["sb", "super-bowl"], usage="bettinglines superbowl")
    async def superbowl(self):
        #passing because the command superbowl is shadowing this subcommand lol i do all the other stuff in bettinglines
        pass

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get Super Bowl information from a certain year!",
                      aliases=["sb", "super-bowl"], usage="superbowl [year]",
                      help="`year`- The year to get inductees for (optional). Defaults to the last year.")
    async def superbowl(self, ctx, year="2021"):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/super-bowl/"
        soup = await scrape_and_parse(url)

        table = soup.find("tbody")

        embed, value = superbowl_embed(ctx, year, table)
        if not embed:
            return await send_error(ctx, year, "year")

        view = Toggle(ctx, value, 2021, "superbowl", min_value=1967, table=table)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    async def full_scrape(self, soup):
        options = []
        found = 0
        for i, header in enumerate(soup.findAll("h3")):
            if header.getText().lower() == "nfl":
                for headline in soup.findAll('ul')[i].findAll("li"):
                    if found == 5: break

                    title = headline.find("a")["title"]
                    s = await scrape_and_parse(headline.find("a")["href"])

                    desc = s.find('div', {'class': 'article-body'})
                    if desc is None: continue
                    desc = desc.find('p').getText()

                    emojis = [self.client.teamconverter.strict_convert(word) for word in title.split(" ")]
                    for e in emojis.copy():
                        if e is None: emojis.remove(e)
                    if len(emojis) == 0: emojis.append("NFL")

                    shortened_title = title[:95]
                    if shortened_title != title: shortened_title += "..."
                    options.append(
                        [discord.SelectOption(label=shortened_title, emoji=self.client.emoji_dict[emojis[0].lower()]),
                         desc, headline.find("a")["href"], title])
                    found += 1
                break

        return options

    async def team_scrape(self, soup):
        options = []
        found = 0
        for article in soup.findAll("article", {"class": "news-feed-item news-feed-story-package"}):
            if not article.find("div", {"class": "news-feed_item-meta icon-font-before icon-espnplus-before"}):
                title = article.find("h1").getText()
                shortened_title = title[:95]
                if shortened_title != article.find("h1").getText(): shortened_title += "..."
                options.append([discord.SelectOption(label=shortened_title), article.find("p").getText(),
                                "https://www.espn.com"+article.find("h1").find("a")["href"], title])
                found += 1

            if found == 5:
                break

        return options

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the latest ESPN Articles!",
                      aliases=["news"], usage="articles")
    async def articles(self, ctx, team: TeamConverter=None):
        await ctx.trigger_typing()

        if not team:
            url = f"http://www.espn.com/espn/latestnews"
        else:
            url = f"https://www.espn.com/nfl/team/_/name/{self.client.teamconverter.simple_convert(team, 'espn')}/" \
            f"{'-'.join(self.client.teamconverter.simple_convert(team, 'full').split())}"
        soup = await scrape_and_parse(url)

        if not team:
            options = await self.full_scrape(soup)

        else:
            options = await self.team_scrape(soup)

        print(options)

        embed = await dropdown_embed(ctx, 0, options)
        view = DropdownView(ctx, options, options[0][0].label, "articles", soup=soup)
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get the league scores for a certain week!", usage="scores [week]",
                      help="`week`- The NFL week (optional). Defaults to current week.")
    async def scores(self, ctx, week=None):
        await ctx.trigger_typing()

        url = f"https://www.espn.com/nfl/schedule"
        if week:
            url += f"/_/week/{week}/seasontype/2"

        soup = await scrape_and_parse(url)

        embed = discord.Embed(title=f'Scores for {soup.findAll("button", {"class": "button-filter med dropdown-toggle"})[2].text}',
                              color=self.client.color, description="", url=url)

        container = soup.find("div", {"id": "sched-container"})

        for game in container.findAll(re.compile("h2|div")):
            if game.name == "h2":
                embed.description += "\n**"+game.text+"**\n"

            if game.name == "div" and 'responsive-table-wrap' in game.attrs["class"]:
                for row in game.findAll("tr"):
                    if [i.getText() for i in row.findAll("td")] == [] or ["odd", "byeweek"] == row.attrs.get("class") or len(row.findAll("span")) == 0: continue

                    teams = [row.findAll("abbr")[i]["title"] for i in range(2)]
                    date = row.find("td", {"data-behavior": "date_time"})
                    score = row.find("a", {"name": "&lpos=nfl:schedule:score"})
                    if date: date = int(datetime.datetime.strptime(date.attrs["data-date"], "%Y-%m-%dT%H:%MZ").timestamp()) - (5 * 60 * 60)

                    if score: extra = score.text
                    elif date: extra = f"<t:{date}:t>"
                    else: extra = "LIVE"

                    emoji1, emoji2 = [self.client.emoji_dict[self.client.teamconverter.simple_convert(teams[i]) if teams[i].lower() not in ["nfc", "afc"] else teams[i].lower()] for i in range(2)]

                    if score:
                        team = self.client.teamconverter.simple_convert(teams[0], "espn")
                        team = teams[0].upper() if not team else team.upper()
                        scores = [i.split() for i in score.text.split(",")]
                        if team == scores[0][0]:  i1, i2 = 0, 1
                        else: i1, i2 = 1, 0
                        embed.description += f"{emoji1} **{teams[0]}** `{scores[i1][1]} - {scores[i2][1]}` **{teams[1]}** {emoji2}\n"

                    else:
                        embed.description += f"{emoji1} **{teams[0]}** @ **{teams[1]}** {emoji2} {extra}\n"

        await reply(ctx, embed=embed)


def setup(client):
    client.add_cog(League(client))
