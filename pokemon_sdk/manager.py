import discord
import random
import aiopoke
from typing import List, Optional, Dict
from datetime import datetime
import pytz
from utils.formatting import format_pokemon_display
from .services import PokeAPIService
from .calculations import generate_pokemon_data, calculate_stats, iv_percent
from .constants import NATURES, REGIONS_GENERATION, BERRIES, EVOLUTION_STONES, VERSION_GROUPS
from helpers.growth import GrowthRate

class EvolutionChoiceView(discord.ui.View):
	def __init__(
		self,
		owner_id: str,
		pokemon_id: int,
		current_pokemon: dict,
		evolution_species_id: int,
		evolution_name: str,
		manager
	):
		super().__init__(timeout=60.0)
		self.owner_id = owner_id
		self.pokemon_id = pokemon_id
		self.current_pokemon = current_pokemon
		self.evolution_species_id = evolution_species_id
		self.evolution_name = evolution_name
		self.manager = manager
		self.answered = False
		self.message: Optional[discord.Message] = None
		
		evolve_button = discord.ui.Button(
			label=f"Evoluir para {evolution_name}",
			style=discord.ButtonStyle.success,
			custom_id="evolve"
		)
		evolve_button.callback = self._evolve_callback
		self.add_item(evolve_button)
		
		cancel_button = discord.ui.Button(
			label="Agora Não",
			style=discord.ButtonStyle.secondary,
			custom_id="cancel"
		)
		cancel_button.callback = self._cancel_callback
		self.add_item(cancel_button)
		
		block_button = discord.ui.Button(
			label="Nunca Evoluir",
			style=discord.ButtonStyle.danger,
			custom_id="block"
		)
		block_button.callback = self._block_callback
		self.add_item(block_button)
	
	async def _evolve_callback(self, interaction: discord.Interaction):
		if str(interaction.user.id) != self.owner_id:
			await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
			return
		
		if self.answered:
			await interaction.response.send_message("Já foi respondido!", ephemeral=True)
			return
		
		self.answered = True
		
		await interaction.response.edit_message(
			content=f"<@{self.owner_id}> Evoluindo...",
			view=None
		)
		
		try:
			result = await self.manager.evolve_pokemon(
				self.owner_id,
				self.pokemon_id,
				self.evolution_species_id
			)
			
			await interaction.edit_original_response(
				content=f"<@{self.owner_id}> <:emojigg_Cap:1424197927496060969> {format_pokemon_display(self.current_pokemon, bold_name=True, show_gender=False)} evoluiu para {format_pokemon_display(result, bold_name=True, show_gender=False)}!"
			)
		except Exception as e:
			await interaction.edit_original_response(
				content=f"<@{self.owner_id}> Erro ao evoluir: {e}"
			)
		finally:
			self.manager._release_lock(self.owner_id)
		
		self.stop()
	
	async def _cancel_callback(self, interaction: discord.Interaction):
		if str(interaction.user.id) != self.owner_id:
			await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
			return
		
		if self.answered:
			await interaction.response.send_message("Já foi respondido!", ephemeral=True)
			return
		
		self.answered = True
		
		current_name = self.current_pokemon.get("name", "").title()
		
		await interaction.response.edit_message(
			content=f"<@{self.owner_id}> {current_name} não evoluiu. (Tentará novamente no próximo nível)",
			view=None
		)
		
		self.manager._release_lock(self.owner_id)
		self.stop()
	
	async def _block_callback(self, interaction: discord.Interaction):
		if str(interaction.user.id) != self.owner_id:
			await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
			return
		
		if self.answered:
			await interaction.response.send_message("Já foi respondido!", ephemeral=True)
			return
		
		self.answered = True
		
		self.manager.tk.block_evolution(self.owner_id, self.pokemon_id, True)
		
		current_name = self.current_pokemon.get("name", "").title()
		
		await interaction.response.edit_message(
			content=f"<@{self.owner_id}> {current_name} nunca evoluirá. (Use `/desbloquear` para reverter)",
			view=None
		)
		
		self.manager._release_lock(self.owner_id)
		self.stop()
	
	async def on_timeout(self):
		if not self.answered and self.message:
			for item in self.children:
				item.disabled = True
			
			current_name = self.current_pokemon.get("name", "").title()
			
			await self.message.edit(
				content=f"<@{self.owner_id}> Tempo esgotado! {current_name} não evoluiu. (Tentará novamente no próximo nível)",
				view=None
			)
			
			self.manager._release_lock(self.owner_id)

