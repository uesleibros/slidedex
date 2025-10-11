import discord
from typing import Optional, Callable, Dict, Tuple
from io import BytesIO
from utils.formatting import format_pokemon_display
from utils.canvas import compose_evolution_async
from .config import EvolutionConfig, Emojis
from .messages import EvolutionMessages, ButtonLabels
from pokemon_sdk.config import tk

class BaseEvolutionView(discord.ui.View):
	def __init__(self, owner_id: str, processor, timeout: float = None):
		config = EvolutionConfig()
		timeout = timeout or config.interaction_timeout
		super().__init__(timeout=timeout)
		self.owner_id = owner_id
		self.processor = processor
		self.answered = False
		self.message: Optional[discord.Message] = None
	
	async def _validate_interaction(self, interaction: discord.Interaction) -> bool:
		if str(interaction.user.id) != self.owner_id:
			await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
			return False
		
		if self.answered:
			await interaction.response.send_message("Já foi respondido!", ephemeral=True)
			return False
		
		return True
	
	def _cleanup(self):
		self.answered = True
		self.processor.release_lock(self.owner_id)
		self.stop()

class EvolutionChoiceView(BaseEvolutionView):
	def __init__(
		self,
		owner_id: str,
		pokemon_id: int,
		current_pokemon: dict,
		evolution_species_id: int,
		evolution_name: str,
		processor,
		on_evolve: Optional[Callable] = None
	):
		super().__init__(owner_id, processor)
		self.pokemon_id = pokemon_id
		self.current_pokemon = current_pokemon
		self.evolution_species_id = evolution_species_id
		self.evolution_name = evolution_name
		self.on_evolve = on_evolve
		self.ui_handler = EvolutionUIHandler(processor)
		
		self._add_buttons()
	
	def _add_buttons(self):
		evolve_button = discord.ui.Button(
			label=ButtonLabels.evolve(self.evolution_name),
			style=discord.ButtonStyle.success,
			custom_id="evolve"
		)
		evolve_button.callback = self._evolve_callback
		self.add_item(evolve_button)
		
		cancel_button = discord.ui.Button(
			label=ButtonLabels.cancel(),
			style=discord.ButtonStyle.secondary,
			custom_id="cancel"
		)
		cancel_button.callback = self._cancel_callback
		self.add_item(cancel_button)
		
		block_button = discord.ui.Button(
			label=ButtonLabels.block(),
			style=discord.ButtonStyle.danger,
			custom_id="block"
		)
		block_button.callback = self._block_callback
		self.add_item(block_button)
	
	async def _evolve_callback(self, interaction: discord.Interaction):
		if not await self._validate_interaction(interaction):
			return
		
		self.answered = True
		await interaction.response.edit_message(
			content=f"<@{self.owner_id}> {EvolutionMessages.evolving()}",
			view=None
		)
		
		try:
			result = await self.ui_handler.execute_evolution_with_animation(
				interaction=interaction,
				owner_id=self.owner_id,
				pokemon_id=self.pokemon_id,
				current_pokemon=self.current_pokemon,
				evolution_species_id=self.evolution_species_id
			)
			
			if self.on_evolve:
				await self.on_evolve(result)
				
		except Exception as e:
			await interaction.edit_original_response(
				content=EvolutionMessages.error(self.owner_id, str(e))
			)
		finally:
			self._cleanup()
	
	async def _cancel_callback(self, interaction: discord.Interaction):
		if not await self._validate_interaction(interaction):
			return
		
		current_name = self.current_pokemon.get("name", "").title()
		await interaction.response.edit_message(
			content=EvolutionMessages.cancelled(self.owner_id, current_name),
			view=None
		)
		self._cleanup()
	
	async def _block_callback(self, interaction: discord.Interaction):
		if not await self._validate_interaction(interaction):
			return
		
		tk.block_evolution(self.owner_id, self.pokemon_id, True)
		current_name = self.current_pokemon.get("name", "").title()
		
		await interaction.response.edit_message(
			content=EvolutionMessages.blocked(self.owner_id, current_name),
			view=None
		)
		self._cleanup()
	
	async def on_timeout(self):
		if not self.answered and self.message:
			current_name = self.current_pokemon.get("name", "").title()
			await self.message.edit(
				content=EvolutionMessages.timeout(self.owner_id, current_name),
				view=None
			)
			self.processor.release_lock(self.owner_id)

