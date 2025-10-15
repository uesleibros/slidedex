from typing import List, Dict, Optional
from sdk.items.constants import ITEM_EMOJIS, CATEGORY_NAMES
import discord

class BagItemsLayout(discord.ui.LayoutView):
	def __init__(self, items: List, current_page: int = 0, per_page: int = 20) -> None:
		super().__init__()
		self.items = items
		self.per_page = per_page
		self.current_page = current_page
		self.total_pages = (len(items) - 1) // per_page + 1
		self.build_page()

	def build_page(self) -> None:
		self.clear_items()
		start_idx = self.current_page * self.per_page
		end_idx = min(start_idx + self.per_page, len(self.items))
		page_items = self.items[start_idx:end_idx]

		container: discord.ui.Container = discord.ui.Container()
		container.add_item(discord.ui.TextDisplay("### Sua Mochila"))
		container.add_item(discord.ui.Separator())
		
		self.create_categorized_items(container, page_items)
		container.add_item(discord.ui.TextDisplay(
			f"-# Mostrando {start_idx+1}–{end_idx} de {self.total_pages}"
		))
		self.add_item(container)
		
		action_row: discord.ui.ActionRow = discord.ui.ActionRow()
		
		prev_button: discord.ui.Button = discord.ui.Button(
			emoji="◀️",
			style=discord.ButtonStyle.secondary,
			disabled=self.current_page == 0,
			custom_id="prev_page"
		)
		prev_button.callback = self.previous_page
		action_row.add_item(prev_button)
		
		next_button: discord.ui.Button = discord.ui.Button(
			emoji="▶️",
			style=discord.ButtonStyle.secondary,
			disabled=self.current_page >= self.total_pages - 1,
			custom_id="next_page"
		)
		next_button.callback = self.next_page
		action_row.add_item(next_button)
		
		self.add_item(action_row)

	def create_categorized_items(self, container: discord.ui.Container, items) -> None:
		current_category: Optional[str] = None
		current_section: Optional[discord.ui.Section] = None

		for item in items:
			if item["category"] != current_category:
				if not current_section is None:
					container.add_item(current_section)
					container.add_item(discord.ui.Separator())
				current_category = item["category"]
				category_name = CATEGORY_NAMES.get(current_category, current_category)
				current_section = discord.ui.Section(
					accessory=discord.ui.Thumbnail(
						f"attachment://{current_category}.png"
					)
				)
				current_section.add_item(discord.ui.TextDisplay(f"-# **{CATEGORY_NAMES.get(item['category'])}**"))

			current_section.add_item(f"`{item['id']}`　{ITEM_EMOJIS.get(item['id'])} {item['name']}{item['quantity']:>4}x")
		
		if not current_section is None:
			container.add_item(current_section)
			container.add_item(discord.ui.Separator())

	async def previous_page(self, interaction: discord.Interaction):		
		self.current_page -= 1
		self.build_page()
		await interaction.response.edit_message(view=self)

	async def next_page(self, interaction: discord.Interaction):		
		self.current_page += 1
		self.build_page()
		await interaction.response.edit_message(view=self)

