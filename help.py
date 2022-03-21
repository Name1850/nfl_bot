import discord
from discord.ext import commands
from interactions import *
from static_functions import example_dict, reply
from converters.timeconverter import TimeConverter
from converters.teamconverter import TeamConverter
from converters.sortconverter import SortConverter

def dropdown_check(ctx, value):
    cog = ctx.bot.get_cog(value)
    cmds = cog.walk_commands()

    embed = discord.Embed(title=f"{cog.qualified_name} Help", color=ctx.bot.color)
    for cmd in cmds: embed.add_field(name=str(cmd), inline=False, value=f"{cmd.description}\n")
    embed.set_footer(text=f"Type `{ctx.prefix}help <command>` for more info on a command.")

    return embed

timeconverter = TimeConverter()
teamconverter = TeamConverter()
sortconverter = SortConverter()

class HelpCommand(commands.HelpCommand):
    def command_help(self, command):
        embed = discord.Embed(title=f"{'Command' if command.parent is None else 'Subcommand'} Help `{command}`",
                              description=command.description, color=self.context.bot.color)

        embed.add_field(name="Usage", inline=False,
                        value=f"`{self.context.prefix}{command.usage}`")
        embed.add_field(name="Examples",
                        value=f"\n".join([f'`{self.context.prefix}{ex}`' for ex in example_dict[str(command)]]),
                        inline=False)
        if len(command.aliases) > 0:
            embed.add_field(name="Aliases",
                            value="\n".join([f'`{self.context.prefix}{alias}`' for alias in command.aliases]),
                            inline=False)
        if command.help is not None:
            embed.add_field(name="Parameters", value=command.help, inline=False)

        bucket = command if command.parent is None else command.parent
        cooldown = bucket._buckets._cooldown
        embed.add_field(name="Cooldown", value=f'`{timeconverter.simple_convert(float(cooldown.per))}`')

        return embed

    async def send_bot_help(self, mapping):
        all_cogs = list(self.context.bot.cogs)
        for c in ["Owner", "Error Handler", "Event Handler", "Live Scores"]:
            all_cogs.remove(c)

        embed = dropdown_check(self.context, "Player Stats")
        options = [discord.SelectOption(label=x) for x in all_cogs]
        view = DropdownView(self.context, options, "Player Stats", "help")

        msg = await reply(self.context, embed=embed, view=view)
        view.message = msg

    async def send_command_help(self, command):
        if command.cog is not None:
            if command.cog.qualified_name in ["Owner", "Error Handler", "Event Handler", "Live Scores"]:
                embed = discord.Embed(title="Help Error", description=f"Command `{command}` not found.",
                                      color=discord.Color.red())
                return await reply(self.context, embed=embed)
        if command.cog is None:
            return await reply(self.context, content="help")
        embed = self.command_help(command)
        await reply(self.context, embed=embed)

    async def send_group_help(self, group):
        embed = self.command_help(group)
        await reply(self.context, embed=embed)

    async def send_cog_help(self, cog):
        cmds = cog.walk_commands()
        embed = discord.Embed(title=f"{cog.qualified_name} Help", color=self.context.bot.color)
        for cmd in cmds:
            embed.add_field(name=str(cmd), inline=False, value=f"{cmd.description}\n")

        embed.set_footer(text=f"Type `{self.context.prefix}help <command>` for more info on a command.")
        await reply(self.context, embed=embed)

    async def send_error_message(self, error):
        command = " ".join(self.context.message.content.split(" ")[1:]).lower()
        cog = self.context.bot.get_cog(command.title())
        if cog is not None and cog.qualified_name not in ["Owner", "Error Handler", "Event Handler", "Live Scores"]:
            return await self.send_cog_help(cog)

        if command == "team":
            embed = discord.Embed(title="Team abbreviations", color=self.context.bot.color)
            for i in range(2):
                value = ""
                for j in range(16):
                    key = list(teamconverter.convert_dict)[(i * 16) + j]
                    value += f"{self.context.bot.emoji_dict[teamconverter.simple_convert(key[1])]} **{key[0].title()}:** `{key[1]}`\n"
                embed.add_field(name="\u200b", value=value)

            await reply(self.context, embed=embed)
            return

        if command == "sort":
            embed = discord.Embed(title="Sort Help", color=self.context.bot.color,
                                  description="When searching up `alltimeleaders`, and sorting by `attempts`, `touchdowns`, `interceptions` or `yards`, type the category and the sort_by! "
                                              "E.G. `rushing attempts` or `receiving yards`, not just `attempts` or `yards`.")
            for sort_by_dict in sortconverter.sort_by_dicts:
                value = ""
                for k, v in sortconverter.sort_by_dicts[sort_by_dict].items():
                    value += f"**{v[1].title()}:** `{k.title()}`\n"
                embed.add_field(name=sort_by_dict.title(), value=value)

                if sort_by_dict == "defense":
                    value = ""
                    for k, v in sortconverter.teamdefense_dict.items():
                        value += f"**{v.title()}:** `{k.title()}`\n"
                    embed.add_field(name="Teamdefense", value=value)

            return await reply(self.context, embed=embed)

        embed = discord.Embed(title="Help Error", description=f"Command `{command}` not found.", color=discord.Color.red())
        await reply(self.context, embed=embed)
