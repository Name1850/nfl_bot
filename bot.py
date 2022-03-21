import re

import discord
from discord.ext import commands
import os
import pymongo
from help import HelpCommand

from converters.teamconverter import TeamConverter
from converters.sortconverter import SortConverter
from converters.positionconverter import PositionConverter
from converters.timeconverter import TimeConverter
from converters.dateconverter import DateConverter

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = myclient["sports-bot"]
col = db["servers"]


def get_prefix(client, message):
    try:
        doc = col.find({"server_id": message.guild.id})[0]
        prefixes = [doc["prefix"]]

        fallback = os.urandom(32).hex()
        comp = re.compile("^(" + "|".join(map(re.escape, prefixes)) + ").*", flags=re.I)
        match = comp.match(message.content)
        if match is not None:
            return match.group(1)
        return fallback

    except IndexError:
        return ["s!", "S!"]


class NFLBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix=get_prefix, intents=intents, help_command=HelpCommand(), case_insensitive=True)

        self.db = db

        self.sortconverter = SortConverter()
        self.teamconverter = TeamConverter()
        self.positionconverter = PositionConverter()
        self.dateconverter = DateConverter()
        self.timeconverter = TimeConverter()

        self.color = 0x68c4f4
        self.avatar_url = "https://cdn.discordapp.com/avatars/911787246783434792/0f4bda740309b8cef7f34e3fe47d0444.webp?size=1024"
        self.emoji_dict = {'dal': '<:dal:908470026678452237>', 'det': '<:det:908470026691022870>', 'nwe': '<:nwe:908470026858795009>',
                           'crd': '<:ari:908470027047546880>', 'sfo': '<:sfo:908470026879782963>', 'den': '<:den:908470026934321233>',
                           'gnb': '<:gnb:908470026963677214>', 'clt': '<:ind:908470027332767775>', 'nor': '<:nor:908470027001430036>',
                           'nyg': '<:nyg:908470027030769674>', 'tam': '<:tam:908470027039146024>', 'htx': '<:hou:908470027378913291>',
                           'ari': '<:ari:908470027047546880>', 'sea': '<:sea:908470027072704612>', 'lar': '<:lar:908470027123060777>',
                           'oti': '<:ten:908470027584417853>', 'kan': '<:kan:908470027215319070>', 'chi': '<:chi:908470027282423818>',
                           'ind': '<:ind:908470027332767775>', 'car': '<:car:908470027345330228>', 'was': '<:was:929569543242809444>',
                           'mia': '<:mia:908470027353743360>', None: "<:nfl:908576986987921458>", 'cin': '<:cin:908470027370500147>',
                           'lvr': '<:lvr:908470027370500157>', 'hou': '<:hou:908470027378913291>', 'rav': '<:bal:908470027479564309>',
                           'atl': '<:atl:908470027399872534>', 'bal': '<:bal:908470027479564309>', 'buf': '<:buf:908470027504726057>',
                           'cle': '<:cle:908470027529879612>', 'jax': '<:jax:908470027559260211>', 'ten': '<:ten:908470027584417853>',
                           'phi': '<:phi:908470027605405716>', 'lac': '<:lac:908470027613786132>', 'pit': '<:pit:908470027643150376>',
                           'nyj': '<:nyj:908470027831894037>', 'min': '<:min:908470027848654948>', 'nfc': '<:nfc:908543554408820776>',
                           'afc': '<:afc:908543522943152138>', 'sdg': '<:lac:908470027613786132>', 'oak': '<:lvr:908470027370500157>',
                           'stl': '<:lar:908470027123060777>', '': "<:nfl:908576986987921458>", "nfl": "<:nfl:908576986987921458>",
                           "2tm": "<:nfl:908576986987921458>", "ram": '<:lar:908470027123060777>', "rai": '<:lvr:908470027370500157>',
                           "pho": '<:ari:908470027047546880>', "bos": '<:nwe:908470026858795009>', "bcl": '<:ind:908470027332767775>',
                           "nyy": '<:nyg:908470027030769674>', "3tm": "<:nfl:908576986987921458>"}


client = NFLBot()

@client.event
async def on_message(message):
    if message.content == "<@!911787246783434792>":
        try:
            doc = col.find({"server_id": message.guild.id})[0]
            prefix = doc["prefix"]
        except IndexError:
            prefix = "s!"

        embed = discord.Embed(title="Server Info", color=client.color,
                              description=f"My prefix for this server is: `{prefix}`\n"
                                          f"Type `{prefix}help` for a list of commands.")
        await message.reply(embed=embed)

    await client.process_commands(message)


for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load_extension(f"cogs.{filename[:-3]}")
        print(filename, "cog loaded.")

client.run("TOKEN")
