import discord
from discord.ext import commands
from static_functions import *
from converters.teamconverter import TeamConverter
from interactions import *

def contracts_embed(ctx, team, splice_dict, url, choice):
    embed = discord.Embed(
        title=f"{ctx.bot.emoji_dict[team.lower()]} {ctx.bot.teamconverter.simple_convert(team, 'reverse').title()} Active Contracts",
        url=url, description="", color=ctx.bot.color)

    for k, v in {k: v for k, v in splice_dict[choice]}.items():
        embed.add_field(name=k.upper(), value="\n".join(v), inline=False)
    embed.set_footer(text=f"Want this team's pending free agents? Type `{ctx.prefix}freeagents {team}`")
    return embed

class Money(commands.Cog, name="Money Commands"):
    def __init__(self, client):
        self.client = client

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get every team's (or a specific team's) current cap space!", aliases=["cap", "cap-space"],
                      usage="capspace")
    async def capspace(self, ctx, team: TeamConverter=None):
        await ctx.trigger_typing()

        url = f"https://www.spotrac.com/nfl/cap/"
        soup = await scrape_and_parse(url)

        table = soup.find("tbody")

        if team is None:
            embed = discord.Embed(title="Cap Space for All 32 Teams", url=url, color=self.client.color, description="")
            for row in table.findAll("tr"):
                stats = [i.getText() for i in row.findAll("td")]
                name = stats[1].strip().split("\n")[0]
                amount = stats[-3].split("$")[1]

                if stats[0] == "League Average":
                    embed.add_field(name="League Average", value=f"`${amount}`")
                else:
                    embed.description += f"**{stats[0]}. {self.client.emoji_dict[self.client.teamconverter.simple_convert(name)]} {name}** - `${amount}`\n"

            return await reply(ctx, embed=embed)

        full_team = self.client.teamconverter.simple_convert(team, "full")

        for row in table.findAll("tr"):
            stats = [i.getText() for i in row.findAll("td")]
            if stats[1].strip().split("\n")[0].lower() == full_team.lower():
                embed = discord.Embed(title=f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Cap Space Info",
                                      url=url, description="", color=self.client.color)

                cap_details = {"Rank": stats[0], "Cap Space": f"${stats[-3].split('$')[1]}", "Signed": stats[2],
                                "Avg. Age": stats[3], "Active Cap": stats[4], "Dead Cap": stats[5]}

                for k, v in cap_details.items():
                    embed.add_field(name=k, value=f"`{v}`")

                embed = add_thumbnail(ctx, team, embed)

                await reply(ctx, embed=embed)
                return

        raise ValueError

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get a player's contract info!", aliases=["salary"], usage="contract <team> <name>",
                      help="`team` - An abbreviation of the team. See `help team` for valid abbreviations.\n"
                           "`name`- An NFL player.")
    async def contract(self, ctx, abbrev, *, name):
        await ctx.trigger_typing()

        name = name.lower().replace("'", "").replace(".", "")
        team = self.client.teamconverter.simple_convert(abbrev, "reverse")
        if team is None:
            await send_error(ctx, abbrev, "team", f"Please provide the team's abbreviation!\n"
                                                  f"Type `{ctx.prefix}help team` for valid team abbreviations!")
            return

        if len(name.split(" ")) < 2:
            await send_error(ctx, name, "name", "Please provide a first and last name!")
            return

        url = f"https://www.spotrac.com/nfl/{'-'.join(team.split(' '))}/{'-'.join(name.split(' '))}/"
        soup = await scrape_and_parse(url)

        if len(soup.findAll("tbody")) == 0:
            await send_error(ctx, name, "name",
                             "Try typing their full name (e.g. not `Chris Carson` but `Christopher Carson`)?")
            return

        table = soup.findAll("tbody")[2]
        contract_info = [[i.getText().strip() for i in row.findAll("td")] for row in
                         table.findAll("tr", {"class": "salaryRow"})][:-1]
        for r in contract_info.copy():
            if r[0].startswith("Pre-6/1 Release") or r[0].startswith("Potential Out"): contract_info.remove(r)

        table = soup.findAll("tbody")[1]
        full_contract = [[i.getText().strip() for i in row.findAll("td")] for row in table.findAll("tr")]
        if "contract" not in full_contract[0][0].lower():
            embed = discord.Embed(description=f"`{name}` does not have an active contract right now!",
                                  color=discord.Color.red())
            return await reply(ctx, embed=embed)

        embed = discord.Embed(
            title=f"{self.client.emoji_dict[self.client.teamconverter.simple_convert(team)]} {name.title()}",
            color=self.client.color, url=url, description="")
        for info in full_contract:
            embed.description += f"**{info[0].strip(':')}:** `{info[1]}`\n"
        for year in contract_info:
            if len(embed.fields) % 3 == 2:
                embed.add_field(name="\u200b", value="\u200b")
            embed.add_field(name=f"{year[0]} Contract", value=f"**Base Salary:** `{year[3]}`\n"
                                                              f"**Signing Bonus:** `{year[4]}`\n"
                                                              f"**Cap Hit:** `{year[-4]}`")
        if len(embed.fields) % 3 == 2: embed.add_field(name="\u200b", value="\u200b")

        embed.set_thumbnail(url=soup.find("div", {"class": "player-logo"}).find("img")["src"])
        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get pending free agents for a certain team!", aliases=["fa", "free-agents"],
                      usage="freeagents <team>",
                      help="`team`- What team to get pending free agents for. See `help team` to see valid teams.")
    async def freeagents(self, ctx, team: TeamConverter):
        await ctx.trigger_typing()

        team_name = self.client.teamconverter.simple_convert(team, "full")
        url = f"https://www.spotrac.com/nfl/free-agents/all/{'-'.join(team_name.split())}/all-statuses/"
        soup = await scrape_and_parse(url)

        table = soup.find("tbody")

        fa_types = {"UFA": [], "RFA": [], "ERFA": []}
        for row in table.findAll("tr"):
            stats = [i.getText() for i in row.findAll("td")]
            player = f'**{stats[1]} {" ".join(stats[0].split()[1:])}** - `{stats[5]}`'
            fa_types[stats[-2]].append(player)

        embed = discord.Embed(
            title=f"{self.client.emoji_dict[team.lower()]} {self.client.teamconverter.simple_convert(team, 'reverse').title()} Pending Free Agents",
            url=url, description="", color=self.client.color)

        for k, v in fa_types.items():
            if len(v) != 0:
                embed.add_field(name=k, value="\n".join(v), inline=False)

        await reply(ctx, embed=embed)

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Get active contracts for every player on a certain team!",
                     usage="contracts <team>",
                     help="`team`- What team to get contracts for. See `help team` to see valid teams.")
    async def contracts(self, ctx, team: TeamConverter):
        await ctx.trigger_typing()

        team_name = self.client.teamconverter.simple_convert(team, "full")
        url = f"https://www.spotrac.com/nfl/{'-'.join(team_name.split())}/contracts/"
        soup = await scrape_and_parse(url)

        table = soup.find("tbody")

        positions = {"qb": [], "rb": [], "wr": [], "te": [], "ol": [], "dl": [], "lb": [], "db": [], "st": []}

        for player in table.findAll("tr"):
            stats = f"**{player.find('td').find('a').getText()}** - `{' '.join([x.getText() for x in player.findAll('td')[4].findAll('span')[1:]])}`"
            if self.client.positionconverter.simple_convert(player.findAll("td")[1].getText()) in positions:
                positions[self.client.positionconverter.simple_convert(player.findAll("td")[1].getText())].append(stats)

        splice_dict = {"offense": list(positions.items())[:5],
                       "defense": list(positions.items())[5:-1],
                       "special teams": list(positions.items())[-1:]}

        embed = contracts_embed(ctx, team, splice_dict, url, "offense")
        view = RosterButton(ctx, team, splice_dict, url, "team contracts")
        msg = await reply(ctx, embed=embed, view=view)
        view.message = msg


def setup(client):
    client.add_cog(Money(client))