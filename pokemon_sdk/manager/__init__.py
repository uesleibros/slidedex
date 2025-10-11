import discord
from typing import List, Optional, Dict, TYPE_CHECKING
from utils.formatting import format_pokemon_display, format_item_display
from ..services import PokeAPIService
from ..calculations import generate_pokemon_data
from ..constants import REGIONS_GENERATION
from .views import MoveChoiceView
from .messages import Messages
from ..evolution import EvolutionProcessor, EvolutionUIHandler, EvolutionConfig, EvolutionTriggers
from .config import GameConfig, StatusConfig, ItemPool, ItemCategories, Emojis
from helpers.growth import GrowthRate

if TYPE_CHECKING:
	from toolkit import Toolkit

HELD_ITEM_EFFECTS = {
	"lucky-egg": {"exp_multiplier": 1.5},
	"exp-share": {"shares_exp": True},
	"soothe-bell": {"happiness_multiplier": 1.5},
	"macho-brace": {"ev_multiplier": 2.0, "speed_modifier": 0.5},
	"amulet-coin": {"money_multiplier": 2.0},
}

class ItemManager:
	def __init__(self, config: GameConfig = None):
		self.config = config or GameConfig()
		self._tk = None
		self._pm = None
	
	@property
	def tk(self) -> 'Toolkit':
		if self._tk is None:
			from pokemon_sdk.config import tk
			self._tk = tk
		return self._tk
	
	@property
	def pm(self):
		if self._pm is None:
			from pokemon_sdk.config import pm
			self._pm = pm
		return self._pm
	
	def get_item(self, item_id: str) -> Optional[object]:
		try:
			return self.pm.service.get_item(item_id)
		except:
			return None
	
	def validate_item(self, item_id: str) -> bool:
		item = self.get_item(item_id)
		return item is not None
	
	def get_item_attributes(self, item_id: str) -> List[str]:
		item = self.get_item(item_id)
		return [attr.name for attr in item.attributes] if item else []
	
	def is_battle_only_item(self, item_id: str) -> bool:
		attributes = self.get_item_attributes(item_id)
		if not attributes:
			return False
		return "usable-in-battle" in attributes and "usable-overworld" not in attributes
	
	def is_consumable(self, item_id: str) -> bool:
		attributes = self.get_item_attributes(item_id)
		return "consumable" in attributes
	
	def is_holdable(self, item_id: str) -> bool:
		attributes = self.get_item_attributes(item_id)
		return "holdable" in attributes
	
	def get_item_category(self, item_id: str) -> str:
		item = self.get_item(item_id)
		if not item:
			return ItemCategories.DEFAULT_CATEGORY
		
		if item.name.endswith(ItemCategories.BERRY_SUFFIX):
			return "berries"
		
		category_name = item.category.name.lower()
		return ItemCategories.MAPPING.get(category_name, ItemCategories.DEFAULT_CATEGORY)
	
	def get_item_name(self, item_id: str, language: str = None) -> str:
		language = language or self.config.default_language
		item = self.get_item(item_id)
		
		if not item:
			return item_id.replace("-", " ").title()
		
		for name_entry in item.names:
			if name_entry.language.name == language:
				return name_entry.name
		
		return item.name.replace("-", " ").title()
	
	def get_item_effect(self, item_id: str, language: str = None) -> Optional[str]:
		language = language or self.config.default_language
		item = self.get_item(item_id)
		
		if not item:
			return None
		
		for effect_entry in item.effect_entries:
			if effect_entry.language.name == language:
				return effect_entry.short_effect
		
		return None
	
	def get_item_cost(self, item_id: str) -> int:
		item = self.get_item(item_id)
		return item.cost if item else 0
	
	def give_item(self, user_id: str, item_id: str, quantity: int = 1) -> Dict:
		is_valid = self.validate_item(item_id)
		if not is_valid:
			raise ValueError(Messages.item_not_found(item_id))
		
		item = self.get_item(item_id)
		if not item:
			raise ValueError(Messages.item_not_found(item_id))
		
		category = self.get_item_category(item_id)
		new_quantity = self.tk.add_item(user_id, item_id, quantity, category)
		item_name = self.get_item_name(item_id)
		
		return {
			"item_id": item_id,
			"name": item_name,
			"quantity": new_quantity,
			"added": quantity
		}
	
	def give_random_item(self, user_id: str, item_pool: Optional[List[str]] = None, quantity: int = 1) -> Dict:
		item_pool = item_pool or ItemPool.RANDOM_ITEMS
		idx = self.tk.roll_random(user_id, 0, len(item_pool))
		item_id = item_pool[idx]
		return self.give_item(user_id, item_id, quantity)
	
	def give_level_up_reward(self, user_id: str, pokemon_level: int) -> Optional[Dict]:
		if pokemon_level % self.config.level_reward_interval != 0:
			return None
		
		level_rewards = ItemPool.LEVEL_REWARDS.get(pokemon_level)
		if not level_rewards:
			return None
		
		given_items = []
		for item_id, qty in level_rewards:
			try:
				if isinstance(qty, tuple):
					qty = self.tk.roll_random(user_id, qty[0], qty[1] + 1)
				result = self.give_item(user_id, item_id, qty)
				given_items.append(result)
			except:
				continue
		
		return {"level": pokemon_level, "items": given_items}
	
	def give_capture_reward(self, user_id: str, pokemon: Dict) -> List[Dict]:
		rewards = []
		reward_list = ItemPool.CAPTURE_REWARDS_BASE.copy()
		
		if pokemon.get("is_shiny"):
			reward_list.extend(ItemPool.CAPTURE_REWARDS_SHINY)
		
		if pokemon.get("is_legendary"):
			reward_list.extend(ItemPool.CAPTURE_REWARDS_LEGENDARY)
		
		if pokemon.get("is_mythical"):
			reward_list.extend(ItemPool.CAPTURE_REWARDS_MYTHICAL)
		
		for item_id, qty in reward_list:
			try:
				if isinstance(qty, tuple):
					qty = self.tk.roll_random(user_id, qty[0], qty[1] + 1)
				result = self.give_item(user_id, item_id, qty)
				rewards.append(result)
			except:
				continue
		
		return rewards

