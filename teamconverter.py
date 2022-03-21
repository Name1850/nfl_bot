from discord.ext import commands

class TeamConverter(commands.Converter):
    def __init__(self):
        self.convert_dict = {('chicago bears', 'CHI', 'CHI', "bears"): 'CHI', ('detroit lions', 'DET', 'DET', "lions"): 'DET', ('minnesota vikings', 'MIN', 'MIN', "vikes"): 'MIN',
                             ('green bay packers', 'GB', 'GB', "pack"): 'GNB', ('washington football team', 'WAS', 'WAS', "wft"): 'WAS', ('philadelphia eagles', 'PHI', 'PHI', "eagles"): 'PHI',
                             ('new york giants', 'NYG', 'NYG', "giants"): 'NYG', ('dallas cowboys', 'DAL', 'DAL', "cowboys"): 'DAL', ('new orleans saints', 'NO', 'NO', "saints"): 'NOR',
                             ('tampa bay buccaneers', 'TB', 'TB', "bucs"): 'TAM', ('carolina panthers', 'CAR', 'CAR', "panthers"): 'CAR', ('atlanta falcons', 'ATL', 'ATL', "falcons"): 'ATL',
                             ('seattle seahawks', 'SEA', 'SEA', "hawks"): 'SEA', ('los angeles rams', 'LAR', 'LAR', "rams"): 'RAM', ('san francisco 49ers', 'SF', 'SF', "9ers"): 'SFO',
                             ('arizona cardinals', 'ARI', 'ARI', "cards"): 'CRD', ('pittsburgh steelers', 'PIT', 'PIT', "steelers"): 'PIT', ('baltimore ravens', 'BAL', 'BAL', "ravens"): 'RAV',
                             ('cleveland browns', 'CLE', 'CLE', "browns"): 'CLE', ('cincinnati bengals', 'CIN', 'CIN', "bengals"): 'CIN', ('new england patriots', 'NE', 'NE', "pats"): 'NWE',
                             ('miami dolphins', 'MIA', 'MIA', "fins"): 'MIA', ('buffalo bills', 'BUF', 'BUF', "bills"): 'BUF', ('new york jets', 'NYJ', 'NYJ', "kets"): 'NYJ',
                             ('tennessee titans', 'TEN', 'TEN', "titans"): 'OTI', ('houston texans', 'HOU', 'HOU', "texans"): 'HTX', ('jacksonville jaguars', 'JAX', 'JAX', "jags"): 'JAX',
                             ('indianapolis colts', 'IND', 'IND', "colts"): 'CLT', ('kansas city chiefs', 'KC', 'KC', "chiefs"): 'KAN', ('denver broncos', 'DEN', 'DEN', "broncos"): 'DEN',
                             ('las vegas raiders', 'LV', 'LVR', "raiders"): 'RAI', ('los angeles chargers', 'LAC', 'LAC', "chargers"): 'SDG',
                             #old teams
                             ("oakland raiders", "OAK", "OAK", "old_team"): "RAI", ('washington redskins', 'WAS', 'WAS', "old_team"): 'WAS', ('st. louis rams', 'STL', 'STL', "old_team"): 'RAM',
                             ("san diego chargers", "SD", "SDG", "old_team"): "SDG", ('st. louis cardinals', 'STL', 'STL', "old_team"): 'CRD', ("baltimore colts", "BAL", "BAL", "old_team"): "CLT",
                             ("los angeles raiders", "LAR", "LAR", "old_team"): "RAI"
                             }


    def type_conversion(self, key, conversion_type):
        if conversion_type == "espn" and key[1] == "WAS": return "WSH"
        conversion_dict = {"normal": self.convert_dict[key].lower(), "current abbrev": key[1], "espn": key[1], "full": key[0], "city": key[0].split()[:-1]}
        try:
            return conversion_dict[conversion_type]
        except KeyError:
            return key[0].lower()

    def conversion(self, argument, conversion_type):
        for key in self.convert_dict.keys():
            if argument.lower() in key or argument.lower() in key[0].split(" ") or argument.upper() in key or argument.upper() == self.convert_dict[key]:
                return self.type_conversion(key, conversion_type)

        for key in self.convert_dict.keys():
            if argument.lower() in key[0]:
                return self.type_conversion(key, conversion_type)


    async def convert(self, ctx, argument):
        converted_value = self.conversion(argument, "normal")
        if converted_value is not None: return converted_value

        raise commands.BadArgument(message=f"`{argument}` is not a valid team! See `{ctx.prefix}help team` for valid team abbreviations!")

    def simple_convert(self, argument, conversion_type="normal"):
        return self.conversion(argument, conversion_type)


    def strict_convert(self, argument):
        if argument.lower() == "football": return
        for key in self.convert_dict.keys():
            if (argument.lower() in key[0].split(" ") or argument[:-1].lower() in key[0].split(" ") or argument[:-2].lower() in key[0].split(" ") or\
                    argument.lower() == key[3] or argument[:-2].lower() == key[3]) and key[3] != "old_team":
                return self.convert_dict[key]
