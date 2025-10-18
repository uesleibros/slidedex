from typing import List, Dict, Final, Tuple
from sdk.items.constants import ITEM_EMOJIS, CATEGORY_NAMES
from sdk.toolkit import Toolkit
import discord

class BagItemsLayout(discord.ui.LayoutView):
    MAX_ITEMS_PER_SECTION: Final[int] = 10
    DEFAULT_PER_PAGE: Final[int] = 20
    
    def __init__(self, items: List[Dict], tk: Toolkit, current_page: int = 0, per_page: int = DEFAULT_PER_PAGE) -> None:
        super().__init__()
        self.tk = tk
        self.items = sorted(items, key=lambda x: (x["category"], x["name"]))
        self.per_page = per_page
        self.current_page = current_page
        self.total_pages = max(1, (len(items) - 1) // per_page + 1) if items else 1
        
        self._page_cache: Dict[int, List] = {}
        self._formatted_items = self._precompute_all()
        
        self._prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
        self._prev_button.callback = self.previous_page
        
        self._next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="next_page")
        self._next_button.callback = self.next_page
        
        self.build_page()

    def _precompute_all(self) -> List[Tuple[str, str]]:
        return [
            (
                item['category'],
                f"`{item['id']}`　{ITEM_EMOJIS.get(item['id'], '❔')} **{item['name']}**　×{item['quantity']}"
            )
            for item in self.items
        ]

    def _build_page_components(self, start_idx: int, end_idx: int) -> List:
        if self.current_page in self._page_cache:
            return self._page_cache[self.current_page]
        
        components = []
        page_items = self._formatted_items[start_idx:end_idx]
        
        container = discord.ui.Container()
        container.add_item(discord.ui.TextDisplay("### Sua Mochila"))
        container.add_item(discord.ui.Separator())
        
        if page_items:
            category_groups = {}
            for category, formatted in page_items:
                category_groups.setdefault(category, []).append(formatted)
            
            for category, items_list in category_groups.items():
                section = discord.ui.Section(accessory=discord.ui.Thumbnail(f"attachment://{category}.png"))
                section.add_item(discord.ui.TextDisplay(f"**{CATEGORY_NAMES.get(category, category.title())}**"))
                section.add_item(discord.ui.TextDisplay("\n".join(items_list)))
                container.add_item(section)
                container.add_item(discord.ui.Separator())
        else:
            container.add_item(discord.ui.TextDisplay("Sua mochila está vazia."))
            container.add_item(discord.ui.Separator())
        
        pagination = f"-# Mostrando {start_idx + 1}–{end_idx} de {len(self.items)}" if self.items else "-# Nenhum item"
        container.add_item(discord.ui.TextDisplay(pagination))
        
        components.append(container)
        self._page_cache[self.current_page] = components
        return components

    def build_page(self) -> None:
        self.clear_items()
        
        start_idx = self.current_page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.items))
        
        for component in self._build_page_components(start_idx, end_idx):
            self.add_item(component)
        
        self._prev_button.disabled = self.current_page == 0
        self._next_button.disabled = self.current_page >= self.total_pages - 1
        
        action_row = discord.ui.ActionRow()
        action_row.add_item(self._prev_button)
        action_row.add_item(self._next_button)
        self.add_item(action_row)

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