class MoveChoiceView(discord.ui.View):
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
		super().__init__(timeout=60.0)
		self.owner_id = owner_id
		self.pokemon_id = pokemon_id
		self.new_move_id = new_move_id
		self.new_move_name = new_move_name
		self.pp_max = pp_max
		self.current_moves = current_moves
		self.pokemon = pokemon
		self.manager = manager
		self.answered = False
		self.message: Optional[discord.Message] = None
		
		for idx, move in enumerate(current_moves):
			move_id = move["id"]
			move_name = move_id.replace("-", " ").title()
			
			button = discord.ui.Button(
				label=f"Esquecer {move_name}",
				style=discord.ButtonStyle.primary,
				custom_id=f"forget_{idx}"
			)
			button.callback = self._create_callback(move_id)
			self.add_item(button)
		
		cancel_button = discord.ui.Button(
			label="Cancelar",
			style=discord.ButtonStyle.secondary,
			custom_id="cancel"
		)
		cancel_button.callback = self._cancel_callback
		self.add_item(cancel_button)
	
	def _create_callback(self, move_to_forget: str):
		async def callback(interaction: discord.Interaction):
			if str(interaction.user.id) != self.owner_id:
				await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
				return
			
			if self.answered:
				await interaction.response.send_message("Já foi respondido!", ephemeral=True)
				return
			
			self.answered = True
			
			self.manager.tk.learn_move(
				self.owner_id,
				self.pokemon_id,
				self.new_move_id,
				self.pp_max,
				replace_move_id=move_to_forget
			)
			
			move_forgotten_name = move_to_forget.replace("-", " ").title()
			
			await interaction.response.edit_message(
				content=f"<@{self.owner_id}> {format_pokemon_display(self.pokemon, bold_name=True)} Esqueceu **{move_forgotten_name}** e Aprendeu **{self.new_move_name}**!",
				view=None
			)
			
			self.manager._release_lock(self.owner_id)
			self.stop()
		
		return callback
	
	async def _cancel_callback(self, interaction: discord.Interaction):
		if str(interaction.user.id) != self.owner_id:
			await interaction.response.send_message("Essa escolha não é sua!", ephemeral=True)
			return
		
		if self.answered:
			await interaction.response.send_message("Já foi respondido!", ephemeral=True)
			return
		
		self.answered = True
		
		await interaction.response.edit_message(
			content=f"<@{self.owner_id}> {format_pokemon_display(self.pokemon, bold_name=True)} Não aprendeu **{self.new_move_name}**.",
			view=None
		)
		
		self.manager._release_lock(self.owner_id)
		self.stop()
	
	async def on_timeout(self):
		if not self.answered and self.message:
			for item in self.children:
				item.disabled = True
			
			await self.message.edit(
				content=f"<@{self.owner_id}> Tempo esgotado! {format_pokemon_display(self.pokemon, bold_name=True)} não aprendeu **{self.new_move_name}**.",
				view=None
			)
			
			self.manager._release_lock(self.owner_id)

