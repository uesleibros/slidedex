from typing import List, Dict, Optional
from sdk.items.constants import ITEM_EMOJIS, CATEGORY_NAMES
import discord

class BagItemsLayout(discord.ui.LayoutView):
	def __init__(self, items: List) -> None:
		super().__init__()
		self.items = items
		self.categorized_items: Dict = {}
		self.build_page()

	def build_page(self) -> None:
		self.clear_items()

		container: discord.ui.Container = discord.ui.Container()
		container.add_item(discord.ui.TextDisplay("### Sua Mochila"))
		container.add_item(discord.ui.Separator())
		
		self.create_categorized_items(container)
		self.add_item(container)

	def create_categorized_items(self, container: discord.ui.Container) -> None:
		current_category: Optional[str] = None
		current_section: Optional[discord.ui.Section] = None

		for item in self.items:
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

			current_section.add_item(f"`{item['id']}`　{ITEM_EMOJIS.get(item['id'])} {item['name']}{item['quantity']:>4}x")
		
		if not current_section is None:
			container.add_item(current_section)
			container.add_item(discord.ui.Separator())
