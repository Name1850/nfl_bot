import traceback
import discord
from discord.ext import commands
import difflib
from converters.timeconverter import TimeConverter
from static_functions import *

class ErrorHandler(commands.Cog, name="Error Handler"):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title=f"{'Command' if ctx.command.parent is None else 'Subcommand'} Error `{ctx.command}`",
                description=f"{error}", color=discord.Color.red())
            embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.usage}`")

            if ctx.command.parent is None: name = ctx.command.name
            else: name = f"{ctx.command.parent.name} {ctx.command.name}"

            examples = "\n".join([f"`{ctx.prefix}{i}`" for i in example_dict[name]])
            embed.add_field(name="Examples", value=f"{examples}", inline=False)

        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title=f"{'Command' if ctx.command.parent is None else 'Subcommand'} Error `{ctx.command}`",
                description=f"Missing argument `{error.param.name}`.", color=discord.Color.red())
            embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.usage}`")

            if ctx.command.parent is None: name = ctx.command.name
            else: name = f"{ctx.command.parent.name} {ctx.command.name}"

            examples = "\n".join([f"`{ctx.prefix}{i}`" for i in example_dict[name]])
            embed.add_field(name="Examples", value=f"{examples}", inline=False)

        elif isinstance(error, commands.CommandNotFound):
            cmd = ctx.invoked_with
            cmds = []
            for c in self.client.commands:
                if c.cog is not None:
                    if c.cog.qualified_name not in ["Owner", "Live Scores"]:
                        cmds.append(c.name)
                else:
                    cmds.append(c.name)

            best_match = difflib.get_close_matches(cmd, cmds, 1)
            if len(best_match) == 1:
                embed = discord.Embed(title="Command Error",
                                      description=f"Command `{cmd}` not found. Maybe you meant `{best_match[0]}`?",
                                      color=discord.Color.red())
                await ctx.reply(embed=embed)
                return
            else:
                return

        elif isinstance(error, commands.MissingPermissions):
            missingperms = ",".join([f"`{i}`" for i in error.missing_permissions])
            embed = discord.Embed(title="Command Error",
                                  description=f"You are missing the following permissions: {missingperms}.",
                                  color=discord.Color.red())

        elif isinstance(error, commands.BotMissingPermissions):
            missingperms = ",".join([f"`{i}`" for i in error.missing_permissions])
            embed = discord.Embed(title="Command Error",
                                  description=f"I am missing the following permissions: {missingperms}.",
                                  color=discord.Color.red())

        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(title="Command On Cooldown", color=discord.Color.red(),
                                  description=f"The command `{ctx.invoked_with}` is on cooldown. "
                                              f"Try again in `{self.client.timeconverter.simple_convert(float(error.retry_after))}`.")
            await ctx.reply(embed=embed)
            return

        elif isinstance(error, commands.NotOwner):
            return
        else:
            channel = self.client.get_channel(908520601155694624)
            embed = discord.Embed(title=f"{ctx.command.name.title()} Error", color=discord.Color.red(),
                                  description=f"```{''.join(traceback.format_exception(type(error), error, error.__traceback__))}```")
            embed.add_field(name="Error", value=f"`{error}`")
            embed.add_field(name="Type", value=f"`{type(error)}`", inline=False)
            embed.add_field(name="\u200b", value="\u200b")
            embed.add_field(name="Message", value=f"{ctx.message.content}", inline=False)
            await channel.send(embed=embed)

            embed = discord.Embed(title="Command Error",
                                  description="Unknown error. Developers are being alerted about it!",
                                  color=discord.Color.red())

        if random.choice([True, False, False]):
            embed.description += " Report a bug in our [**Support Server**](https://discord.gg/edCYbf3QBE)!"

        await ctx.reply(embed=embed)
        ctx.command.reset_cooldown(ctx)


def setup(client):
    client.add_cog(ErrorHandler(client))
