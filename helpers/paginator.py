import discord
from typing import List

class PaginatorView(discord.ui.View):
	def __init__(self, embeds: List[discord.Embed], author: discord.User):
		super().__init__(timeout=180)
		self.embeds = embeds
		self.author = author
		self.current = 0
		self._update_buttons()
	
	def _update_buttons(self) -> None:
		self.previous.disabled = self.current == 0
		self.next.disabled = self.current == len(self.embeds) - 1
	
	async def _check_author(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id != self.author.id:
			await interaction.response.send_message(
				"Você não pode usar isso!", 
				ephemeral=True
			)
			return False
		return True
	
	@discord.ui.button(emoji="◀️", style=discord.ButtonStyle.gray)
	async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if not await self._check_author(interaction):
			return
		
		self.current -= 1
		self._update_buttons()
		await interaction.response.edit_message(
			embed=self.embeds[self.current], 
			view=self
		)
	
	@discord.ui.button(emoji="▶️", style=discord.ButtonStyle.gray)
	async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if not await self._check_author(interaction):
			return
		
		self.current += 1
		self._update_buttons()
		await interaction.response.edit_message(
			embed=self.embeds[self.current], 
			view=self
		)