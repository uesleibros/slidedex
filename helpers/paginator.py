import discord
from typing import List, Callable, TypeVar, Generic, Awaitable, Optional

T = TypeVar('T')

class PaginatorView(discord.ui.View):
	def __init__(self, embeds: List[discord.Embed], author: discord.User):
		super().__init__(timeout=180)
		self.embeds = embeds
		self.author = author
		self.current = 0
		self._update_buttons()
	
	def _update_buttons(self) -> None:
		self.previous.disabled = self.current == 0
		self.next.disabled = self.current == len(self.embeds) - 1
	
	async def _check_author(self, interaction: discord.Interaction) -> bool:
		if interaction.user.id != self.author.id:
			await interaction.response.send_message(
				"Você não pode usar isso!", 
				ephemeral=True
			)
			return False
		return True
	
	@discord.ui.button(emoji="◀️", style=discord.ButtonStyle.gray)
	async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if not await self._check_author(interaction):
			return
		
		self.current -= 1
		self._update_buttons()
		await interaction.response.edit_message(
			embed=self.embeds[self.current], 
			view=self
		)
	
	@discord.ui.button(emoji="▶️", style=discord.ButtonStyle.gray)
	async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if not await self._check_author(interaction):
			return
		
		self.current += 1
		self._update_buttons()
		await interaction.response.edit_message(
			embed=self.embeds[self.current], 
			view=self
		)

class DynamicPaginatorView(discord.ui.View, Generic[T]):    
    def __init__(
        self,
        items: List[T],
        user_id: int,
        embed_generator: Callable[[List[T], int, int, int, int], Awaitable[discord.Embed]],
        page_size: int = 20,
        current_page: int = 0,
        timeout: int = 180
    ):
        super().__init__(timeout=timeout)
        self.items = items
        self.user_id = user_id
        self.embed_generator = embed_generator
        self.page_size = page_size
        self.current_page = max(0, min(current_page, self.total_pages - 1)) if items else 0
        self._update_buttons()
    
    @property
    def total_pages(self) -> int:
        return max(1, (len(self.items) + self.page_size - 1) // self.page_size)
    
    def _get_page_items(self) -> List[T]:
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.items[start:end]
    
    async def get_embed(self) -> discord.Embed:
        start = self.current_page * self.page_size
        end = min(start + self.page_size, len(self.items))
        page_items = self._get_page_items()
        
        return await self.embed_generator(
            page_items,
            start,
            end,
            len(self.items),
            self.current_page
        )
    
    def _update_buttons(self) -> None:
        self.previous.disabled = self.current_page == 0
        self.next.disabled = self.current_page >= self.total_pages - 1
        self.first.disabled = self.current_page == 0
        self.last.disabled = self.current_page >= self.total_pages - 1
    
    async def _check_author(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Você não pode usar isso!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.gray)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_author(interaction):
            return
        
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_author(interaction):
            return
        
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_author(interaction):
            return
        
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)
    
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.gray)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._check_author(interaction):
            return
        
        self.current_page = self.total_pages - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=await self.get_embed(), view=self)
    
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True