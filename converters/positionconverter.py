from discord.ext import commands

class PositionConverter(commands.Converter):
    def __init__(self):
        self.convert_dict = {"qb": ["qb"], "rb": ["rb", "hb"], "wr": ["wr"], "te": ["te"],
                         "ol": ["rt", "lt", "c", "rg", "lg", "g", "t", "ol", "og", "ot", "ls"],
                         "dl": ["dl", "de", "dt", "nt", "le", "re", "rde", "lde", "ldt", "rdt"],
                         "lb": ["olb", "ilb", "mlb", "rolb", "lolb", "lb", "rilb", "lilb"],
                         "db": ["cb", "lcb", "rcb", "ss", "fs", "s", "db"],
                         "st": ["k", "p", "pk", "ret", "pr", "kr", "st"]}

    async def convert(self, ctx, argument):
        for k, v in self.convert_dict.items():
            if argument.lower() == k or argument.lower() in v:
                return k

        raise commands.BadArgument(message=f"`{argument}` is not a valid position!")

    def simple_convert(self, argument):
        for k, v in self.convert_dict.items():
            if argument.lower() == k or argument.lower() in v:
                return k