class EvolutionUIHandler:
	def __init__(self, processor):
		self.processor = processor
	
	async def generate_evolution_animation(
		self,
		current_pokemon: Dict,
		new_species_id: int
	) -> BytesIO:	
		old_sprite_bytes = self.processor.pm.service.get_pokemon_sprite(current_pokemon)[0]
		current_pokemon["species_id"] = new_species_id
		new_sprite_bytes = self.processor.pm.service.get_pokemon_sprite(current_pokemon)[0]
		
		return await compose_evolution_async(old_sprite_bytes, new_sprite_bytes)
	
	async def execute_evolution_with_animation(
		self,
		interaction: discord.Interaction,
		owner_id: str,
		pokemon_id: int,
		current_pokemon: Dict,
		evolution_species_id: int
	) -> Dict:
		gif_buffer = await self.generate_evolution_animation(
			current_pokemon,
			evolution_species_id
		)
		
		result = self.processor.evolve_pokemon(
			owner_id,
			pokemon_id,
			evolution_species_id
		)
		
		message = EvolutionMessages.evolved(
			owner_id,
			format_pokemon_display(current_pokemon, bold_name=True, show_gender=False),
			format_pokemon_display(result, bold_name=True, show_gender=False),
			Emojis.EVOLUTION
		)
		
		await interaction.edit_original_response(
			content=message,
			attachments=[discord.File(gif_buffer, filename="evolution.gif")]
		)
		
		return result
	
	async def send_evolution_message(
		self,
		channel: discord.abc.Messageable,
		owner_id: str,
		pokemon_id: int,
		current_pokemon: Dict,
		evolution_species_id: int
	) -> Tuple[Dict, discord.Message]:
		gif_buffer = await self.generate_evolution_animation(
			current_pokemon,
			evolution_species_id
		)
		
		result = self.processor.evolve_pokemon(
			owner_id,
			pokemon_id,
			evolution_species_id
		)
		
		message_content = EvolutionMessages.evolved(
			owner_id,
			format_pokemon_display(current_pokemon, bold_name=True, show_gender=False),
			format_pokemon_display(result, bold_name=True, show_gender=False),
			Emojis.EVOLUTION
		)
		
		sent_message = await channel.send(
			content=message_content,
			file=discord.File(gif_buffer, filename="evolution.gif")
		)
		
		return result, sent_message
	
	async def show_evolution_choice(
		self,
		message: discord.Message,
		owner_id: str,
		pokemon_id: int,
		pokemon: Dict,
		evolution_data: Dict,
		on_evolve: Optional[Callable] = None
	) -> Optional[discord.Message]:
		view = EvolutionChoiceView(
			owner_id=owner_id,
			pokemon_id=pokemon_id,
			current_pokemon=pokemon,
			evolution_species_id=evolution_data["species_id"],
			evolution_name=evolution_data["name"],
			processor=self.processor,
			on_evolve=on_evolve
		)
		
		extra_info = self.processor.build_extra_info(evolution_data, pokemon)
		content = EvolutionMessages.can_evolve(
			format_pokemon_display(pokemon, bold_name=True),
			evolution_data['name'],
			extra_info
		)
		
		sent_message = await message.channel.send(content=content, view=view)
		view.message = sent_message
		return sent_message
	
	def evolve_silent(
		self,
		owner_id: str,
		pokemon_id: int,
		evolution_species_id: int
	) -> Dict:
		return self.processor.evolve_pokemon(owner_id, pokemon_id, evolution_species_id)