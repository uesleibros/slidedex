import discord
from typing import List, Callable, Optional, Awaitable

class Paginator(discord.ui.View):
	def __init__(
		self,
		items: List,
		user_id: int,
		embed_generator: Callable[[List, int, int, int, int], Awaitable[discord.Embed]],
		page_size: int = 20,
		current_page: int = 0,
		timeout: float = 120
	):
		super().__init__(timeout=timeout)
		self.items = items
		self.page_size = max(page_size, 1)
		self.user_id = user_id
		self.total = len(items)
		self.embed_generator = embed_generator

		max_page = max((self.total - 1) // self.page_size, 0)
		self.current_page = min(max(current_page - 1, 0), max_page)

		self.update_buttons()

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		return interaction.user.id == self.user_id

	def update_buttons(self):
		self.first_page.disabled = self.current_page == 0
		self.prev_page.disabled = self.current_page == 0
		max_page = (self.total - 1) // self.page_size
		self.next_page.disabled = self.current_page == max_page
		self.last_page.disabled = self.current_page == max_page

	async def get_embed(self) -> discord.Embed:
		start = self.current_page * self.page_size
		end = min(start + self.page_size, self.total)
		page_items = self.items[start:end]
		return await self.embed_generator(page_items, start, end, self.total, self.current_page)

	@discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
	async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = 0
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
	async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.current_page > 0:
			self.current_page -= 1
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
	async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		max_page = (self.total - 1) // self.page_size
		if self.current_page < max_page:
			self.current_page += 1
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)

	@discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
	async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		self.current_page = (self.total - 1) // self.page_size
		self.update_buttons()
		embed = await self.get_embed()
		await interaction.response.edit_message(embed=embed, view=self)