import discord
from io import BytesIO
import numpy as np
from adjustText import adjust_text
from discord.ext import commands
from bs4 import Comment
from matplotlib import pyplot as plt
import matplotlib as mpl
from static_functions import *
import pandas as pd


class Information(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.command(description="Display a graph for TD/INT ratios among QBs!",
                      usage="tdint")
    async def tdint(self, ctx):
        await ctx.trigger_typing()

        url = f"https://www.pro-football-reference.com/years/2021/passing.htm"
        stats_page = await scrape_and_parse(url)

        table = stats_page.find('table')
        players = table.find('tbody')
        players_stats = [[i.getText() for i in player.findAll("td")] for player in players.findAll("tr")]
        for player in players_stats.copy():
            if player == [] or not is_number(player[11]):
                players_stats.remove(player)

        tdint = []
        for i in range(32):
            tdint.append([players_stats[i][0], (players_stats[i][11], players_stats[i][13])])

        x = np.array([int(player[1][0]) for player in tdint])
        y = np.array([int(player[1][1]) for player in tdint])

        fig, ax = plt.subplots()
        ax.scatter(x, y)

        texts = []
        for i in range(len(tdint)):
            texts.append(ax.text(x[i], y[i], tdint[i][0], fontsize=7))
        adjust_text(texts)

        plt.xlabel('Touchdowns')
        plt.ylabel('Interceptions')

        buffer = BytesIO()
        fig.savefig(buffer)
        buffer.seek(0)

        f = discord.File(buffer, filename="image.png")
        embed = discord.Embed(title="TD/INT Ratio For top 32 QBs", color=self.client.color)
        embed.set_image(url="attachment://image.png")
        await reply(ctx, embed=embed, file=f)

    def update_name(self, name):
        listname = name.split(" ")
        first = listname[0]
        first = first.replace(".", "")

        listname[0] = first
        name1 = " ".join(listname)

        first = ".".join(list(first))
        first += "."
        listname[0] = first
        name2 = " ".join(listname)

        return name1, name2

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(description="Display a radar chart for a player! Inspired by towardsdatascience.com!",
                      usage="radar <position> <name>",
                      help="`position`- Either `passing`, `receiving`, `defense`, `teamdefense` or `rushing`."
                           "`name`- An NFL player or team (if you choose teamdefense).")
    async def radar(self, ctx, position, *, name):
        await ctx.trigger_typing()

        if position.lower() not in ["passing", "rushing", "receiving", "defense", "teamdefense"]:
            return await send_error(ctx, position, "position",
                                    "Either `passing`, `receiving`, `defense`, `teamdefense` or `rushing`!")

        if position.lower() != "teamdefense":
            name1, name2 = self.update_name(name)
            if position.lower() == "defense":
                headers = ["player", "tm", "age", "pos", "g", "gs", "int", "yds", "td", "lng", "pd", "ff", "fmb", "fr",
                           "yds", "td", "sk", "comb", "solo", "ast", "tfl", "qbhits", "sfty"]
                rows = []
                for player in self.client.db["defense"].find():
                    rows.append([player["player"]] + player["stats"])


            else:
                url = f"https://www.pro-football-reference.com/years/2021/{position.lower()}.htm"
                stats_page = await scrape_and_parse(url)

                headers = [i.getText().lower() for i in
                           stats_page.find("thead").findAll("tr")[1 if position.lower() in ["rushing"] else 0].findAll(
                               "th")][1:]
                rows = []
                table = stats_page.findAll("tbody")[0]
                for player in table:
                    try:
                        rows.append([i.getText() for i in player.findAll("td")])
                    except:
                        pass

                for row in rows.copy():
                    if row == []: rows.remove(row)

            splice = {"passing": ["att", 5, "attempts"], "rushing": ["att", 5, "attempts"],
                      "receiving": ["tgt", 3, "targets"], "defense": ["solo", 1.5, "tackles"]}

            baseline = int(rows[0][headers.index("g")])
            for i in range(5):
                if int(rows[i + 1][headers.index("g")]) > baseline:
                    baseline = int(rows[i + 1][headers.index("g")])

            for row in rows.copy():
                try:
                    if float(row[headers.index(splice[position.lower()][0])]) < baseline * splice[position.lower()][1]:
                        rows.remove(row)
                except ValueError:
                    rows.remove(row)

            category_dict = {"passing": ['Yds', 'TD', 'INT', 'Cmp%', 'Y/A', 'Rate'],
                             "rushing": ['Yds', "TD", "Att", "Y/A", "Fmb"],
                             "receiving": ["Yds", "TD", "Rec", "Ctch%", "Y/R", "Fmb"],
                             "defense": ["INT", "PD", "FF", "Sk", "Solo"]}
            categories = category_dict[position.lower()]
            column_headers = ['Player', 'Tm'] + categories

            for i, qb in enumerate(rows):
                stats = []
                for x in categories:
                    if str(qb[headers.index(x.lower())]).replace("%", "").strip() != "":
                        stats.append(float(str(qb[headers.index(x.lower())]).replace("%", "").strip()))
                    else:
                        stats.append(0)

                r = [str(qb[0]).replace("*", "").replace("+", "").strip().lower(), qb[
                    1]] + stats  # [float(str(qb[headers.index(x.lower())]).replace("%", "").strip()) for x in categories]
                rows[i] = r

            team = None
            for row in rows:
                if row[0].lower() == name.lower() or row[1].lower() == name1.lower() or row[0].lower() == name2.lower():
                    team = self.client.teamconverter.simple_convert(row[1]).upper()

            if team is None:
                min_amount = splice[position.lower()]
                await send_error(ctx, name, "name",
                                 f"Did you misspell their name? Also, they need at least `{min_amount[1]}` {min_amount[2]} per game (`{baseline * splice[position.lower()][1]}` in total) to qualify for a radar chart!")
                return

        else:
            if self.client.teamconverter.simple_convert(name) is None:
                return await send_error(ctx, name, "team")

            url = f"https://www.pro-football-reference.com/years/2021/opp.htm"
            soup = await scrape_and_parse(url)

            rows = []
            table = soup.findAll("tbody")[0]
            for row in table.findAll("tr"):
                x = [i.getText() for i in row.findAll("td")]
                rows.append([x[0].lower(), x[6], int(x[3])/int(x[1])])

            important_stats = {0: ["Y/G", "Sk"],
                               1: ["Y/G"],
                               4: ["Pts/G", "RshTD", "RecTD"]}

            j = 0
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                if '<table' in comment:
                    if j in important_stats:
                        soup_table = BeautifulSoup(comment, "lxml")
                        table = soup_table.findAll('table')[0]

                        column_headers = [i.getText() for i in table.find("thead").findAll("th")][1:]

                        teams = [[i.getText() for i in row.findAll("td")] for row in table.findAll("tr")][1:-3]
                        for team in teams:
                            updated_stats = []
                            for x in important_stats[j]:
                                updated_stats.append(team[column_headers.index(x)])

                            for e in updated_stats: rows[[x[0] for x in rows].index(team[0].lower())].append(e)

                    j += 1

            for i, row in enumerate(rows):
                total = int(row[-2]) + int(row[-1])
                rows[i] = row[:-2]
                rows[i].append(total)
                rows[i] = [rows[i][0]] + [float(j) for j in rows[i][1:]]

            categories = ["TO", "Y/G", "P Y/G", "Sk", "R Y/G", "Pts/G", "TD"]
            column_headers = ["Player"] + categories
            team = self.client.teamconverter.simple_convert(name).upper()

        df = pd.DataFrame(rows, columns=column_headers)

        for i in categories:
            df[i + '_Rank'] = df[i].rank(pct=True)

        if position.lower() == "passing":
            df['INT_Rank'] = 1 - df['INT_Rank']
        elif position.lower() in ["rushing", "receiving"]:
            df['Fmb_Rank'] = 1 - df['Fmb_Rank']
        elif position.lower() == "teamdefense":
            for reverse in ["TD", "Y/G", "P Y/G", "R Y/G", "Pts/G"]: df[f"{reverse}_Rank"] = 1 - df[f"{reverse}_Rank"]

        team_colors = {'CRD': '#97233f', 'ATL': '#a71930', 'RAV': '#241773', 'BUF': '#00338d', 'CAR': '#0085ca',
                       'CHI': '#0b162a', 'CIN': '#fb4f14', 'CLE': '#311d00', 'DAL': '#041e42', 'DEN': '#002244',
                       'DET': '#0076b6', 'GNB': '#203731', 'HTX': '#03202f', 'CLT': '#002c5f', 'JAX': '#006778',
                       'KAN': '#e31837', 'SDG': '#002a5e', 'RAM': '#003594', 'MIA': '#008e97', 'MIN': '#4f2683',
                       'NWE': '#002244', 'NOR': '#d3bc8d', 'NYG': '#0b2265', 'NYJ': '#125740', 'RAI': '#000000',
                       'PHI': '#004c54', 'PIT': '#ffb612', 'SFO': '#aa0000', 'SEA': '#002244', 'TAM': '#d50a0a',
                       'OTI': '#0c2340', 'WAS': '#773141'}

        secondary_colors = {'CRD': '#FFB612', 'BUF': '#C60C30', 'CHI': '#C83803', 'CIN': '#101820', 'CLE': '#FF3C00',
                            'DAL': '#869397',
                            'DEN': '#FB4F14', 'DET': '#B0B7BC', 'GNB': '#FFB612', 'HTX': '#A71930', 'CLT': '#A2AAAD',
                            'JAX': '#D7A22A',
                            'KAN': '#FFB81C', 'SDG': '#FFC20E', 'RAM': '#ffd100', 'MIA': '#F26A24', 'MIN': '#FFB81C',
                            'NWE': '#C60C30',
                            'NOR': '#000000', 'NYG': '#A71930', 'NYJ': '#003F2D', 'PHI': '#A5ACAF', 'PIT': '#101820',
                            'SFO': '#B3995D',
                            'SEA': '#69BE28', 'TAM': '#0A0A08', 'OTI': '#4495D1', "ATL": "#000000", "RAV": "#000000",
                            "CAR": "#000000",
                            "RAI": "#A5ACAF", "WAS": "#FFB612"}

        mpl.rcParams['font.size'] = 16
        mpl.rcParams['xtick.major.pad'] = 15
        mpl.rcParams['xtick.color'] = "#FFFFFF"

        offset = np.pi / 6
        angles = np.linspace(0, 2 * np.pi, len(categories) + 1) + offset

        def create_radar_chart(ax, player_data, color):
            ax.plot(angles, np.append(player_data[-(len(angles) - 1):], player_data[-(len(angles) - 1)]),
                    color=team_colors[color], linewidth=2)
            ax.fill(angles, np.append(player_data[-(len(angles) - 1):], player_data[-(len(angles) - 1)]),
                    color="#FFFFFF", alpha=0.2)

            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)
            ax.set_yticklabels([])

            ax.text(0, 0, player_data[0].title(), ha='center', va='center', size=25, color=secondary_colors[color],
                    fontweight="bold")

        def get_data(data):
            try:
                return np.asarray(data[data['Player'] == name.lower()])[0]
            except IndexError:
                try:
                    return np.asarray(data[data['Player'] == name1.lower()])[0]
                except IndexError:
                    return np.asarray(data[data['Player'] == name2.lower()])[0]
                except NameError:
                    return \
                    np.asarray(data[data['Player'] == self.client.teamconverter.simple_convert(name, "reverse").lower()])[0]

        fig = plt.figure(figsize=(8, 8), facecolor='white')
        ax = fig.add_subplot(projection='polar', facecolor='#ededed')
        data = get_data(df)
        ax = create_radar_chart(ax, data, team)

        buffer = BytesIO()
        fig.savefig(buffer, transparent=True, bbox_inches='tight', pad_inches=0)
        buffer.seek(0)

        f = discord.File(buffer, filename="image.png")
        embed = discord.Embed(color=self.client.color)
        embed.set_image(url="attachment://image.png")
        await reply(ctx, embed=embed, file=f)

        mpl.rcParams['font.size'] = 10
        mpl.rcParams['xtick.major.pad'] = 3.5

def setup(client):
    client.add_cog(Information(client))
