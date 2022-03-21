import discord
from discord.ext import commands
import math

class TimeConverter(commands.Converter):
    def __init__(self):
        self.time_dict = {"d":86400, "h":3600, "m":60, "s":1}

    def simple_convert(self, argument: float):
        argument = math.ceil(argument)
        string = ""
        for data, unit in self.time_dict.items():
            if argument//unit > 0:
                string += f"{argument//unit}{data} "
            argument -= (argument//unit)*unit

        return string.strip()