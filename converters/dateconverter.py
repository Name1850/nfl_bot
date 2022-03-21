import discord
from discord.ext import commands

class DateConverter(commands.Converter):
    def __init__(self):
        self.dates = [["january", "jan"], ["february", "feb", "febuary"], ["march", "mar"], ["april", "apr"],
                      ["may", "may"], ["june", "jun"], ["july", "jul"], ["august", "aug"],
                      ["september", "sep"], ["october", "oct"], ["november", "nov"], ["december", "dec"]]

    def real_date(self, month, day):
        if int(day) >= 32:
            return False
        if int(day) >= 31 and int(month) in [2, 4, 6, 9, 11]:
            return False
        if int(day) >= 30 and int(month) == 2:
            return False
        return True

    async def convert(self, ctx, argument):
        if len(argument.split("/")) == 2:
            month, day = argument.split("/")
            try:
                if self.real_date(int(month), int(day)):
                    return (int(month), int(day)), f"{self.dates[int(month)-1][0].title()} {day}"
            except:
                pass

        elif len(argument.split(" ")) == 2:
            if argument.split(" ")[0].isdigit(): day, month = argument.split(" ")
            elif argument.split(" ")[1].isdigit(): month, day = argument.split(" ")
            else: return (0, 0), "Today"

            for i, date in enumerate(self.dates):
                if month.lower() in date and self.real_date(int(i+1), int(day)):
                    return (i+1, int(day)), f"{date[0].title()} {day}"

        return (0, 0), "Today"
