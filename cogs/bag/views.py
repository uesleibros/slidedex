from typing import List, Dict, Optional, Final
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
        
        self._prev_button = self._create_navigation_button("◀️", "prev_page", self.previous_page)
        self._next_button = self._create_navigation_button("▶️", "next_page", self.next_page)
        
        self.build_page()

    def _create_navigation_button(self, emoji: str, custom_id: str, callback) -> discord.ui.Button:
        button = discord.ui.Button(
            emoji=emoji, 
            style=discord.ButtonStyle.secondary, 
            custom_id=custom_id
        )
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
        
        if page_items:
            self._add_categorized_items(container, page_items)
        else:
            container.add_item(discord.ui.TextDisplay("*Sua mochila está vazia.*"))
        
        pagination_text = f"-# Mostrando {start_idx + 1}–{end_idx} de {len(self.items)}" if self.items else "-# Nenhum item"
        container.add_item(discord.ui.TextDisplay(pagination_text))
        self.add_item(container)
        
        self._update_buttons_state()
        action_row = discord.ui.ActionRow()
        action_row.add_item(self._prev_button)
        action_row.add_item(self._next_button)
        self.add_item(action_row)

    def _add_categorized_items(self, container: discord.ui.Container, items: List[Dict]) -> None:
        categorized_items = self._group_items_by_category(items)

        for category, category_items in categorized_items.items():
            section = self._create_category_section(category)
            items_text = self._format_items_text(category_items)
            section.add_item(discord.ui.TextDisplay(items_text))
            
            container.add_item(section)
            container.add_item(discord.ui.Separator())

    def _group_items_by_category(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        categorized: Dict[str, List[Dict]] = {}
        for item in items:
            category = item["category"]
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)
        return categorized

    def _format_items_text(self, items: List[Dict]) -> str:
        lines = []
        for item in items:
            emoji = ITEM_EMOJIS.get(item['id'], '❔')
            line = f"`{item['id']}`　{emoji} **{item['name']}**　×{item['quantity']}"
            lines.append(line)
        return "\n".join(lines)

    def _create_category_section(self, category: str) -> discord.ui.Section:
        category_name = CATEGORY_NAMES.get(category, category.title())
        section = discord.ui.Section(
            accessory=discord.ui.Thumbnail(f"attachment://{category}.png")
        )
        section.add_item(discord.ui.TextDisplay(f"**{category_name}**"))
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
