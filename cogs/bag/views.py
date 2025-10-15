from typing import List, Dict, Optional
from sdk.items.constants import ITEM_EMOJIS, CATEGORY_NAMES
import discord

class BagItemsLayout(discord.ui.LayoutView):
    def __init__(self, items: List[Dict], current_page: int = 0, per_page: int = 20) -> None:
        super().__init__()
        self.items = sorted(items, key=lambda x: x["category"])
        self.per_page = per_page
        self.current_page = current_page
        self.total_pages = max(1, (len(items) - 1) // per_page + 1) if items else 1
        
        self._prev_button = self._create_navigation_button("◀️", "prev_page", self.previous_page)
        self._next_button = self._create_navigation_button("▶️", "next_page", self.next_page)
        
        self.build_page()

    def _create_navigation_button(self, emoji: str, custom_id: str, callback) -> discord.ui.Button:
        button = discord.ui.Button(emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=custom_id)
        button.callback = callback
        return button

    def _update_buttons_state(self) -> None:
        self._prev_button.disabled = self.current_page == 0
        self._next_button.disabled = self.current_page >= self.total_pages - 1

    def _get_page_slice(self) -> tuple[List[Dict], int, int]:
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.items))
        return self.items[start_idx:end_idx], start_idx, end_idx

    def build_page(self) -> None:
        self.clear_items()
        page_items, start_idx, end_idx = self._get_page_slice()

        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay("### Sua Mochila"))
        container.add_item(discord.ui.Separator())
        
        self._add_categorized_items(container, page_items)
        
        container.add_item(discord.ui.TextDisplay(f"-# Mostrando {start_idx + 1}–{end_idx} de {len(self.items)}"))
        self.add_item(container)
        
        self._update_buttons_state()
        action_row = discord.ui.ActionRow()
        action_row.add_item(self._prev_button)
        action_row.add_item(self._next_button)
        self.add_item(action_row)

    def _add_categorized_items(self, container: discord.ui.Container, items: List[Dict]) -> None:
        if not items:
            return

        current_category: Optional[str] = None
        current_section: Optional[discord.ui.Section] = None

        for item in items:
            if item["category"] != current_category:
                if current_section is not None:
                    container.add_item(current_section)
                    container.add_item(discord.ui.Separator())
                
                current_category = item["category"]
                current_section = self._create_category_section(current_category)

            emoji = ITEM_EMOJIS.get(item['id'], '')
            current_section.add_item(f"`{item['id']}`　{emoji} {item['name']}{item['quantity']:>4}x")
        
        if current_section is not None:
            container.add_item(current_section)
            container.add_item(discord.ui.Separator())

    def _create_category_section(self, category: str) -> discord.ui.Section:
        section = discord.ui.Section(accessory=discord.ui.Thumbnail(f"attachment://{category}.png"))
        category_name = CATEGORY_NAMES.get(category, category)
        section.add_item(discord.ui.TextDisplay(f"-# **{category_name}**"))
        return section

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