class PokemonManager:
	def __init__(self, toolkit):
		self.tk = toolkit
		self.service = PokeAPIService()
		self._user_locks = {}
		self.brazil_tz = pytz.timezone('America/Sao_Paulo')

	def _is_locked(self, owner_id: str) -> bool:
		return self._user_locks.get(owner_id, False)
	
	def _acquire_lock(self, owner_id: str) -> bool:
		if self._is_locked(owner_id):
			return False
		self._user_locks[owner_id] = True
		return True
	
	def _release_lock(self, owner_id: str):
		self._user_locks[owner_id] = False

	def _get_current_time_of_day(self) -> str:
		current_time = datetime.now(self.brazil_tz)
		hour = current_time.hour
		
		if 6 <= hour < 18:
			return "day"
		else:
			return "night"

	async def get_item(self, item_id: str) -> Optional[aiopoke.Item]:
		try:
			item = await self.service.client.get_item(item_id)
			return item
		except:
			return None

	async def validate_item(self, item_id: str) -> bool:
		item = await self.get_item(item_id)
		return item is not None

	async def get_item_attributes(self, item_id: str) -> List[str]:
		item = await self.get_item(item_id)
		if not item:
			return []
		return [attr.name for attr in item.attributes]

	async def is_battle_only_item(self, item_id: str) -> bool:
		attributes = await self.get_item_attributes(item_id)
		
		if not attributes:
			return False
		
		has_battle = "usable-in-battle" in attributes
		has_overworld = "usable-overworld" in attributes
		
		return has_battle and not has_overworld

	async def is_consumable(self, item_id: str) -> bool:
		attributes = await self.get_item_attributes(item_id)
		return "consumable" in attributes

	async def is_holdable(self, item_id: str) -> bool:
		attributes = await self.get_item_attributes(item_id)
		return "holdable" in attributes

	async def get_item_category(self, item_id: str) -> str:
		item = await self.get_item(item_id)
		
		if not item:
			return "items"
		
		if item.name in BERRIES or item.name.endswith("-berry"):
			return "berries"
		
		category_name = item.category.name.lower()
		
		category_map = {
			"stat-boosts": "items",
			"medicine": "items",
			"other": "items",
			"vitamins": "items",
			"healing": "items",
			"pp-recovery": "items",
			"revival": "items",
			"status-cures": "items",
			"loot": "items",
			"held-items": "items",
			"choice": "items",
			"effort-drop": "items",
			"bad-held-items": "items",
			"training": "items",
			"plates": "items",
			"species-specific": "items",
			"type-enhancement": "items",
			"event-items": "key_items",
			"gameplay": "key_items",
			"plot-advancement": "key_items",
			"unused": "key_items",
			"standard-balls": "pokeballs",
			"special-balls": "pokeballs",
			"apricorn-balls": "pokeballs",
			"all-machines": "tms_hms",
			"tm": "tms_hms",
			"hm": "tms_hms",
			"berries": "berries"
		}
		
		return category_map.get(category_name, "items")

	async def get_item_name(self, item_id: str, language: str = "en") -> str:
		item = await self.get_item(item_id)
		
		if not item:
			return item_id.replace("-", " ").title()
		
		for name_entry in item.names:
			if name_entry.language.name == language:
				return name_entry.name
		
		return item.name.replace("-", " ").title()

	async def get_item_effect(self, item_id: str, language: str = "en") -> Optional[str]:
		item = await self.get_item(item_id)
		
		if not item:
			return None
		
		for effect_entry in item.effect_entries:
			if effect_entry.language.name == language:
				return effect_entry.short_effect
		
		return None

	async def get_item_cost(self, item_id: str) -> int:
		item = await self.get_item(item_id)
		
		if not item:
			return 0
		
		return item.cost

	async def give_item(
		self,
		user_id: str,
		item_id: str,
		quantity: int = 1
	) -> Dict:
		is_valid = await self.validate_item(item_id)
		
		if not is_valid:
			raise ValueError(f"Item '{item_id}' não encontrado na PokeAPI")
		
		item = await self.get_item(item_id)
		
		if not item:
			raise ValueError(f"Item '{item_id}' não encontrado")
		
		if hasattr(item, 'flavor_text_entries') and item.flavor_text_entries:
			is_gen3_or_earlier = False
			
			for flavor in item.flavor_text_entries:
				if flavor.version_group.name in VERSION_GROUPS:
					is_gen3_or_earlier = True
					break
			
			if not is_gen3_or_earlier:
				raise ValueError(f"Item `{item_id}` não está disponível na Gen 3")
		
		new_quantity = self.tk.add_item(user_id, item_id, quantity)
		
		item_name = await self.get_item_name(item_id)
		
		return {
			"item_id": item_id,
			"name": item_name,
			"quantity": new_quantity,
			"category": self.get_item_category(item_id),
			"added": quantity
		}

	async def give_random_item(
		self,
		user_id: str,
		item_pool: Optional[List[str]] = None,
		quantity: int = 1
	) -> Dict:
		if not item_pool:
			item_pool = [
				"potion",
				"super-potion",
				"hyper-potion",
				"full-heal",
				"revive",
				"antidote",
				"paralyze-heal",
				"awakening",
				"burn-heal",
				"ice-heal",
				"poke-ball",
				"great-ball",
				"ultra-ball",
				"rare-candy",
				"protein",
				"iron",
				"carbos",
				"calcium",
				"hp-up",
				"zinc",
				"pp-up",
				"pp-max"
			]
		
		item_id = random.choice(item_pool)
		return await self.give_item(user_id, item_id, quantity)

	async def give_level_up_reward(
		self,
		user_id: str,
		pokemon_level: int
	) -> Optional[Dict]:
		if pokemon_level % 10 != 0:
			return None
		
		rewards = {
			10: [("potion", 3)],
			20: [("super-potion", 2), ("poke-ball", 5)],
			30: [("hyper-potion", 2), ("great-ball", 3)],
			40: [("full-heal", 2), ("ultra-ball", 2)],
			50: [("max-potion", 1), ("rare-candy", 1)],
			60: [("full-restore", 2), ("pp-up", 1)],
			70: [("max-revive", 2), ("protein", 1)],
			80: [("full-restore", 3), ("rare-candy", 2)],
			90: [("max-elixir", 2), ("pp-max", 1)],
			100: [("master-ball", 1), ("rare-candy", 5)]
		}
		
		level_rewards = rewards.get(pokemon_level)
		if not level_rewards:
			return None
		
		given_items = []
		for item_id, qty in level_rewards:
			try:
				result = await self.give_item(user_id, item_id, qty)
				given_items.append(result)
			except:
				continue
		
		return {
			"level": pokemon_level,
			"items": given_items
		}

	async def give_capture_reward(
		self,
		user_id: str,
		pokemon: Dict
	) -> List[Dict]:
		rewards = []
		
		base_rewards = [
			("poke-ball", random.randint(1, 3))
		]
		
		if pokemon.get("is_shiny"):
			base_rewards.append(("rare-candy", random.randint(1, 2)))
			base_rewards.append(("ultra-ball", random.randint(2, 5)))
		
		if pokemon.get("is_legendary"):
			base_rewards.append(("master-ball", 1))
			base_rewards.append(("rare-candy", 5))
			base_rewards.append(("max-revive", 3))
		
		if pokemon.get("is_mythical"):
			base_rewards.append(("master-ball", 2))
			base_rewards.append(("rare-candy", 10))
			base_rewards.append(("pp-max", 3))
		
		for item_id, qty in base_rewards:
			try:
				result = await self.give_item(user_id, item_id, qty)
				rewards.append(result)
			except:
				continue
		
		return rewards

	async def use_healing_item(
		self,
		user_id: str,
		pokemon_id: int,
		item_id: str
	) -> Dict:
		if not self.tk.has_item(user_id, item_id):
			raise ValueError("Você não tem esse item")
		
		is_valid = await self.validate_item(item_id)
		if not is_valid:
			raise ValueError("Item inválido")
		
		pokemon = self.tk.get_pokemon(user_id, pokemon_id)
		poke = await self.service.get_pokemon(pokemon["species_id"])
		base_stats = self.service.get_base_stats(poke)
		stats = calculate_stats(base_stats, pokemon["ivs"], pokemon["evs"], pokemon["level"], pokemon["nature"])
		max_hp = stats["hp"]
		current_hp = pokemon.get("current_hp", max_hp)
		
		healing_items = {
			"potion": 20,
			"super-potion": 50,
			"hyper-potion": 200,
			"max-potion": 999999,
			"full-restore": 999999,
			"fresh-water": 50,
			"soda-pop": 60,
			"lemonade": 80,
			"moomoo-milk": 100,
			"energy-powder": 50,
			"energy-root": 200,
			"berry-juice": 20,
			"sweet-heart": 20
		}
		
		heal_amount = healing_items.get(item_id, 0)
		
		if heal_amount > 0:
			new_hp = min(current_hp + heal_amount, max_hp)
			self.tk.set_current_hp(user_id, pokemon_id, new_hp)
			self.tk.remove_item(user_id, item_id, 1)
			
			healed = new_hp - current_hp
			
			del poke
			del base_stats
			
			return {
				"success": True,
				"healed": healed,
				"current_hp": new_hp,
				"max_hp": max_hp,
				"item_used": item_id
			}
		
		del poke
		del base_stats
		
		raise ValueError("Este item não cura HP")

	async def use_revive_item(
		self,
		user_id: str,
		pokemon_id: int,
		item_id: str
	) -> Dict:
		if not self.tk.has_item(user_id, item_id):
			raise ValueError("Você não tem esse item")
		
		is_valid = await self.validate_item(item_id)
		if not is_valid:
			raise ValueError("Item inválido")
		
		pokemon = self.tk.get_pokemon(user_id, pokemon_id)
		
		if pokemon.get("current_hp", 1) > 0:
			raise ValueError("Este Pokémon não está desmaiado")
		
		poke = await self.service.get_pokemon(pokemon["species_id"])
		base_stats = self.service.get_base_stats(poke)
		stats = calculate_stats(base_stats, pokemon["ivs"], pokemon["evs"], pokemon["level"], pokemon["nature"])
		max_hp = stats["hp"]
		
		revive_items = {
			"revive": max_hp // 2,
			"max-revive": max_hp,
			"revival-herb": max_hp
		}
		
		heal_amount = revive_items.get(item_id, 0)
		
		if heal_amount > 0:
			self.tk.set_current_hp(user_id, pokemon_id, heal_amount)
			self.tk.remove_item(user_id, item_id, 1)
			
			if item_id == "revival-herb":
				self.tk.decrease_happiness_revival_herb(user_id, pokemon_id)
			
			del poke
			del base_stats
			
			return {
				"success": True,
				"restored_hp": heal_amount,
				"current_hp": heal_amount,
				"max_hp": max_hp,
				"item_used": item_id
			}
		
		del poke
		del base_stats
		
		raise ValueError("Este item não revive Pokémon")

	async def use_rare_candy(
		self,
		user_id: str,
		pokemon_id: int,
		message: Optional[discord.Message] = None
	) -> Dict:
		if not self.tk.has_item(user_id, "rare-candy"):
			raise ValueError("Você não tem Rare Candy")
		
		pokemon = self.tk.get_pokemon(user_id, pokemon_id)
		
		if pokemon["level"] >= 100:
			raise ValueError("Este Pokémon já está no nível máximo")
		
		self.tk.remove_item(user_id, "rare-candy", 1)
		
		result = await self.add_experience(
			user_id,
			pokemon_id,
			self.tk.get_exp_for_level(pokemon['growth_type'], pokemon['level'] + 1) - pokemon['exp'],
			notify_message=message
		)
		
		return result

	async def use_evolution_stone(
		self,
		user_id: str,
		pokemon_id: int,
		stone_id: str
	) -> Dict:
		if stone_id not in EVOLUTION_STONES:
			raise ValueError("Este não é um item de evolução válido")
		
		if not self.tk.has_item(user_id, stone_id):
			raise ValueError(f"Você não tem {stone_id}")
		
		evolution_data = await self.check_evolution(user_id, pokemon_id, trigger="use-item", item_id=stone_id)
		
		if not evolution_data or evolution_data.get("item") != stone_id:
			pokemon = self.tk.get_pokemon(user_id, pokemon_id)
			pokemon_name = pokemon.get("nickname") or pokemon.get("name", "").title()
			raise ValueError(f"**{pokemon_name}** não pode evoluir com este item")
		
		self.tk.remove_item(user_id, stone_id, 1)
		
		evolved = await self.evolve_pokemon(user_id, pokemon_id, evolution_data["species_id"])
		
		return evolved

	async def _build_pokemon_data(
		self,
		species_id: int,
		level: int = 5,
		forced_gender: Optional[str] = None,
		ivs: Optional[Dict[str, int]] = None,
		nature: Optional[str] = None,
		ability: Optional[str] = None,
		moves: Optional[List[Dict]] = None,
		shiny: Optional[bool] = None,
		held_item: Optional[str] = None,
		nickname: Optional[str] = None,
		status: Optional[dict] = {"name": None, "counter" : 0},
		owner_id: str = "wild",
		on_party: bool = False
	) -> Dict:
		poke: aiopoke.Pokemon = await self.service.get_pokemon(species_id)
		species: aiopoke.PokemonSpecies = await self.service.get_species(species_id)
		base_stats = self.service.get_base_stats(poke)
	
		growth_type: str = species.growth_rate.name
		pkm_name = poke.name
		happiness: int = species.base_happiness
	
		final_ivs = ivs or {k: random.randint(0, 31) for k in base_stats.keys()}
		final_nature = nature or random.choice(list(NATURES.keys()))
	
		is_legendary: bool = species.is_legendary
		is_mythical: bool = species.is_mythical
		poke_types: list = [x.type.name for x in poke.types]
		poke_region: str = REGIONS_GENERATION.get(species.generation.name, "generation-i")
	
		final_level = min(max(level, 1), 100)
		
		gen = generate_pokemon_data(base_stats, level=final_level, nature=final_nature, ivs=final_ivs)
		final_ability = ability or self.service.choose_ability(poke)
		final_moves = moves or self.service.select_level_up_moves(poke, final_level)
		final_gender = self.service.roll_gender(species, forced=forced_gender)
		final_shiny = shiny if shiny is not None else self.service.roll_shiny()
	
		exp = GrowthRate.calculate_exp(growth_type, final_level)
		
		del poke
		del species
		del base_stats
	
		return {
			"id": 0,
			"species_id": species_id,
			"owner_id": owner_id,
			"level": gen["level"],
			"exp": exp,
			"ivs": gen["ivs"],
			"evs": gen["evs"],
			"nature": gen["nature"],
			"ability": final_ability,
			"gender": final_gender,
			"is_shiny": final_shiny,
			"held_item": held_item,
			"caught_at": "",
			"types": poke_types,
			"region": poke_region,
			"is_legendary": is_legendary,
			"is_mythical": is_mythical,
			"moves": final_moves,
			"status": status,
			"happiness": happiness,
			"growth_type": growth_type,
			"base_stats": gen["stats"],
			"current_hp": gen["current_hp"],
			"on_party": on_party,
			"nickname": nickname,
			"name": pkm_name
		}

	async def generate_temp_pokemon(self, **kwargs) -> Dict:
		return await self._build_pokemon_data(**kwargs)

	async def create_pokemon(
		self,
		owner_id: str,
		species_id: int,
		level: int = 5,
		on_party: bool = True,
		give_rewards: bool = True,
		**kwargs
	) -> Dict:
		pkmn = await self._build_pokemon_data(
			species_id=species_id,
			level=level,
			owner_id=owner_id,
			on_party=on_party,
			**kwargs
		)

		created = self.tk.add_pokemon(
			owner_id=pkmn["owner_id"],
			species_id=pkmn["species_id"],
			ivs=pkmn["ivs"],
			nature=pkmn["nature"],
			ability=pkmn["ability"],
			gender=pkmn["gender"],
			shiny=pkmn["is_shiny"],
			level=pkmn["level"],
			moves=pkmn["moves"],
			status=pkmn["status"],
			is_legendary=pkmn["is_legendary"],
			is_mythical=pkmn["is_mythical"],
			types=pkmn["types"],
			region=pkmn["region"],
			on_party=pkmn["on_party"],
			current_hp=pkmn["current_hp"],
			growth_type=pkmn["growth_type"],
			held_item=pkmn["held_item"],
			nickname=pkmn["nickname"],
			happiness=pkmn["happiness"],
			base_stats=pkmn["base_stats"],
			name=pkmn["name"],
			exp=pkmn["exp"]
		)

		if give_rewards:
			await self.give_capture_reward(owner_id, created)

		return created
	
	async def check_evolution(self, owner_id: str, pokemon_id: int, trigger: str = "level-up", item_id: Optional[str] = None) -> Optional[Dict]:
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if self.tk.is_evolution_blocked(owner_id, pokemon_id):
			return None
		
		species = await self.service.get_species(pokemon["species_id"])
		chain = await self.service.client.get_evolution_chain(species.evolution_chain.id)
		
		def find_current_in_chain(chain_link, current_species_id):
			if chain_link.species.name == str(current_species_id) or chain_link.species.url.split('/')[-2] == str(current_species_id):
				return chain_link
			
			for evo in chain_link.evolves_to:
				result = find_current_in_chain(evo, current_species_id)
				if result:
					return result
			return None
		
		current_link = find_current_in_chain(chain.chain, pokemon["species_id"])
		
		if not current_link or not current_link.evolves_to:
			return None
		
		current_time_of_day = self._get_current_time_of_day()
		
		for evolution in current_link.evolves_to:
			evolution_species_id = int(evolution.species.url.split('/')[-2])
			
			if evolution_species_id > 386:
				continue
			
			for detail in evolution.evolution_details:
				if detail.trigger.name != trigger:
					continue
				
				if trigger == "level-up":
					if detail.min_level and pokemon["level"] < detail.min_level:
						continue
					
					if detail.min_happiness:
						current_happiness = pokemon.get("happiness", 0)
						if current_happiness < detail.min_happiness:
							continue
					
					if detail.time_of_day and detail.time_of_day not in ["", None]:
						if detail.time_of_day != current_time_of_day:
							continue
					
					if detail.known_move:
						has_move = False
						known_move_id = detail.known_move.name
						for move in pokemon.get("moves", []):
							if move.get("id") == known_move_id:
								has_move = True
								break
						if not has_move:
							continue
					
					if detail.min_affection and pokemon.get("happiness", 0) < detail.min_affection:
						continue
				
				elif trigger == "use-item":
					if not detail.item:
						continue
					if item_id and detail.item.name != item_id:
						continue
				
				elif trigger == "trade":
					if detail.held_item:
						if pokemon.get("held_item") != detail.held_item.name:
							continue
				
				evolution_name = evolution.species.name.title()
				
				return {
					"species_id": evolution_species_id,
					"name": evolution_name,
					"trigger": detail.trigger.name,
					"min_level": detail.min_level if detail.min_level else None,
					"item": detail.item.name if detail.item else None,
					"min_happiness": detail.min_happiness if detail.min_happiness else None,
					"min_affection": detail.min_affection if detail.min_affection else None,
					"known_move": detail.known_move.name if detail.known_move else None,
					"held_item": detail.held_item.name if detail.held_item else None,
					"time_of_day": detail.time_of_day if detail.time_of_day else None
				}
		
		return None
	
	async def evolve_pokemon(self, owner_id: str, pokemon_id: int, new_species_id: int) -> Dict:
		old_pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		new_poke = await self.service.get_pokemon(new_species_id)
		new_species = await self.service.get_species(new_species_id)
		new_base_stats = self.service.get_base_stats(new_poke)
		
		new_types = [t.type.name for t in new_poke.types]
		is_legendary = new_species.is_legendary
		is_mythical = new_species.is_mythical
		growth_type = new_species.growth_rate.name
		region = REGIONS_GENERATION.get(new_species.generation.name, "generation-i")
		
		new_ability = self.service.choose_ability(new_poke)
		
		final_moves = old_pokemon["moves"].copy()
		
		old_max_hp = old_pokemon["base_stats"]["hp"]
		old_current_hp = old_pokemon.get("current_hp", old_max_hp)
		hp_percent = old_current_hp / old_max_hp if old_max_hp > 0 else 1.0
		
		new_max_hp = new_base_stats["hp"]
		new_current_hp = int(new_max_hp * hp_percent)
		
		self.tk.set_level(owner_id, pokemon_id, old_pokemon["level"])
		
		updated_pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		updated_pokemon["species_id"] = new_species_id
		updated_pokemon["name"] = new_poke.name
		updated_pokemon["types"] = new_types
		updated_pokemon["base_stats"] = new_base_stats
		updated_pokemon["ability"] = new_ability
		updated_pokemon["is_legendary"] = is_legendary
		updated_pokemon["is_mythical"] = is_mythical
		updated_pokemon["growth_type"] = growth_type
		updated_pokemon["region"] = region
		updated_pokemon["current_hp"] = new_current_hp
		
		idx = self.tk._get_pokemon_index(owner_id, pokemon_id)
		self.tk.db["pokemon"][idx] = updated_pokemon
		self.tk._save()
		
		self.tk.set_moves(owner_id, pokemon_id, final_moves)
		
		del new_poke
		del new_species
		del new_base_stats
		
		return self.tk.get_pokemon(owner_id, pokemon_id)
	
	async def process_evolution(
		self,
		owner_id: str,
		pokemon_id: int,
		message: Optional[discord.Message] = None
	) -> Optional[Dict]:
		if not self._acquire_lock(owner_id):
			return None
			
		evolution_data = await self.check_evolution(owner_id, pokemon_id, trigger="level-up")
		
		if not evolution_data:
			self._release_lock(owner_id)
			return None
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if message:
			view = EvolutionChoiceView(
				owner_id=owner_id,
				pokemon_id=pokemon_id,
				current_pokemon=pokemon,
				evolution_species_id=evolution_data["species_id"],
				evolution_name=evolution_data["name"],
				manager=self
			)
			
			extra_info = ""
			if evolution_data.get("min_happiness"):
				extra_info += f" (Felicidade: {pokemon.get('happiness', 0)}/{evolution_data['min_happiness']})"
			if evolution_data.get("time_of_day"):
				time_text = "Dia" if evolution_data["time_of_day"] == "day" else "Noite"
				extra_info += f" ({time_text})"
			
			content = (
				f"<@{owner_id}> {format_pokemon_display(pokemon, bold_name=True)} pode evoluir para **{evolution_data['name']}**!{extra_info}\n"
				f"Você quer evoluir?\n"
				f"-# Você tem até 1 minuto para decidir."
			)
			
			sent_message = await message.channel.send(content=content, view=view)
			view.message = sent_message
			
			return evolution_data
		
		self._release_lock(owner_id)
		return evolution_data
	
	async def process_level_up(
		self,
		owner_id: str,
		pokemon_id: int,
		levels_gained: List[int],
		message: Optional[discord.Message] = None
	) -> Dict:
		if not levels_gained:
			return {
				"learned": [],
				"needs_choice": [],
				"levels_gained": [],
				"evolution": None,
				"rewards": []
			}
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		poke = await self.service.get_pokemon(pokemon["species_id"])
		
		all_moves = self.service.get_level_up_moves(poke)
		
		new_moves = {}
		for move_id, level in all_moves:
			if level in levels_gained:
				new_moves[move_id] = level
		
		learned = []
		needs_choice = []
		
		sorted_moves = sorted(new_moves.items(), key=lambda x: x[1])
		
		for move_id, level in sorted_moves:
			pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
			
			if self.tk.has_move(owner_id, pokemon_id, move_id):
				continue
			
			try:
				move_detail = await self.service.get_move(move_id)
				pp_max = move_detail.pp if move_detail.pp else 10
			except:
				pp_max = 10
			
			if self.tk.can_learn_move(owner_id, pokemon_id):
				self.tk.learn_move(owner_id, pokemon_id, move_id, pp_max)
				learned.append({
					"id": move_id,
					"name": move_id.replace("-", " ").title(),
					"level": level,
					"pp_max": pp_max
				})
			else:
				needs_choice.append({
					"id": move_id,
					"name": move_id.replace("-", " ").title(),
					"level": level,
					"pp_max": pp_max
				})
				
				if message:
					pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
					await self._handle_move_choice(message, owner_id, pokemon_id, move_id, pp_max, pokemon)
		
		del poke
		
		rewards = []
		for level in levels_gained:
			reward = await self.give_level_up_reward(owner_id, level)
			if reward:
				rewards.append(reward)
		
		evolution_data = None
		if message:
			evolution_data = await self.process_evolution(owner_id, pokemon_id, message)
		
		return {
			"learned": learned,
			"needs_choice": needs_choice,
			"levels_gained": levels_gained,
			"evolution": evolution_data,
			"rewards": rewards
		}

	async def _handle_move_choice(
		self,
		message: discord.Message,
		owner_id: str,
		pokemon_id: int,
		new_move_id: str,
		pp_max: int,
		pokemon: Dict
	) -> None:
		if not self._acquire_lock(owner_id):
			return
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if self.tk.has_move(owner_id, pokemon_id, new_move_id):
			self._release_lock(owner_id)
			return
		
		new_move_name = new_move_id.replace("-", " ").title()
		
		current_moves = pokemon.get("moves", [])
		
		view = MoveChoiceView(
			owner_id=owner_id,
			pokemon_id=pokemon_id,
			new_move_id=new_move_id,
			new_move_name=new_move_name,
			pp_max=pp_max,
			current_moves=current_moves,
			pokemon=pokemon,
			manager=self
		)
		
		content = f"<@{owner_id}> {format_pokemon_display(pokemon, bold_name=True)} Quer aprender **{new_move_name}**, mas já conhece 4 movimentos.\nEscolha um movimento para esquecer ou cancele para não aprender **{new_move_name}**.\n-# Você tem até 1 minuto para fazer sua escolha."
		
		sent_message = await message.channel.send(content=content, view=view)
		view.message = sent_message

	async def add_experience(
		self,
		owner_id: str,
		pokemon_id: int,
		exp_gain: int,
		notify_message: Optional[discord.Message] = None
	) -> Dict:
		result = self.tk.add_exp(owner_id, pokemon_id, exp_gain)
		
		if result.get("max_level_reached") and result.get("old_level") < 100:
			if notify_message:
				pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
				await notify_message.channel.send(
					f"{format_pokemon_display(pokemon, bold_name=True)} atingiu o **nível máximo 100**!"
				)
		
		levels_gained = result.get("levels_gained", [])
		
		if levels_gained:
			move_result = await self.process_level_up(owner_id, pokemon_id, levels_gained, notify_message)
			result["move_learning"] = move_result
			
			if notify_message:
				pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
				await self._send_level_up_notification(notify_message, result, move_result)
		else:
			result["move_learning"] = {
				"learned": [],
				"needs_choice": [],
				"levels_gained": [],
				"evolution": None,
				"rewards": []
			}
		
		return result

	async def _send_level_up_notification(
		self,
		message: discord.Message,
		exp_result: Dict,
		move_result: Dict
	) -> None:
		pokemon = self.tk.get_pokemon(exp_result["owner_id"], exp_result["id"])
		
		lines = []
		
		lines.append(f"<:Cuck:1424197273235095616> {format_pokemon_display(pokemon, bold_name=True)} Subiu para o nivel **{move_result.get('levels_gained', [])[-1]}**!")
		
		if move_result.get("learned"):
			lines.append("")
			lines.append("Moves Aprendidos:")
			for move_info in move_result["learned"]:
				lines.append(f"  - {move_info['name']} (Nv. {move_info['level']})")
		
		if move_result.get("rewards"):
			lines.append("")
			lines.append("Recompensas de Nível:")
			for reward in move_result["rewards"]:
				for item in reward["items"]:
					lines.append(f"  - {item['name']} x{item['added']}")
		
		if lines:
			await message.channel.send("\n".join(lines))
		
	def get_party(self, user_id: str) -> List[Dict]:
		return self.tk.get_user_pokemon(user_id, on_party=True)

	def get_box(self, user_id: str) -> List[Dict]:
		return self.tk.get_user_pokemon(user_id, on_party=False)

	def list_all(self, user_id: str) -> List[Dict]:
		return self.tk.list_pokemon_by_owner(user_id)

	async def heal(self, owner_id: str, pokemon_id: int) -> Dict:
		p = self.tk.get_pokemon(owner_id, pokemon_id)
		poke = await self.service.get_pokemon(p["species_id"])
		base_stats = self.service.get_base_stats(poke)
		stats = calculate_stats(base_stats, p["ivs"], p["evs"], p["level"], p["nature"])

		del poke
		del base_stats
		del p

		return self.tk.set_current_hp(owner_id, pokemon_id, stats["hp"])

	def move_to_party(self, owner_id: str, pokemon_id: int) -> Dict:
		return self.tk.move_to_party(owner_id, pokemon_id)

	def move_to_box(self, owner_id: str, pokemon_id: int) -> Dict:
		return self.tk.move_to_box(owner_id, pokemon_id)

	def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> Dict:
		return self.tk.set_moves(owner_id, pokemon_id, moves)

	def iv_percent(self, p: Dict, decimals: int = 2) -> float:
		return iv_percent(p["ivs"], decimals)

	async def close(self):
		await self.service.close()







