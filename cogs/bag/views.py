from typing import List, Dict, Final, Tuple, Optional
from sdk.items.constants import ITEM_EMOJIS, CATEGORY_NAMES
from sdk.toolkit import Toolkit
import discord

class BagItemsLayout(discord.ui.LayoutView):
    MAX_ITEMS_PER_SECTION: Final[int] = 10
    DEFAULT_PER_PAGE: Final[int] = 20
    
    def __init__(self, items: List[Dict], tk: Toolkit, current_page: int = 0, per_page: int = DEFAULT_PER_PAGE) -> None:
        super().__init__()
        self.tk = tk
        self.items = items
        self.per_page = per_page
        self.current_page = current_page
        
        self._separator = discord.ui.Separator()
        self._empty_msg = discord.ui.TextDisplay("Sua mochila está vazia.")
        self._pagination_fmt = "-# Mostrando {}–{} de {}"
        
        self._formatted_items = self._precompute_all()
        self._category_groups = self._build_category_groups()
        self._available_categories = self._get_available_categories()
        
        self.selected_category: Optional[str] = self._get_default_category()
        
        self._category_select = discord.ui.Select(
            placeholder="Selecione uma categoria...",
            custom_id="category_filter"
        )
        self._category_select.callback = self._on_category_change
        self._populate_category_select()
        
        self._prev_btn = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
        self._prev_btn.callback = self._prev
        self._next_btn = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="next_page")
        self._next_btn.callback = self._next
        
        self._select_row = discord.ui.ActionRow()
        self._select_row.add_item(self._category_select)
        
        self._nav_row = discord.ui.ActionRow()
        self._nav_row.add_item(self._prev_btn)
        self._nav_row.add_item(self._next_btn)
        
        self._build()

    def _precompute_all(self) -> Tuple[Tuple[str, str, str], ...]:
        items = sorted(self.items, key=lambda x: (x["category"], x["name"]))
        
        tms_hms_items = tuple(item['id'] for item in items if item['category'] == 'tms_hms')
        
        machines_map = {}
        if tms_hms_items:
            api = self.tk.api
            for item_id in tms_hms_items:
                machine_data = api.get_machine(item_id)
                if machine_data:
                    machines_map[item_id] = machine_data['move']['name']
        
        emojis = ITEM_EMOJIS
        result = []
        
        for item in items:
            category = item['category']
            item_id = item['id']
            
            formatted = f"`{item_id}`　{emojis.get(item_id, '❔')} **{item['name']}**"
            
            if category == 'tms_hms' and item_id in machines_map:
                formatted += f" ({machines_map[item_id]})"
            
            formatted += f" ×{item['quantity']}"
            
            result.append((category, f"attachment://{category}.png", formatted))
        
        return tuple(result)

    def _build_category_groups(self) -> Tuple[Tuple[str, str, Tuple[str, ...]], ...]:
        if not self._formatted_items:
            return ()
        
        groups = {}
        for category, thumbnail, formatted in self._formatted_items:
            if category not in groups:
                groups[category] = (thumbnail, [])
            groups[category][1].append(formatted)
        
        return tuple(
            (cat, thumb, tuple(items))
            for cat, (thumb, items) in groups.items()
        )

    def _get_available_categories(self) -> Tuple[str, ...]:
        return tuple(cat for cat, _, _ in self._category_groups)

    def _get_default_category(self) -> Optional[str]:
        if not self._available_categories:
            return None
        return 'items' if 'items' in self._available_categories else self._available_categories[0]

    def _get_category_thumbnail(self) -> Optional[str]:
        if not self.selected_category:
            return None
        for category, thumbnail, _ in self._category_groups:
            if category == self.selected_category:
                return thumbnail
        return None

    def _populate_category_select(self) -> None:
        self._category_select.options.clear()
        
        category_names = CATEGORY_NAMES
        for category in self._available_categories:
            self._category_select.add_option(
                label=category_names.get(category, category.title()),
                value=category,
                default=self.selected_category == category
            )

    def _get_filtered_items(self) -> Tuple[Tuple[str, str, str], ...]:
        if self.selected_category is None:
            return self._formatted_items
        return tuple(item for item in self._formatted_items if item[0] == self.selected_category)

    @property
    def _filtered_len(self) -> int:
        return len(self._get_filtered_items())

    @property
    def _total_pages(self) -> int:
        total = self._filtered_len
        return max(1, (total - 1) // self.per_page + 1) if total else 1

    @property
    def _max_page(self) -> int:
        return self._total_pages - 1

    def _build(self) -> None:
        self.clear_items()
        
        filtered_items = self._get_filtered_items()
        total = len(filtered_items)
        
        idx = self.current_page * self.per_page
        end = min(idx + self.per_page, total)
        
        c = discord.ui.Container()
        
        thumbnail = self._get_category_thumbnail()
        if thumbnail:
            header_section = discord.ui.Section(accessory=discord.ui.Thumbnail(thumbnail))
            header_section.add_item(discord.ui.TextDisplay("### Sua Mochila"))
            c.add_item(header_section)
        else:
            c.add_item(discord.ui.TextDisplay("### Sua Mochila"))
        
        c.add_item(self._separator)
        
        if filtered_items:
            TextDisplay = discord.ui.TextDisplay
            separator = self._separator
            category_names = CATEGORY_NAMES
            
            if self.selected_category:
                for category, _, _ in self._category_groups:
                    if category == self.selected_category:
                        page_items = tuple(item for cat, _, item in filtered_items[idx:end])
                        
                        c.add_item(TextDisplay(f"-# **{category_names.get(category, category.title())}**"))
                        c.add_item(TextDisplay(chr(10).join(page_items)))
                        c.add_item(separator)
                        break
            else:
                for category, _, _ in self._category_groups:
                    page_items = tuple(item for cat, _, item in filtered_items[idx:end] if cat == category)
                    
                    if page_items:
                        c.add_item(TextDisplay(f"-# **{category_names.get(category, category.title())}**"))
                        c.add_item(TextDisplay(chr(10).join(page_items)))
                        c.add_item(separator)
        else:
            c.add_item(self._empty_msg)
            c.add_item(self._separator)
        
        pagination = self._pagination_fmt.format(idx + 1, end, total) if total else "-# Nenhum item"
        c.add_item(discord.ui.TextDisplay(pagination))
        
        self.add_item(c)
        
        if self._available_categories:
            self.add_item(self._select_row)
        
        self._prev_btn.disabled = not self.current_page
        self._next_btn.disabled = self.current_page >= self._max_page
        
        self.add_item(self._nav_row)

    async def _on_category_change(self, interaction: discord.Interaction) -> None:
        selected = self._category_select.values[0]
        self.selected_category = selected
        self.current_page = 0
        self._populate_category_select()
        self._build()
        await interaction.response.edit_message(view=self)

    async def _prev(self, interaction: discord.Interaction) -> None:
        if self.current_page:
            self.current_page -= 1
            self._build()
            await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction) -> None:
        if self.current_page < self._max_page:
            self.current_page += 1
            self._build()
            await interaction.response.edit_message(view=self)
