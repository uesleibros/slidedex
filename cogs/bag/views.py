from typing import List, Dict, Final
from sdk.items.constants import ITEM_EMOJIS, CATEGORY_NAMES
import discord

class BagItemsLayout(discord.ui.LayoutView):
    MAX_ITEMS_PER_SECTION: Final[int] = 10
    DEFAULT_PER_PAGE: Final[int] = 20
    
    def __init__(self, items: List[Dict], current_page: int = 0, per_page: int = DEFAULT_PER_PAGE) -> None:
        super().__init__()
        self.items = sorted(items, key=lambda x: (x["category"], x["name"]))
        self.per_page = per_page
        self.current_page = current_page
        self.total_pages = max(1, (len(items) - 1) // per_page + 1) if items else 1
        
        self._prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
        self._prev_button.callback = self.previous_page
        
        self._next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="next_page")
        self._next_button.callback = self.next_page
        
        self.build_page()

    def build_page(self) -> None:
        self.clear_items()
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.items))
        page_items = self.items[start_idx:end_idx]

        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay("### Sua Mochila"))
        container.add_item(discord.ui.Separator())
        
        if page_items:
            self._add_categorized_items(container, page_items)
        else:
            container.add_item(discord.ui.TextDisplay("*Sua mochila está vazia.*"))
        
        pagination_text = f"-# Mostrando {start_idx + 1}–{end_idx} de {len(self.items)}" if self.items else "-# Nenhum item"
        container.add_item(discord.ui.TextDisplay(pagination_text))
        self.add_item(container)
        
        self._prev_button.disabled = self.current_page == 0
        self._next_button.disabled = self.current_page >= self.total_pages - 1
        
        action_row = discord.ui.ActionRow()
        action_row.add_item(self._prev_button)
        action_row.add_item(self._next_button)
        self.add_item(action_row)

    def _add_categorized_items(self, container: discord.ui.Container, items: List[Dict]) -> None:
        current_category = None
        current_section = None
        items_batch = []

        for item in items:
            category = item["category"]
            
            if category != current_category:
                if current_section:
                    current_section.add_item(discord.ui.TextDisplay(self._format_items_text(items_batch)))
                    container.add_item(current_section)
                    container.add_item(discord.ui.Separator())
                
                current_category = category
                category_name = CATEGORY_NAMES.get(category, category.title())
                current_section = discord.ui.Section(accessory=discord.ui.Thumbnail(f"attachment://{category}.png"))
                current_section.add_item(discord.ui.TextDisplay(f"**{category_name}**"))
                items_batch = []
            
            items_batch.append(item)
        
        if current_section:
            current_section.add_item(discord.ui.TextDisplay(self._format_items_text(items_batch)))
            container.add_item(current_section)
            container.add_item(discord.ui.Separator())

    def _format_items_text(self, items: List[Dict]) -> str:
        return "\n".join(
            f"`{item['id']}`　{ITEM_EMOJIS.get(item['id'], '❔')} **{item['name']}**　×{item['quantity']}"
            for item in items
        )

    async def previous_page(self, interaction: discord.Interaction) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.build_page()
            await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction) -> None:
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.build_page()
            await interaction.response.edit_message(view=self)
