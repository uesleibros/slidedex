import discord
from typing import Optional, List, Dict, Callable, Awaitable
from utils.formatting import format_pokemon_display
from .config import UIConfig
from .messages import Messages, ButtonLabels

class BaseChoiceView(discord.ui.View):
	def __init__(self, owner_id: str, manager, timeout: float = None):
		timeout = timeout or UIConfig().interaction_timeout
		super().__init__(timeout=timeout)
		self.owner_id = owner_id
		self.manager = manager
		self.answered = False
		self.message: Optional[discord.Message] = None
	
	async def _validate_interaction(self, interaction: discord.Interaction) -> bool:
		if str(interaction.user.id) != self.owner_id:
			await interaction.response.send_message(Messages.not_your_choice(), ephemeral=True)
			return False
		
		if self.answered:
			await interaction.response.send_message(Messages.already_answered(), ephemeral=True)
			return False
		
		return True
	
	def _cleanup(self):
		self.answered = True
		self.manager._release_lock(self.owner_id)
		self.stop()

class MoveChoiceView(BaseChoiceView):
	def __init__(
		self,
		owner_id: str,
		pokemon_id: int,
		new_move_id: str,
		new_move_name: str,
		pp_max: int,
		current_moves: List[Dict],
		pokemon: dict,
		manager
	):
		super().__init__(owner_id, manager)
		self.pokemon_id = pokemon_id
		self.new_move_id = new_move_id
		self.new_move_name = new_move_name
		self.pp_max = pp_max
		self.current_moves = current_moves
		self.pokemon = pokemon
		
		self._add_buttons()
	
	def _add_buttons(self):
		for idx, move in enumerate(self.current_moves):
			move_id = move["id"]
			move_name = move_id.replace("-", " ").title()
			
			button = discord.ui.Button(
				label=ButtonLabels.forget_move(move_name),
				style=discord.ButtonStyle.primary,
				custom_id=f"forget_{idx}"
			)
			button.callback = self._create_forget_callback(move_id)
			self.add_item(button)
		
		cancel_button = discord.ui.Button(
			label=ButtonLabels.cancel_move(),
			style=discord.ButtonStyle.secondary,
			custom_id="cancel"
		)
		cancel_button.callback = self._cancel_callback
		self.add_item(cancel_button)
	
	def _create_forget_callback(self, move_to_forget: str) -> Callable[[discord.Interaction], Awaitable[None]]:
		async def callback(interaction: discord.Interaction):
			if not await self._validate_interaction(interaction):
				return
			
			self.manager.tk.learn_move(
				self.owner_id,
				self.pokemon_id,
				self.new_move_id,
				self.pp_max,
				replace_move_id=move_to_forget
			)
			
			move_forgotten_name = move_to_forget.replace("-", " ").title()
			message = Messages.move_learned(
				self.owner_id,
				format_pokemon_display(self.pokemon, bold_name=True),
				move_forgotten_name,
				self.new_move_name
			)
			
			await interaction.response.edit_message(content=message, view=None)
			self._cleanup()
		
		return callback
	
	async def _cancel_callback(self, interaction: discord.Interaction):
		if not await self._validate_interaction(interaction):
			return
		
		message = Messages.move_not_learned(
			self.owner_id,
			format_pokemon_display(self.pokemon, bold_name=True),
			self.new_move_name
		)
		
		await interaction.response.edit_message(content=message, view=None)
		self._cleanup()
	
	async def on_timeout(self):
		if not self.answered and self.message:
			message = Messages.move_timeout(
				self.owner_id,
				format_pokemon_display(self.pokemon, bold_name=True),
				self.new_move_name
			)
			await self.message.edit(content=message, view=None)
			self.manager._release_lock(self.owner_id)