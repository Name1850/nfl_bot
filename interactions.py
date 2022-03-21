import discord
from cogs.league import draft_embed, espn_embed, pfr_loop, playoff_embed, dropdown_embed, superbowl_embed
from cogs.teams import roster_embed, team_draft_embed
from cogs.stats import gamelog_embed, stats_embed
from cogs.money import contracts_embed
from cogs.misc import undefeated_embed
from cogs.accolades import award_embed, hof_embed
from cogs.leaders import leaders_embed, alltimeleaders_embed, salaryleaders_embed
import help

class Dropdown(discord.ui.Select):
    def __init__(self, options, placeholder, choice):
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=[x[0] for x in options] if choice == "articles" else options
        )
        self.choice = choice
        self.value = None

    async def callback(self, interaction: discord.Interaction):
        self.value = self.values[0]
        self.placeholder = self.value
        if self.choice == "help":
            await interaction.response.edit_message(embed=help.dropdown_check(self.view.ctx, self.value), view=self.view)
        elif self.choice == "articles":
            index = [x.label for x in self.options].index(self.value)
            await interaction.response.edit_message(embed=await dropdown_embed(self.view.ctx, index, self.view.options), view=self.view)
        elif self.choice == "stats":
            self.view.stop()

class DropdownView(discord.ui.View):
    def __init__(self, ctx, options, placeholder, choice, timeout=30, soup=None, index=0):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.add_item(Dropdown(options, placeholder, choice))
        self.message = None

        self.choice = choice
        self.soup = soup
        self.index = index
        self.options = options

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't interact with this.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(self.message.content, view=self)

class ButtonView(discord.ui.View):
    def __init__(self, buttons):
        super().__init__()
        for button in buttons:
            self.add_item(button)


class ConferenceButton(discord.ui.View):
    def __init__(self, ctx, conf_dicts, soup, conf, year=None, playoff=False):
        super().__init__(timeout=30)
        self.soup = soup
        self.year = year
        self.conf_dicts = conf_dicts
        self.conf = conf
        self.ctx = ctx
        self.message = None
        self.playoff = playoff

    async def edit_response_message(self, interaction):
        if self.playoff:
            await interaction.response.edit_message(embed=playoff_embed(self.ctx, self.soup, self.conf_dicts[self.conf.upper()], self.conf))
        elif self.year is None:
            await interaction.response.edit_message(embed=espn_embed(self.ctx, self.soup, self.conf, self.conf_dicts[self.conf]))
        else:
            await interaction.response.edit_message(embed=pfr_loop(self.ctx, self.soup, self.conf, self.conf_dicts[self.conf], self.year))

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't interact with this.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="NFC", style=discord.ButtonStyle.blurple, emoji="<:nfc:908543554408820776>")
    async def nfc(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.conf = "NFC"
        await self.edit_response_message(interaction)

    @discord.ui.button(label="AFC", style=discord.ButtonStyle.blurple, emoji="<:afc:908543522943152138>")
    async def afc(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.conf = "AFC"
        await self.edit_response_message(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(self.message.content, view=self)

class RosterButton(discord.ui.View):
    def __init__(self, ctx, team, splice_dict, url, choice):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.message = None
        self.team = team
        self.splice_dict = splice_dict
        self.url = url
        self.choice = choice

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't interact with this.", ephemeral=True)
            return False
        return True

    async def edit_response_message(self, interaction, choice):
        if self.choice == "roster":
            await interaction.response.edit_message(
                embed=roster_embed(self.ctx, self.team, self.splice_dict, self.url, choice), view=self)
        elif self.choice == "team contracts":
            await interaction.response.edit_message(
                embed=contracts_embed(self.ctx, self.team, self.splice_dict, self.url, choice), view=self)

    @discord.ui.button(label="Offense", style=discord.ButtonStyle.blurple)
    async def offense(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.edit_response_message(interaction, "offense")

    @discord.ui.button(label="Defense", style=discord.ButtonStyle.blurple)
    async def defense(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.edit_response_message(interaction, "defense")

    @discord.ui.button(label="Special Teams", style=discord.ButtonStyle.blurple)
    async def specialteams(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.edit_response_message(interaction, "special teams")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(self.message.content, view=self)

class Toggle(discord.ui.View):
    def __init__(self, ctx, value, max_value, choice, year=None, players=None, format_dict=None, column_headers=None, url=None, face=None, soup=None,
                 name=None, season=None, parsed_table=None, min_value=0, table=None, team=None, rows=None, text=None, leader_index=None, filter=None):
        super().__init__(timeout=30)

        self.value = value
        self.max_value = max_value
        self.ctx = ctx
        self.message = None
        self.choice = choice
        self.year = year
        self.players = players
        self.format_dict = format_dict
        self.column_headers = column_headers
        self.url = url
        self.face = face
        self.soup = soup
        self.name = name
        self.season = season
        self.parsed_table = parsed_table
        self.min_value = min_value
        self.team = team
        self.table = table
        self.rows = rows
        self.text = text
        self.leader_index = leader_index
        self.filter = filter

        if value == min_value: self.children[0].disabled = True
        if value == self.max_value: self.children[1].disabled = True

    async def edit_response_message(self, interaction):
        if self.choice == "draft": embed = draft_embed(self.ctx, self.year, self.value, self.players)
        elif self.choice == "gamelog": embed = gamelog_embed(self.ctx, self.soup, self.format_dict, self.column_headers, self.url, self.face, self.value)
        elif self.choice == "stats": embed = await stats_embed(self.ctx, self.soup, self.name, self.season, self.url, self.column_headers, self.value, self.parsed_table)
        elif self.choice == "team draft": embed = team_draft_embed(self.ctx, self.team, self.value, self.table, self.url)
        elif self.choice == "undefeated": embed = undefeated_embed(self.ctx, self.value, self.table)
        elif self.choice == "awards": embed = award_embed(self.ctx, self.value)
        elif self.choice == "hof": embed = await hof_embed(self.ctx, self.value)
        elif self.choice == "superbowl": embed = superbowl_embed(self.ctx, self.value, self.table)[0]
        elif self.choice == "leaders": embed = leaders_embed(self.ctx, self.rows, self.text, self.url, self.leader_index, self.value)
        elif self.choice == "alltimeleaders": embed = alltimeleaders_embed(self.ctx, self.text, self.table, self.url, self.value, self.filter)
        elif self.choice == "salary leaders": embed = salaryleaders_embed(self.ctx, self.text, self.rows, self.url, self.value)
        else: return
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.blurple)
    async def previous(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value -= 1
        if self.value == self.min_value: button.disabled = True
        if self.children[1].disabled: self.children[1].disabled = False

        await self.edit_response_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value += 1
        if self.value == self.max_value: button.disabled = True
        if self.children[0].disabled: self.children[0].disabled = False

        await self.edit_response_message(interaction)

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't interact with this.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.message.edit(self.message.content, view=self)
