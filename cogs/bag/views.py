from typing import List, Dict, Final, Tuple
from sdk.items.constants import ITEM_EMOJIS, CATEGORY_NAMES
from sdk.toolkit import Toolkit
import discord

class BagItemsLayout(discord.ui.LayoutView):
    __slots__ = ('tk', 'items', 'per_page', 'current_page', 'total_pages',
                 '_formatted_items', '_category_groups', '_prev_btn', '_next_btn',
                 '_action_row', '_header', '_separator', '_empty_msg', '_max_page',
                 '_total_len', '_pagination_fmt')
    
    MAX_ITEMS_PER_SECTION: Final[int] = 10
    DEFAULT_PER_PAGE: Final[int] = 20
    
    def __init__(self, items: List[Dict], tk: Toolkit, current_page: int = 0, per_page: int = DEFAULT_PER_PAGE) -> None:
        super().__init__()
        self.tk = tk
        self.items = items
        self.per_page = per_page
        self.current_page = current_page
        self._total_len = len(items)
        self.total_pages = max(1, (self._total_len - 1) // per_page + 1) if self._total_len else 1
        self._max_page = self.total_pages - 1
        
        self._header = discord.ui.TextDisplay("### Sua Mochila")
        self._separator = discord.ui.Separator()
        self._empty_msg = discord.ui.TextDisplay("Sua mochila está vazia.")
        self._pagination_fmt = "-# Mostrando {}–{} de {}"
        
        self._formatted_items = self._precompute_all()
        self._category_groups = self._build_category_groups()
        
        self._prev_btn = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary, custom_id="prev_page")
        self._prev_btn.callback = self._prev
        self._next_btn = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="next_page")
        self._next_btn.callback = self._next
        
        row = self._action_row = discord.ui.ActionRow()
        row.add_item(self._prev_btn)
        row.add_item(self._next_btn)
        
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

    def _build(self) -> None:
        self.clear_items()
        
        idx = self.current_page * self.per_page
        end = min(idx + self.per_page, self._total_len)
        
        c = discord.ui.Container()
        c.add_item(self._header)
        c.add_item(self._separator)
        
        if self._formatted_items:
            page_items_set = set(self._formatted_items[idx:end])
            
            Section = discord.ui.Section
            Thumbnail = discord.ui.Thumbnail
            TextDisplay = discord.ui.TextDisplay
            separator = self._separator
            category_names = CATEGORY_NAMES
            
            for category, thumbnail, items_list in self._category_groups:
                page_items = tuple(item for _, _, item in self._formatted_items[idx:end] if self._formatted_items[self._formatted_items.index((category, thumbnail, item))][0] == category)
                
                if page_items:
                    sec = Section(accessory=Thumbnail(thumbnail))
                    sec.add_item(TextDisplay(f"**{category_names.get(category, category.title())}**"))
                    sec.add_item(TextDisplay(chr(10).join(page_items)))
                    c.add_item(sec)
                    c.add_item(separator)
        else:
            c.add_item(self._empty_msg)
            c.add_item(self._separator)
        
        pagination = self._pagination_fmt.format(idx + 1, end, self._total_len) if self._total_len else "-# Nenhum item"
        c.add_item(discord.ui.TextDisplay(pagination))
        
        self.add_item(c)
        
        self._prev_btn.disabled = not self.current_page
        self._next_btn.disabled = self.current_page >= self._max_page
        
        self.add_item(self._action_row)

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
