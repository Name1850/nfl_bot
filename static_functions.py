import random
import discord
import aiohttp
from bs4 import BeautifulSoup

example_dict = {"scores": ["scores", "scores 7"],
                "schedule": ["schedule bears", "schedule chi"],
                "injuries": ["injuries jacksonville", "injuries jacksonville jaguars"],
                "roster": ["roster 49ers", "roster sf"],
                "teaminfo": ["teaminfo phi", "teaminfo philadelphia"],
                "draft": ["draft", "draft 4", "draft 1 2013"],
                "probowl": ["probowl qb", "probowl rb 2019"],
                "allpro": ["allpro ol", "allpro db 2016"],
                "allrookie": ["allrookie", "allrookie 2019"],
                "awards": ["awards", "awards 2013"],
                "top100": ["top100", "top100 2018"],
                "winprobability": ["winprobability"],
                "standings": ["standings", "standings nfc", "standings 2019", "standings 2019 afc"],
                "playoffs": ["playoffs", "playoffs afc", "playoffs 2019", "playoffs 2019 nfc"],
                "bettinglines": ["bettinglines"],
                "bettinglines superbowl": ["bettinglines superbowl"],
                "leaders": ["leaders passing int", "leaders rushing td"],
                "stats": ["stats justin fields", "stats career lawrence taylor"],
                "tdint": ["tdint"],
                "alltimeleaders": ["alltimeleaders singleseason pass yards",
                                   "alltimeleaders singlegame defense interceptions"],
                "stats current": ["stats current justin fields", "stats current trevor lawrence"],
                "stats career": ["stats career lawrence taylor", "stats career walter payton"],
                "stats fantasy": ["stats fantasy lamar jackson", "stats fantasy derrick henry"],
                "stats playoffs": ["stats playoffs tom brady", "stats playoffs russell wilson"],
                "stats year": ["stats year 2009 matt hasselbeck", "stats year 2017 tom brady"],
                "alltimeleaders singleseason": ["alltimeleaders singleseason passing yards",
                                                "alltimeleaders singleseason defense int"],
                "alltimeleaders singlegame": ["alltimeleaders singlegame sfty",
                                              "alltimeleaders singlegame cmp"],
                "alltimeleaders career": ["alltimeleaders career rate", "alltimeleaders career receiving td"],
                "changeprefix": ["changeprefix !", 'changeprefix "sports "'],
                "follow": ["follow"],
                "ping": ["ping"],
                "contract": ["contract chi justin fields", "contract sea russell wilson"],
                "halloffame": ["halloffame", "halloffame 2015"],
                "passerrating": ["passerrating"],
                "undefeated": ["undefeated", "undefeated 2017"],
                "birthdays": ["birthdays"],
                "playerinfo": ["playerinfo justin fields", "playerinfo lawrence taylor"],
                "superbowl": ["superbowl", "superbowl 1986", "superbowl xx", "superbowl 20"],
                "radar": ["radar passing kyler murray", "radar rushing jonathan taylor", "radar defense trevon diggs"],
                "teamdefense": ["teamdefense seattle", "teamdefense seattle seahawks"],
                "starters": ["starters denver", "starters broncos"],
                "transactions": ["transactions new england", "transactions patriots"],
                "articles": ["articles"],
                "playerawards": ["playerawards walter payton", "playerawards tom brady"],
                "support": ["support", "vote", "server", "invite"],
                "ask": ["ask most sacks in a season", "ask tom brady stats"],
                "game": ["game 401326541"],
                "gamelog": ["gamelog justin fields", "gamelog 6 justin fields"],
                "leaders passing": ["leaders passing tds", "leaders passing yards"],
                "leaders rushing": ["leaders rushing tds", "leaders rushing yards"],
                "leaders receiving": ["leaders receiving tds", "leaders receiving yards"],
                "leaders defense": ["leaders defense sacks", "leaders defense ints"],
                "leaders salary": ["leaders salary value", "leaders salary bonus"],
                "leaders fantasy": ["leaders fantasy"],
                "leaders teamdefense": ["leaders teadefense y/g", "leaders teamdefense yds"],
                "capspace": ["capspace", "capspace dolphins"],
                "freeagents": ["freeagents denver", "freeagents broncos"],
                "contracts": ["contracts buf", "contracts buffalo bills"],
                "teamdraft": ["teamdraft raiders", "teamdraft lv"]
                }


def is_number(num):
    try:
        int(num)
        return True
    except ValueError:
        try:
            float(num)
            return True
        except ValueError:
            return False

def is_int(num):
    try:
        int(num)
        return True
    except ValueError:
        return False

async def send_error(ctx, param, expected, extra=""):
    embed = discord.Embed(title=f"{'Command' if ctx.command.parent is None else 'Subcommand'} Error `{ctx.command}`",
                          description=f"`{param}` is not a valid {expected}! {extra}", color=discord.Color.red())
    embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.usage}`")

    if ctx.command.parent is None: name = ctx.command.name
    else: name = f"{ctx.command.parent.name} {ctx.command.name}"
    examples = "\n".join([f"`{ctx.prefix}{i}`" for i in example_dict[name]])
    embed.add_field(name="Examples", value=f"{examples}", inline=False)

    if random.choice([True, False, False]):
        embed.description += " Report a bug in our [**Support Server**](https://discord.gg/edCYbf3QBE)!"

    await ctx.reply(embed=embed)
    ctx.command.reset_cooldown(ctx)

async def subcommand_error(ctx):
    value = "Please choose one of the subcommands:\n"
    for subcmd in ctx.command.walk_commands():
        value += f"`{ctx.command} {subcmd.name}`\n"
    value = value[:-1]
    embed = discord.Embed(title=f"Command Error `{ctx.command}`", description=value, color=discord.Color.red())
    embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.usage}`")

    examples = "\n".join([f"`{ctx.prefix}{i}`" for i in example_dict[ctx.command.name]])
    embed.add_field(name="Examples", value=f"{examples}", inline=False)

    if random.choice([True, False, False]):
        embed.description += " Report a bug in our [**Support Server**](https://discord.gg/edCYbf3QBE)!"

    await ctx.reply(embed=embed)
    ctx.command.reset_cooldown(ctx)

async def check_404(ctx, request, param, expected, extra=""):
    if request.status == 404:
        await send_error(ctx, param, expected, extra=extra)
        return True
    return False

async def reply(ctx, content="", embed=None, file=None, view=None):
    try:
        await ctx.channel.fetch_message(ctx.message.id)
    except discord.NotFound:
        content += ctx.author.mention
        return await ctx.send(content, embed=embed, file=file, view=view)
    else:
        return await ctx.reply(content, embed=embed, file=file, view=view)

def add_thumbnail(ctx, team, embed):
    emoji = ctx.bot.emoji_dict[team.lower()]
    embed.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/{emoji.split(':')[-1].strip('>')}.png?v=1")
    return embed

async def scrape_and_parse(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            soup = BeautifulSoup(await r.read(), features="lxml")

    return soup