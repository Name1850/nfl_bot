from discord.ext import commands

class SortConverter(commands.Converter):
    def __init__(self):
        self.sort_by_dicts = {"passing": {"cmp": ["pass_cmp", "completions"], "att": ["pass_att", "attempts"], "yds": ["pass_yds", "yards"],
                                         "td": ["pass_td", "touchdowns"], "rate": ["pass_rating", "rating"], "cmp%": ["pass_cmp_perc", "completion %"],
                                         "int": ["pass_int", "interceptions"], "4qc": ["comebacks", "comebacks"], "y/a": ["pass_yds_per_att", "yards per attempt"]},
                              "defense": {"fr": ["fumbles_rec", "fumble recoveries"],
                                          "int": ["def_int", "interceptions"],
                                          "td": ["def_int_td", "pick sixes"], "solo": ["tackles_solo", "solo tackles"],
                                          "tfl": ["tackles_loss", "tackles for loss"],
                                          "ff": ["fumbles_forced", "forced fumbles"],
                                          "pd": ["pass_defended", "passes defended"],
                                          "sfty": ["safety_md", "safeties"], "sk": ["sacks", "sacks"]},
                             "rushing": {"att": ["rush_att", "attempts"], "yds": ["rush_yds", "yards"], "td": ["rush_td", "touchdowns"]},
                             "receiving": {"rec": ["rec", "receptions"], "yds": ["rec_yds", "yards"], "td": ["rec_td", "touchdowns"]},
                             "kicking": {"fg%": ["fg_perc", "field goal %"], "fg long": ["fg_long", "longest field goal"]}}

        self.teamdefense_dict =  {"yds": "yards", "to": "takeaways", "pen": "penalties", "cmp%": "completion %", "int": "interceptions", "pd": "passes defended",
                                  "rate": "rating", "sk": "sacks", "yac": "yards after catch", "bltz%": "blitz%", "prss%": "pressure%",
                                  "mtkl": "missed tackles", "y/a": "yards per attempt"}

    def leader_convert(self, category, argument):
        sort_by_dict = self.sort_by_dicts[category]
        if "cmp%" in sort_by_dict and argument.lower() == "cmp%":
            return "cmp%"
        for k, v in sort_by_dict.items():
            if argument.lower() == k or argument.lower()[:-1] == k or argument.lower() == v[1] or argument.lower() == v[1][:-1]:
                return k

    def teamdefense_convert(self, argument):
        stat = None
        for k, v in self.teamdefense_dict.items():
            if argument.lower() == k or argument.lower()[:-1] == k or argument.lower() == v or argument.lower() == v[:-1]:
                stat = k
                break

        if not stat: return None, None
        important_stats = {0: ["cmp%", "int", "pd", "rate", "sk"],
                           1: ["y/a"],
                           "advanced": ["yac", "bltz%", "prss%", "mtkl"],
                           "normal": ["yds", "to", "pen"]}

        for k, v in important_stats.items():
            if stat in v:
                return stat, k

        return None, None

    def all_time_leader_convert(self, argument):
        if argument.split(" ")[0].lower() == "passing" and " ".join(argument.split(" ")[1:]).lower() == "cmp%" or argument.split(" ")[0].lower() == "cmp%":
            return "pass_cmp_perc"

        if argument.split(" ")[0].lower() in self.sort_by_dicts:
            updated_arg =  " ".join(argument.split(" ")[1:])
            for k, v in self.sort_by_dicts[argument.split(" ")[0].lower()].items():
                if updated_arg.lower() == k or updated_arg.lower()[:-1] == k or updated_arg.lower() == v[1] or updated_arg.lower()== v[1][:-1]:
                    return v[0]
        else:
            for sort_by_dict in self.sort_by_dicts.values():
                for k, v in sort_by_dict.items():
                    if argument.lower() == k or argument.lower()[:-1] == k or argument.lower() == v[1] or argument.lower() == v[1][:-1]:
                        return v[0]
