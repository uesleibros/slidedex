import random
from typing import Dict, Any, Optional, List
import aiopoke
from pokemon_sdk.calculations import calculate_stats
from .constants import BattleConstants, STAT_MAP
from .helpers import _apply_stage, _get_stat, _types_of

class BattlePokemon:
	__slots__ = (
		'raw', 'species_id', 'name', 'level', 'stats', 'current_hp', 
		'moves', 'pokeapi_data', 'species_data', 'is_shiny', 'stages',
		'status', 'volatile', 'sprites', 'types', 'ability', 'gender',
		'additional_info'
	)
	
	def __init__(self, raw: Dict[str, Any], pokeapi_data: aiopoke.Pokemon, species_data: aiopoke.PokemonSpecies):
		self.raw = raw
		self.species_id = raw["species_id"]
		self.name = raw.get("name")
		self.level = raw["level"]
		self.additional_info: str = ''
		
		base_stats = raw["base_stats"]
		self.stats = calculate_stats(base_stats, raw["ivs"], raw["evs"], raw["level"], raw["nature"])
		
		current_hp = raw.get("current_hp")
		if current_hp is None:
			self.current_hp = self.stats["hp"]
		else:
			self.current_hp = max(0, min(int(current_hp), self.stats["hp"]))
		
		moves = raw.get("moves")
		if not moves:
			self.moves = [{"id": "tackle", "pp": 35, "pp_max": 35}]
		else:
			self.moves = [dict(m) for m in moves]
		
		self.pokeapi_data = pokeapi_data
		self.species_data = species_data
		self.is_shiny = raw.get("is_shiny", False)
		self.stages = {key: 0 for key in ["atk", "def", "sp_atk", "sp_def", "speed", "accuracy", "evasion"]}
		saved_status = raw.get("status")
		if saved_status and isinstance(saved_status, dict):
			self.status = {"name": saved_status.get("name"), "counter": saved_status.get("counter", 0)}
		else:
			self.status = {"name": None, "counter": 0}
		self.volatile = self._init_volatile()
		self.sprites = self._init_sprites()
		self.types = _types_of(self)
		
		self.ability = raw.get("ability")
		self.gender = raw.get("gender")
	
	def _init_volatile(self) -> Dict[str, Any]:
		return {
			"flinch": False,
			"protect": False,
			"endure": False,
			"destiny_bond": False,
			"grudge": False,
			"grudge_active": False,
			"magic_coat": False,
			"magic_coat_turns": 0,
			"snatch": False,
			"snatch_turns": 0,
			"helping_hand": False,
			"helping_hand_target": None,
			"follow_me": False,
			"focus_punch_setup": False,
			"beak_blast_setup": False,
			"shell_trap_setup": False,
			"confuse": 0,
			"attracted": False,
			"attract": False,
			"attract_by": None,
			"attracted_to": None,
			"last_move_used": None,
			"last_move_type": None,
			"last_move_hit": False,
			"last_move_failed": False,
			"leech_seed": False,
			"leech_seed_by": None,
			"ingrain": False,
			"aqua_ring": False,
			"substitute": 0,
			"focus_energy": False,
			"mist": 0,
			"light_screen": 0,
			"reflect": 0,
			"safeguard": 0,
			"stockpile": 0,
			"bind": 0,
			"bind_by": None,
			"bind_damage": 0,
			"bind_type": None,
			"trapped": False,
			"trapped_by": None,
			"spikes_layers": 0,
			"weather": None,
			"weather_turns": 0,
			"perish_count": -1,
			"encore": 0,
			"encore_move": None,
			"taunt": 0,
			"torment": False,
			"torment_last_move": None,
			"disable": 0,
			"disable_move": None,
			"imprison": False,
			"imprisoned_moves": [],
			"imprison_moves": [],
			"yawn": 0,
			"nightmare": False,
			"foresight": False,
			"identified": False,
			"mind_reader_target": None,
			"mind_reader_turns": 0,
			"miracle_eye": False,
			"rage": False,
			"rage_active": False,
			"bide": 0,
			"bide_damage": 0,
			"rollout": 0,
			"rollout_count": 0,
			"fury_cutter": 0,
			"fury_cutter_count": 0,
			"ice_ball_count": 0,
			"uproar": 0,
			"uproar_active": False,
			"locked_move": None,
			"locked_turns": 0,
			"charge": False,
			"charge_turns": 0,
			"charging": False,
			"two_turn_move": None,
			"wish": 0,
			"wish_hp": 0,
			"baneful_bunker": False,
			"kings_shield": False,
			"spiky_shield": False,
			"crafty_shield": False,
			"mat_block": False,
			"quick_guard": False,
			"wide_guard": False,
			"stall_counter": 0,
			"protect_count": 0,
			"transformed": False,
			"transformed_into": None,
			"transform_target": None,
			"mimic_move": None,
			"mimic_pp": 0,
			"mirror_move": None,
			"sketch_move": None,
			"sketch_learned": False,
			"metronome_active": False,
			"metronome_count": 0,
			"sleep_talk_move": None,
			"original_types": None,
			"conversion_type": None,
			"conversion2_type": None,
			"camouflage_type": None,
			"original_ability": None,
			"copied_ability": None,
			"role_play_ability": None,
			"skill_swap_ability": None,
			"original_stats": None,
			"original_moves": None,
			"psych_up_used": False,
			"held_item": None,
			"stolen_item": None,
			"knocked_off_item": None,
			"used_item": None,
			"recycled_item": None,
			"last_item_used": None,
			"received_item": None,
			"given_item": None,
			"trick_used": False,
			"trick_target": False,
			"embargo": 0,
			"heal_block": 0,
			"mud_sport_active": False,
			"water_sport_active": False,
			"field_mud_sport": 0,
			"field_water_sport": 0,
			"trick_room": False,
			"trick_room_turns": 0,
			"gravity": 0,
			"field_gravity": False,
			"minimized": False,
			"minimize_used": False,
			"defense_curl": False,
			"defense_curl_used": False,
			"flash_fire": False,
			"curse": False,
			"powder": False,
			"electrify": False,
			"semi_invulnerable": False,
			"must_recharge": False,
			"roost_used": False,
			"refreshed": False,
			"assist_active": False,
			"teleport": False,
			"fled": False,
			"force_switch": False,
			"baton_pass_effects": None,
			"baton_pass_active": False,
			"heal_bell_used": False,
			"last_damage_taken": 0,
			"last_damage_type": None,
			"pay_day_money": 0,
			"spit_up_power": 0,
			"crash_damage": 0,
			"magnet_rise": 0,
			"telekinesis": 0
		}
	
	def _init_sprites(self) -> Dict[str, Optional[str]]:
		return {
			"front": self.pokeapi_data.sprites.front_shiny if self.is_shiny else self.pokeapi_data.sprites.front_default,
			"back": self.pokeapi_data.sprites.back_shiny if self.is_shiny else self.pokeapi_data.sprites.back_default
		}
	
	@property
	def fainted(self) -> bool:
		return self.current_hp <= 0
	
	@property
	def display_name(self) -> str:
		nickname = self.raw.get("nickname")
		if nickname:
			return f"{nickname} {self.additional_info}".strip()
		return f"{self.name.title()} {self.additional_info}".strip() if self.name else "Pokémon"
	
	@property
	def can_act(self) -> bool:
		if self.fainted:
			return False
		if self.status["name"] in ["sleep", "freeze"]:
			return False
		return True
	
	def eff_stat(self, key: str) -> int:
		val = _apply_stage(_get_stat(self.stats, key), self.stages.get(key, 0))
		if key == "speed" and self.status["name"] == "paralysis":
			val = int(val * BattleConstants.PARALYSIS_SPEED_MULT)
		return max(1, val)
	
	def dec_pp(self, move_id: str, amount: int = 1) -> bool:
		from .helpers import _slug
		slug = _slug(move_id)
		for m in self.moves:
			if _slug(m["id"]) == slug and "pp" in m:
				m["pp"] = max(0, int(m["pp"]) - amount)
				return True
		return False
	
	def get_pp(self, move_id: str) -> Optional[int]:
		from .helpers import _slug
		slug = _slug(move_id)
		for m in self.moves:
			if _slug(m["id"]) == slug:
				return int(m.get("pp", 0))
		return None
	
	def set_status(self, name: str, turns: Optional[int] = None) -> bool:
		if self.status["name"]:
			return False
		if self.volatile.get("safeguard", 0) > 0 and name in ["burn", "poison", "toxic", "paralysis", "sleep", "freeze"]:
			return False
		if self.volatile.get("substitute", 0) > 0:
			return False
		self.status = {
			"name": name,
			"counter": turns if turns is not None else (random.randint(1, 3) if name == "sleep" else 0)
		}
		return True
	
	def clear_status(self) -> bool:
		if not self.status["name"]:
			return False
		self.status = {"name": None, "counter": 0}
		return True
	
	def status_tag(self) -> str:
		from .constants import STATUS_TAGS
		tags = []
		if self.status["name"] in STATUS_TAGS:
			tags.append(STATUS_TAGS[self.status["name"]])
		if self.volatile.get("confuse", 0) > 0:
			tags.append("CNF")
		if self.volatile.get("leech_seed"):
			tags.append("SEED")
		if self.volatile.get("substitute", 0) > 0:
			tags.append("SUB")
		if self.volatile.get("attracted") or self.volatile.get("attract"):
			tags.append("❤️")
		if self.volatile.get("trapped"):
			tags.append("TRAP")
		if self.volatile.get("transformed"):
			tags.append("COPY")
		if self.volatile.get("taunt", 0) > 0:
			tags.append("TAUNT")
		if self.volatile.get("encore", 0) > 0:
			tags.append("ENCORE")
		return f" [{'/'.join(tags)}]" if tags else ""
	
	def take_damage(self, damage: int, ignore_substitute: bool = False) -> int:
		if not ignore_substitute and self.volatile.get("substitute", 0) > 0:
			actual = min(damage, self.volatile["substitute"])
			self.volatile["substitute"] -= actual
			if self.volatile["substitute"] <= 0:
				self.volatile["substitute"] = 0
			return actual
		
		if self.volatile.get("endure") and damage >= self.current_hp and self.current_hp > 0:
			self.current_hp = 1
			return damage - 1
		
		actual = min(damage, self.current_hp)
		self.current_hp = max(0, self.current_hp - damage)
		
		if self.volatile.get("rage") or self.volatile.get("rage_active"):
			self.stages["atk"] = min(BattleConstants.MAX_STAT_STAGE, self.stages["atk"] + 1)
		
		if self.volatile.get("bide", 0) > 0:
			self.volatile["bide_damage"] = self.volatile.get("bide_damage", 0) + actual
		
		self.volatile["last_damage_taken"] = actual
		
		return actual
	
	def heal(self, amount: int) -> int:
		if self.volatile.get("heal_block", 0) > 0:
			return 0
		
		actual = min(amount, self.stats["hp"] - self.current_hp)
		self.current_hp = min(self.stats["hp"], self.current_hp + amount)
		return actual
	
	def can_switch(self) -> bool:
		if self.volatile.get("bind", 0) > 0:
			return False
		if self.volatile.get("trapped"):
			return False
		if self.volatile.get("ingrain"):
			return False
		if self.volatile.get("encore", 0) > 0:
			return False
		if self.volatile.get("semi_invulnerable"):
			return False
		return True
	
	def reset_stats(self) -> None:
		for key in self.stages:
			self.stages[key] = 0
	
	def clear_turn_volatiles(self) -> None:
		self.volatile.update({
			"flinch": False,
			"protect": False,
			"endure": False,
			"destiny_bond": False,
			"magic_coat": False,
			"snatch": False,
			"helping_hand": False,
			"helping_hand_target": None,
			"follow_me": False,
			"focus_punch_setup": False,
			"beak_blast_setup": False,
			"shell_trap_setup": False,
			"baneful_bunker": False,
			"kings_shield": False,
			"spiky_shield": False,
			"mat_block": False,
			"last_move_hit": False,
			"last_move_failed": False
		})
	
	def modify_stat_stage(self, stat: str, stages: int) -> tuple[int, int]:
		mapped_stat = STAT_MAP.get(stat, stat)
		if mapped_stat not in self.stages:
			return 0, 0
		
		if self.volatile.get("mist", 0) > 0 and stages < 0:
			return 0, self.stages[mapped_stat]
		
		old = self.stages[mapped_stat]
		self.stages[mapped_stat] = max(
			BattleConstants.MIN_STAT_STAGE, 
			min(BattleConstants.MAX_STAT_STAGE, self.stages[mapped_stat] + stages)
		)
		
		actual_change = self.stages[mapped_stat] - old
		return actual_change, old
	
	def get_battle_state(self) -> Dict[str, Any]:
		return {
			"current_hp": self.current_hp,
			"moves": [dict(m) for m in self.moves],
			"status": dict(self.status),
			"stages": dict(self.stages),
			"volatile_keys": {
				k: v for k, v in self.volatile.items() 
				if v and k not in [
					"leech_seed_by", "bind_by", "attracted_to", 
					"mind_reader_target", "transformed_into", 
					"helping_hand_target", "attract_by", "trapped_by"
				]
			}
		}
	
	def is_move_disabled(self, move_id: str) -> bool:
		from .helpers import _slug
		slug = _slug(move_id)
		
		if self.volatile.get("disable", 0) > 0:
			disabled_move = self.volatile.get("disable_move")
			if disabled_move and _slug(disabled_move) == slug:
				return True
		
		if self.volatile.get("encore", 0) > 0:
			encore_move = self.volatile.get("encore_move")
			if encore_move and _slug(encore_move) != slug:
				return True
		
		if self.volatile.get("imprison"):
			imprisoned = self.volatile.get("imprisoned_moves", []) or self.volatile.get("imprison_moves", [])
			if slug in imprisoned:
				return True
		
		if self.volatile.get("torment"):
			last = self.volatile.get("torment_last_move")
			if last and _slug(last) == slug:
				return True
		
		return False
	
	def is_status_move_disabled(self) -> bool:
		return self.volatile.get("taunt", 0) > 0
	
	def can_use_item(self) -> bool:
		if self.volatile.get("embargo", 0) > 0:
			return False
		return True
	
	def is_semi_invulnerable(self) -> bool:
		return self.volatile.get("semi_invulnerable", False)
	
	def get_effective_types(self) -> List[str]:
		if self.volatile.get("transformed") and self.volatile.get("transformed_into"):
			target = self.volatile["transformed_into"]
			return target.types.copy() if hasattr(target, 'types') else self.types.copy()
		
		if self.volatile.get("conversion_type"):
			return [self.volatile["conversion_type"]]
		
		if self.volatile.get("conversion2_type"):
			return [self.volatile["conversion2_type"]]
		
		if self.volatile.get("camouflage_type"):
			return [self.volatile["camouflage_type"]]
		
		return self.types.copy()
	
	def get_effective_ability(self) -> Optional[str]:
		if self.volatile.get("role_play_ability"):
			return self.volatile["role_play_ability"]
		
		if self.volatile.get("skill_swap_ability"):
			return self.volatile["skill_swap_ability"]
		
		return self.ability
	
	def reset_volatiles(self) -> None:
		baton_pass_effects = self.volatile.get("baton_pass_effects")
		
		self.volatile = self._init_volatile()
		
		if baton_pass_effects:
			self._apply_baton_pass_effects(baton_pass_effects)
	
	def _apply_baton_pass_effects(self, effects: Dict[str, Any]) -> None:
		if "stages" in effects:
			self.stages = effects["stages"].copy()
		
		passable = ["substitute", "focus_energy", "leech_seed", "confuse", "aqua_ring", "ingrain"]
		for key in passable:
			if key in effects:
				self.volatile[key] = effects[key]
	
	def copy_stat_changes(self, other: 'BattlePokemon') -> None:
		for stat in self.stages:
			self.stages[stat] = other.stages[stat]
	
	def has_move(self, move_id: str) -> bool:
		from .helpers import _slug
		slug = _slug(move_id)
		return any(_slug(m.get("id", "")) == slug for m in self.moves)
	
	def get_move_data(self, move_id: str) -> Optional[Dict[str, Any]]:
		from .helpers import _slug
		slug = _slug(move_id)
		for m in self.moves:
			if _slug(m.get("id", "")) == slug:
				return m
		return None