class PokemonManager:
	def __init__(self, config: GameConfig = None):
		self.service = PokeAPIService()
		self._user_locks = {}
		self.config = config or GameConfig()
		self.item_manager = ItemManager(self.config)
		self._tk = None
		
		evolution_config = EvolutionConfig(
			max_generation=self.config.max_generation,
			default_timezone=self.config.default_timezone,
			day_start_hour=self.config.day_start_hour,
			day_end_hour=self.config.day_end_hour
		)
		self.evolution = EvolutionProcessor(evolution_config)
		self.evolution_ui = EvolutionUIHandler(self.evolution)
		
		self.evolution.release_lock = self._release_lock
	
	@property
	def tk(self) -> 'Toolkit':
		"""Lazy import de tk para evitar import circular"""
		if self._tk is None:
			from pokemon_sdk.config import tk
			self._tk = tk
		return self._tk

	def _is_locked(self, owner_id: str) -> bool:
		return self._user_locks.get(owner_id, False)
	
	def _acquire_lock(self, owner_id: str) -> bool:
		if self._is_locked(owner_id):
			return False
		self._user_locks[owner_id] = True
		return True
	
	def _release_lock(self, owner_id: str):
		self._user_locks[owner_id] = False
	
	def _get_held_item_effect(self, item_id: Optional[str], effect_key: str, default=1.0):
		if not item_id:
			return default
		
		item_effect = HELD_ITEM_EFFECTS.get(item_id, {})
		return item_effect.get(effect_key, default)
	
	def _apply_lucky_egg(self, pokemon: Dict, exp_gain: int) -> int:
		held_item = pokemon.get("held_item")
		if held_item == "lucky-egg":
			return int(exp_gain * 1.5)
		return exp_gain
	
	def _apply_macho_brace(self, pokemon: Dict, ev_gain: Dict[str, int]) -> Dict[str, int]:
		held_item = pokemon.get("held_item")
		if held_item == "macho-brace":
			return {stat: value * 2 for stat, value in ev_gain.items()}
		return ev_gain
	
	def _has_exp_share_in_party(self, owner_id: str) -> bool:
		party = self.tk.get_user_party(owner_id)
		return any(p.get("held_item") == "exp-share" for p in party)
	
	def get_item(self, item_id: str) -> Optional[object]:
		return self.item_manager.get_item(item_id)

	def validate_item(self, item_id: str) -> bool:
		return self.item_manager.validate_item(item_id)

	def get_item_attributes(self, item_id: str) -> List[str]:
		return self.item_manager.get_item_attributes(item_id)

	def is_battle_only_item(self, item_id: str) -> bool:
		return self.item_manager.is_battle_only_item(item_id)

	def is_consumable(self, item_id: str) -> bool:
		return self.item_manager.is_consumable(item_id)

	def is_holdable(self, item_id: str) -> bool:
		return self.item_manager.is_holdable(item_id)

	def get_item_category(self, item_id: str) -> str:
		return self.item_manager.get_item_category(item_id)

	def get_item_name(self, item_id: str, language: str = None) -> str:
		return self.item_manager.get_item_name(item_id, language)

	def get_item_effect(self, item_id: str, language: str = None) -> Optional[str]:
		return self.item_manager.get_item_effect(item_id, language)

	def get_item_cost(self, item_id: str) -> int:
		return self.item_manager.get_item_cost(item_id)

	def give_item(self, user_id: str, item_id: str, quantity: int = 1) -> Dict:
		return self.item_manager.give_item(user_id, item_id, quantity)

	def give_random_item(self, user_id: str, item_pool: Optional[List[str]] = None, quantity: int = 1) -> Dict:
		return self.item_manager.give_random_item(user_id, item_pool, quantity)

	def give_level_up_reward(self, user_id: str, pokemon_level: int) -> Optional[Dict]:
		return self.item_manager.give_level_up_reward(user_id, pokemon_level)

	def give_capture_reward(self, user_id: str, pokemon: Dict) -> List[Dict]:
		return self.item_manager.give_capture_reward(user_id, pokemon)

	def _build_pokemon_data(
		self,
		user_id: str,
		species_id: int,
		level: int = None,
		forced_gender: Optional[str] = None,
		ivs: Optional[Dict[str, int]] = None,
		nature: Optional[str] = None,
		ability: Optional[str] = None,
		moves: Optional[List[Dict]] = None,
		shiny: Optional[bool] = None,
		held_item: Optional[str] = None,
		nickname: Optional[str] = None,
		status: Optional[dict] = None,
		caught_with: str = "poke-ball",
		owner_id: str = "wild",
		on_party: bool = False
	) -> Dict:
		level = level or self.config.default_level
		status = status or StatusConfig().default_status
		
		poke = self.service.get_pokemon(species_id)
		species = self.service.get_species(species_id)
		base_stats = self.service.get_base_stats(poke)
	
		final_ivs = ivs or self.tk.roll_ivs(user_id)
		final_nature = nature or self.tk.roll_nature(user_id)
		final_level = max(self.config.min_level, min(level, self.config.max_level))
		
		gen = generate_pokemon_data(base_stats, level=final_level, nature=final_nature, ivs=final_ivs)
		
		final_ability = ability or self.tk.roll_ability(poke, user_id)
		final_moves = moves or self.service.select_level_up_moves(poke, final_level)
		
		gr = getattr(species, "gender_rate", -1)
		if gr == -1:
			male_ratio = -1
		else:
			male_ratio = 1.0 - (gr * 12.5 / 100.0)
		
		final_gender = self.tk.roll_gender(user_id, male_ratio, forced=forced_gender)
		final_shiny = shiny if shiny is not None else self.tk.roll_shiny(user_id)
	
		exp = GrowthRate.calculate_exp(species.growth_rate.name, final_level)
		
		result = {
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
			"caught_with": caught_with,
			"types": [x.type.name for x in poke.types],
			"region": REGIONS_GENERATION.get(species.generation.name, "generation-i"),
			"is_legendary": species.is_legendary,
			"is_mythical": species.is_mythical,
			"moves": final_moves,
			"status": status,
			"happiness": species.base_happiness,
			"growth_type": species.growth_rate.name,
			"base_stats": gen["stats"],
			"current_hp": gen["current_hp"],
			"on_party": on_party,
			"nickname": nickname,
			"name": poke.name
		}
		
		del poke, species, base_stats
		return result

	def generate_temp_pokemon(self, user_id: str, **kwargs) -> Dict:
		return self._build_pokemon_data(user_id=user_id, **kwargs)

	def create_pokemon(
		self,
		owner_id: str,
		species_id: int,
		level: int = None,
		on_party: bool = True,
		give_rewards: bool = True,
		caught_with: str = "poke-ball",
		user_id: str = None,
		**kwargs
	) -> Dict:
		if not user_id: 
			user_id = owner_id
		pkmn = self._build_pokemon_data(
			user_id=owner_id,
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
			caught_with=pkmn["caught_with"],
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
			self.give_capture_reward(owner_id, created)

		return created
	
	def check_evolution(
		self,
		owner_id: str,
		pokemon_id: int,
		trigger: str = EvolutionTriggers.LEVEL_UP,
		item_id: Optional[str] = None
	) -> Optional[Dict]:
		return self.evolution.check_evolution(owner_id, pokemon_id, trigger, item_id)
	
	def evolve_pokemon(self, owner_id: str, pokemon_id: int, new_species_id: int) -> Dict:
		return self.evolution.evolve_pokemon(owner_id, pokemon_id, new_species_id)
	
	async def process_evolution(
		self,
		owner_id: str,
		pokemon_id: int,
		message: Optional[discord.Message] = None
	) -> Optional[Dict]:
		if not self._acquire_lock(owner_id):
			return None
			
		evolution_data = self.evolution.check_evolution(
			owner_id,
			pokemon_id,
			EvolutionTriggers.LEVEL_UP
		)
		
		if not evolution_data:
			self._release_lock(owner_id)
			return None
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if message:
			await self.evolution_ui.show_evolution_choice(
				message,
				owner_id,
				pokemon_id,
				pokemon,
				evolution_data
			)
			return evolution_data
		
		self._release_lock(owner_id)
		return evolution_data

	def give_held_item(
		self,
		owner_id: str,
		pokemon_id: int,
		item_id: str
	) -> Dict:
		if not self.tk.has_item(owner_id, item_id):
			raise ValueError(f"Você não tem o item `{item_id}`.")
		
		if not self.is_holdable(item_id):
			item_name = self.get_item_name(item_id)
			raise ValueError(f"**{item_name}** não pode ser segurado por Pokémon.")
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if pokemon.get("held_item"):
			current_item_name = self.get_item_name(pokemon["held_item"])
			raise ValueError(
				f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} "
				f"já está segurando **{current_item_name}**."
			)
		
		self.tk.remove_item(owner_id, item_id, 1)
		self.tk.set_pokemon_held_item(owner_id, pokemon_id, item_id)
		
		item_name = self.get_item_name(item_id)
		
		return {
			"pokemon": pokemon,
			"item_id": item_id,
			"item_name": item_name
		}
	
	def take_held_item(
		self,
		owner_id: str,
		pokemon_id: int
	) -> Dict:
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		if not pokemon.get("held_item"):
			raise ValueError(
				f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} "
				f"não está segurando nenhum item."
			)
		
		item_id = pokemon["held_item"]
		item_name = self.get_item_name(item_id)
		
		self.tk.set_pokemon_held_item(owner_id, pokemon_id, None)
		self.give_item(owner_id, item_id, 1)
		
		return {
			"pokemon": pokemon,
			"item_id": item_id,
			"item_name": item_name
		}
	
	def swap_held_item(
		self,
		owner_id: str,
		pokemon_id: int,
		new_item_id: str
	) -> Dict:
		if not self.tk.has_item(owner_id, new_item_id):
			raise ValueError(f"Você não tem o item `{new_item_id}`.")
		
		if not self.is_holdable(new_item_id):
			new_item_name = self.get_item_name(new_item_id)
			raise ValueError(f"**{new_item_name}** não pode ser segurado por Pokémon.")
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		old_item_id = pokemon.get("held_item")
		
		self.tk.remove_item(owner_id, new_item_id, 1)
		
		if old_item_id:
			self.give_item(owner_id, old_item_id, 1)
			old_item_name = self.get_item_name(old_item_id)
		else:
			old_item_name = None
		
		self.tk.set_pokemon_held_item(owner_id, pokemon_id, new_item_id)
		new_item_name = self.get_item_name(new_item_id)
		
		return {
			"pokemon": pokemon,
			"old_item_id": old_item_id,
			"old_item_name": old_item_name,
			"new_item_id": new_item_id,
			"new_item_name": new_item_name
		}
	
	def add_evs(
		self,
		owner_id: str,
		pokemon_id: int,
		ev_gain: Dict[str, int]
	) -> Dict:
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		modified_ev_gain = self._apply_macho_brace(pokemon, ev_gain)
		
		result = self.tk.add_evs(owner_id, pokemon_id, modified_ev_gain)
		
		return {
			"pokemon": result,
			"ev_gain": modified_ev_gain,
			"had_macho_brace": pokemon.get("held_item") == "macho-brace"
		}
	
	async def process_level_up(
		self,
		owner_id: str,
		pokemon_id: int,
		levels_gained: List[int],
		message: Optional[discord.Message] = None
	) -> Dict:
		if not levels_gained:
			return self._empty_level_up_result()
		
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		poke = self.service.get_pokemon(pokemon["species_id"])
		
		all_moves = self.service.get_level_up_moves(poke)
		new_moves = {move_id: level for move_id, level in all_moves if level in levels_gained}
		
		learned, needs_choice = await self._process_moves(
			owner_id, pokemon_id, new_moves, message
		)
		
		del poke
		
		rewards = [reward for level in levels_gained if (reward := self.give_level_up_reward(owner_id, level))]
		
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
	
	def _empty_level_up_result(self) -> Dict:
		return {
			"learned": [],
			"needs_choice": [],
			"levels_gained": [],
			"evolution": None,
			"rewards": []
		}
	
	async def _process_moves(
		self,
		owner_id: str,
		pokemon_id: int,
		new_moves: Dict[str, int],
		message: Optional[discord.Message]
	) -> tuple[List[Dict], List[Dict]]:
		learned = []
		needs_choice = []
		
		sorted_moves = sorted(new_moves.items(), key=lambda x: x[1])
		
		for move_id, level in sorted_moves:
			pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
			
			if self.tk.has_move(owner_id, pokemon_id, move_id):
				continue
			
			pp_max = self._get_move_pp(move_id)
			
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
		
		return learned, needs_choice
	
	def _get_move_pp(self, move_id: str, default: int = 10) -> int:
		try:
			move_detail = self.service.get_move(move_id)
			return move_detail.pp if move_detail.pp else default
		except:
			return default

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
		
		content = Messages.move_choice(
			owner_id,
			format_pokemon_display(pokemon, bold_name=True),
			new_move_name
		)
		
		sent_message = await message.channel.send(content=content, view=view)
		view.message = sent_message

	async def add_experience(
		self,
		owner_id: str,
		pokemon_id: int,
		exp_gain: int,
		notify_message: Optional[discord.Message] = None,
		share_exp: bool = True
	) -> Dict:
		pokemon = self.tk.get_pokemon(owner_id, pokemon_id)
		
		modified_exp = self._apply_lucky_egg(pokemon, exp_gain)
		
		result = self.tk.add_exp(owner_id, pokemon_id, modified_exp)
		result["original_exp"] = exp_gain
		result["lucky_egg_bonus"] = modified_exp - exp_gain
		
		if share_exp and self._has_exp_share_in_party(owner_id):
			await self._distribute_exp_share(owner_id, pokemon_id, exp_gain, notify_message)
		
		if result.get("max_level_reached") and result.get("old_level") < self.config.max_level:
			if notify_message:
				await notify_message.channel.send(
					Messages.max_level_reached(
						format_pokemon_display(pokemon, bold_name=True),
						self.config.max_level
					)
				)
		
		levels_gained = result.get("levels_gained", [])
		
		if levels_gained:
			move_result = await self.process_level_up(owner_id, pokemon_id, levels_gained, notify_message)
			result["move_learning"] = move_result
			
			if notify_message:
				await self._send_level_up_notification(notify_message, result, move_result)
		else:
			result["move_learning"] = self._empty_level_up_result()
		
		return result

	async def _distribute_exp_share(
		self,
		owner_id: str,
		battler_pokemon_id: int,
		base_exp: int,
		notify_message: Optional[discord.Message] = None
	) -> None:
		party = self.tk.get_user_party(owner_id)
		shared_exp = int(base_exp * 0.5)
		
		for pokemon in party:
			if pokemon["id"] == battler_pokemon_id:
				continue
			
			if pokemon.get("current_hp", 0) <= 0:
				continue
			
			if pokemon.get("level", 1) >= 100:
				continue
			
			modified_shared_exp = self._apply_lucky_egg(pokemon, shared_exp)
			
			result = self.tk.add_exp(owner_id, pokemon["id"], modified_shared_exp)
			
			levels_gained = result.get("levels_gained", [])
			if levels_gained and notify_message:
				move_result = await self.process_level_up(owner_id, pokemon["id"], levels_gained, notify_message)
				await self._send_level_up_notification(notify_message, result, move_result)

	async def _send_level_up_notification(
		self,
		message: discord.Message,
		exp_result: Dict,
		move_result: Dict
	) -> None:
		pokemon = self.tk.get_pokemon(exp_result["owner_id"], exp_result["id"])
		
		lines = [
			Messages.level_up(
				format_pokemon_display(pokemon, bold_name=True),
				move_result.get('levels_gained', [])[-1],
				Emojis.LEVEL_UP
			)
		]
		
		if exp_result.get("lucky_egg_bonus", 0) > 0:
			lines.append(f"{format_item_display('lucky-egg')}: +{exp_result['lucky_egg_bonus']} EXP extra")
		
		if move_result.get("learned"):
			lines.append("")
			lines.append("Moves Aprendidos:")
			lines.extend(f"  - {move['name']} (Nv. {move['level']})" for move in move_result["learned"])
		
		if move_result.get("rewards"):
			lines.append("")
			lines.append("Recompensas de Nível:")
			for reward in move_result["rewards"]:
				lines.extend(f"  - {item['name']} x{item['added']}" for item in reward["items"])
		
		if lines:
			await message.channel.send("\n".join(lines))

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
			notify_message=message,
			share_exp=False
		)
		
		return result
		
	def close(self):
		self.service.close()