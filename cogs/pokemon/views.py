import discord
from .embeds import generate_info_embed

class InfoView(discord.ui.View):
	def __init__(self, cog, author: discord.Member, user: discord.Member, all_pokemon_ids: list[int], current_index: int):
		super().__init__(timeout=180)
		self.cog = cog
		self.user = user
		self.author = author
		self.all_pokemon_ids = all_pokemon_ids
		self.current_index = current_index
		self.update_buttons()

	def update_buttons(self):
		self.prev_pokemon.disabled = self.current_index == 0
		self.next_pokemon.disabled = self.current_index == len(self.all_pokemon_ids) - 1

	async def _update_info(self, interaction: discord.Interaction):
		pokemon_id = self.all_pokemon_ids[self.current_index]
		self.update_buttons()
		
		result = await generate_info_embed(str(self.user.id), pokemon_id)

		if result:
			embed, files = result
			if str(self.author.id) != self.user.id:
				embed.title += f"\nde {self.user.display_name}"
			await interaction.response.edit_message(embed=embed, attachments=files, view=self)
		else:
			await interaction.response.edit_message(content="Erro ao carregar este Pokemon.", embed=None, attachments=[], view=self)

	@discord.ui.button(label="Anterior", style=discord.ButtonStyle.secondary)
	async def prev_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_index > 0:
			self.current_index -= 1
			await self._update_info(interaction)

	@discord.ui.button(label="Proximo", style=discord.ButtonStyle.secondary)
	async def next_pokemon(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_index < len(self.all_pokemon_ids) - 1:
			self.current_index += 1
			await self._update_info(interaction)

class ConfirmationView(discord.ui.View):
	def __init__(self, user_id: int, timeout: int = 60):
		super().__init__(timeout=timeout)
		self.user_id = user_id
		self.value = None

	@discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green)
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return await interaction.response.send_message("Esta confirmação não é para você!", ephemeral=True)
		self.value = True
		self.stop()
		await interaction.response.defer()

	@discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red)
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		if interaction.user.id != self.user_id:
			return await interaction.response.send_message("Esta confirmação não é para você!", ephemeral=True)
		self.value = False
		self.stop()
		await interaction.response.defer()

	async def on_timeout(self):
		self.value = False
		for item in self.children:
			item.disabled = True