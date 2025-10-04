# custom_messages.py
import re
from typing import Dict, Any, Optional, List
from enum import Enum

class MessageEvent(Enum):
	CAPTURE = "capture"
	EVOLUTION = "evolution"
	LEVEL_UP = "level_up"
	SHINY_ENCOUNTER = "shiny_encounter"
	LEGENDARY_ENCOUNTER = "legendary_encounter"
	MYTHICAL_ENCOUNTER = "mythical_encounter"
	BATTLE_WIN = "battle_win"
	BATTLE_LOSS = "battle_loss"
	POKEMON_FAINT = "pokemon_faint"
	CRITICAL_HIT = "critical_hit"
	SUPER_EFFECTIVE = "super_effective"
	NOT_VERY_EFFECTIVE = "not_very_effective"
	MOVE_MISS = "move_miss"
	STATUS_APPLIED = "status_applied"
	FULL_HP_DAMAGE = "full_hp_damage"
	HAPPINESS_MAX = "happiness_max"
	IV_PERFECT = "iv_perfect"
	RARE_ABILITY = "rare_ability"
	CATCH_FAIL = "catch_fail"
	CATCH_CRITICAL = "catch_critical"
	DODGE = "dodge"
	PARALYZED_CANT_MOVE = "paralyzed_cant_move"
	CONFUSED_HURT_ITSELF = "confused_hurt_itself"
	WEATHER_DAMAGE = "weather_damage"
	RECOIL_DAMAGE = "recoil_damage"
	HEALING = "healing"
	STAT_BOOST = "stat_boost"
	STAT_DROP = "stat_drop"
	MULTI_HIT = "multi_hit"
	ONE_HIT_KO = "one_hit_ko"
	PARTY_FULL = "party_full"
	LOW_HP = "low_hp"
	POKEMON_TIRED = "pokemon_tired"
	MAX_HAPPINESS = "max_happiness"
	LEARNED_MOVE = "learned_move"
	FORGOT_MOVE = "forgot_move"
	EGG_HATCHING = "egg_hatching"
	TRAINER_BATTLE_START = "trainer_battle_start"
	GYM_BATTLE_START = "gym_battle_start"
	RIVAL_BATTLE_START = "rival_battle_start"

class MessageParser:
	VARIABLE_PATTERN = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
	CONDITIONAL_PATTERN = r'```math
([^```]+)```(.*?)```math
/\1```'
	COMPARISON_PATTERN = r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(=|!=|>=|<=|>|<|contains|in)\s*(.+)$'
	
	@staticmethod
	def parse(template: str, context: Dict[str, Any]) -> str:
		if not template:
			return ""
		
		result = template
		result = MessageParser._process_conditionals(result, context)
		result = MessageParser._process_variables(result, context)
		
		return result
	
	@staticmethod
	def _process_conditionals(text: str, context: Dict[str, Any]) -> str:
		def replace_conditional(match):
			condition = match.group(1)
			content = match.group(2)
			
			if MessageParser._evaluate_condition(condition, context):
				return content
			return ""
		
		max_iterations = 10
		iteration = 0
		while iteration < max_iterations:
			new_text = re.sub(
				MessageParser.CONDITIONAL_PATTERN,
				replace_conditional,
				text,
				flags=re.DOTALL
			)
			if new_text == text:
				break
			text = new_text
			iteration += 1
		
		return text
	
	@staticmethod
	def _process_variables(text: str, context: Dict[str, Any]) -> str:
		def replace_variable(match):
			var_name = match.group(1)
			value = context.get(var_name, f"{{{var_name}}}")
			
			if isinstance(value, bool):
				return "sim" if value else "não"
			elif isinstance(value, (list, tuple)):
				return ", ".join(str(v) for v in value)
			elif isinstance(value, float):
				return f"{value:.2f}"
			
			return str(value)
		
		return re.sub(MessageParser.VARIABLE_PATTERN, replace_variable, text)
	
	@staticmethod
	def _evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
		condition = condition.strip()
		
		match = re.match(MessageParser.COMPARISON_PATTERN, condition)
		if match:
			var_name, operator, value = match.groups()
			var_value = context.get(var_name)
			
			if var_value is None:
				return False
			
			try:
				value = value.strip()
				
				if operator in ["contains", "in"]:
					return MessageParser._compare_contains(var_value, value)
				
				value_cleaned = value.strip('"').strip("'")
				
				if isinstance(var_value, bool):
					value_lower = value_cleaned.lower()
					compare_value = value_lower in ["true", "sim", "yes", "1"]
				elif isinstance(var_value, str):
					compare_value = value_cleaned
				elif isinstance(var_value, (int, float)):
					compare_value = float(value_cleaned)
				else:
					compare_value = value_cleaned
				
				if operator == "=":
					return var_value == compare_value
				elif operator == "!=":
					return var_value != compare_value
				elif operator == ">":
					return var_value > compare_value
				elif operator == "<":
					return var_value < compare_value
				elif operator == ">=":
					return var_value >= compare_value
				elif operator == "<=":
					return var_value <= compare_value
			except Exception:
				return False
		else:
			var_value = context.get(condition)
			if isinstance(var_value, bool):
				return var_value
			return bool(var_value)
		
		return False
	
	@staticmethod
	def _compare_contains(var_value: Any, search_value: str) -> bool:
		search_value = search_value.strip().strip('"').strip("'")
		
		if isinstance(var_value, str):
			return search_value.lower() in var_value.lower()
		elif isinstance(var_value, (list, tuple)):
			return any(search_value.lower() in str(item).lower() for item in var_value)
		
		return False

class CustomMessageSystem:
	DEFAULT_MESSAGES = {
		MessageEvent.CAPTURE: "{pokemon_name} foi capturado[is_shiny] ✨[/is_shiny]!",
		MessageEvent.EVOLUTION: "{old_name} evoluiu para {new_name}!",
		MessageEvent.LEVEL_UP: "{pokemon_name} subiu para o nível {level}!",
		MessageEvent.SHINY_ENCOUNTER: "✨ Um {pokemon_name} shiny selvagem apareceu! ✨",
		MessageEvent.LEGENDARY_ENCOUNTER: "⚡ Um {pokemon_name} lendário apareceu! ⚡",
		MessageEvent.MYTHICAL_ENCOUNTER: "🌟 Um {pokemon_name} mítico apareceu! 🌟",
		MessageEvent.BATTLE_WIN: "💪 Você venceu a batalha!",
		MessageEvent.BATTLE_LOSS: "😔 Você perdeu a batalha...",
		MessageEvent.POKEMON_FAINT: "{pokemon_name} desmaiou!",
		MessageEvent.CRITICAL_HIT: "Um golpe crítico!",
		MessageEvent.SUPER_EFFECTIVE: "É super efetivo!",
		MessageEvent.NOT_VERY_EFFECTIVE: "Não é muito efetivo...",
		MessageEvent.MOVE_MISS: "O ataque errou!",
		MessageEvent.STATUS_APPLIED: "{pokemon_name} foi {status}!",
		MessageEvent.FULL_HP_DAMAGE: "{pokemon_name} recebeu um golpe devastador!",
		MessageEvent.HAPPINESS_MAX: "{pokemon_name} está extremamente feliz! 💖",
		MessageEvent.IV_PERFECT: "Este {pokemon_name} tem IVs perfeitos!",
		MessageEvent.RARE_ABILITY: "{pokemon_name} tem a habilidade rara {ability}!",
		MessageEvent.CATCH_FAIL: "Quase! {pokemon_name} escapou da Pokébola!",
		MessageEvent.CATCH_CRITICAL: "Captura crítica! {pokemon_name} foi capturado imediatamente!",
		MessageEvent.DODGE: "{pokemon_name} desviou do ataque!",
		MessageEvent.PARALYZED_CANT_MOVE: "{pokemon_name} está paralisado e não consegue se mover!",
		MessageEvent.CONFUSED_HURT_ITSELF: "{pokemon_name} está confuso e se machucou!",
		MessageEvent.WEATHER_DAMAGE: "{pokemon_name} foi ferido pelo clima!",
		MessageEvent.RECOIL_DAMAGE: "{pokemon_name} sofreu dano de recuo!",
		MessageEvent.HEALING: "{pokemon_name} recuperou {hp_recovered} HP!",
		MessageEvent.STAT_BOOST: "O {stat} de {pokemon_name} aumentou!",
		MessageEvent.STAT_DROP: "O {stat} de {pokemon_name} diminuiu!",
		MessageEvent.MULTI_HIT: "Acertou {hits} vezes!",
		MessageEvent.ONE_HIT_KO: "Foi um nocaute de um golpe!",
		MessageEvent.PARTY_FULL: "Sua equipe está cheia! {pokemon_name} foi enviado para o PC.",
		MessageEvent.LOW_HP: "{pokemon_name} está com HP baixo!",
		MessageEvent.POKEMON_TIRED: "{pokemon_name} está cansado...",
		MessageEvent.MAX_HAPPINESS: "{pokemon_name} adora você! 💕",
		MessageEvent.LEARNED_MOVE: "{pokemon_name} aprendeu {move_name}!",
		MessageEvent.FORGOT_MOVE: "{pokemon_name} esqueceu {move_name}...",
		MessageEvent.EGG_HATCHING: "O ovo está chocando!",
		MessageEvent.TRAINER_BATTLE_START: "O treinador {trainer_name} quer batalhar!",
		MessageEvent.GYM_BATTLE_START: "Desafio de ginásio contra {gym_leader}!",
		MessageEvent.RIVAL_BATTLE_START: "{rival_name} desafia você para uma batalha!",
	}
	
	def __init__(self, toolkit):
		self.tk = toolkit
		self._ensure_messages_table()
	
	def _ensure_messages_table(self):
		if "custom_messages" not in self.tk.db:
			self.tk.db["custom_messages"] = {}
			self.tk._save()
	
	def get_message(self, user_id: str, event: MessageEvent, context: Dict[str, Any]) -> str:
		with self.tk._lock:
			self._ensure_messages_table()
			
			user_messages = self.tk.db["custom_messages"].get(user_id, {})
			template = user_messages.get(event.value, self.DEFAULT_MESSAGES.get(event, ""))
			
			return MessageParser.parse(template, context)
	
	def set_message(self, user_id: str, event: MessageEvent, template: str) -> bool:
		with self.tk._lock:
			self._ensure_messages_table()
			
			if user_id not in self.tk.db["custom_messages"]:
				self.tk.db["custom_messages"][user_id] = {}
			
			self.tk.db["custom_messages"][user_id][event.value] = template
			self.tk._save()
			return True
	
	def reset_message(self, user_id: str, event: MessageEvent) -> bool:
		with self.tk._lock:
			self._ensure_messages_table()
			
			if user_id in self.tk.db["custom_messages"]:
				if event.value in self.tk.db["custom_messages"][user_id]:
					del self.tk.db["custom_messages"][user_id][event.value]
					self.tk._save()
					return True
			return False
	
	def reset_all_messages(self, user_id: str) -> bool:
		with self.tk._lock:
			self._ensure_messages_table()
			
			if user_id in self.tk.db["custom_messages"]:
				del self.tk.db["custom_messages"][user_id]
				self.tk._save()
				return True
			return False
	
	def list_user_messages(self, user_id: str) -> Dict[str, str]:
		with self.tk._lock:
			self._ensure_messages_table()
			return self.tk.db["custom_messages"].get(user_id, {}).copy()
	
	def preview_message(self, template: str, context: Dict[str, Any]) -> str:
		return MessageParser.parse(template, context)
	
	@staticmethod
	def get_context_variables(event: MessageEvent) -> List[str]:
		base_vars = [
			"pokemon_name", "level", "is_shiny", "is_legendary", "is_mythical",
			"types", "nature", "ability", "gender", "iv_percent", "iv_total", "happiness"
		]
		
		event_specific = {
			MessageEvent.CAPTURE: base_vars + ["ball_type", "critical_capture", "already_caught", "shake_count"],
			MessageEvent.EVOLUTION: base_vars + ["old_name", "new_name", "evolution_method", "old_level"],
			MessageEvent.LEVEL_UP: base_vars + ["old_level", "new_level", "exp_gained"],
			MessageEvent.SHINY_ENCOUNTER: base_vars + ["location", "time_of_day"],
			MessageEvent.LEGENDARY_ENCOUNTER: base_vars + ["location"],
			MessageEvent.MYTHICAL_ENCOUNTER: base_vars + ["location"],
			MessageEvent.BATTLE_WIN: base_vars + ["exp_gained", "money_gained", "turns"],
			MessageEvent.BATTLE_LOSS: base_vars + ["money_lost", "turns"],
			MessageEvent.POKEMON_FAINT: base_vars + ["damage_taken", "attacker_name", "move_name"],
			MessageEvent.CRITICAL_HIT: base_vars + ["move_name", "damage", "target_name"],
			MessageEvent.SUPER_EFFECTIVE: base_vars + ["move_name", "effectiveness", "target_name"],
			MessageEvent.NOT_VERY_EFFECTIVE: base_vars + ["move_name", "effectiveness", "target_name"],
			MessageEvent.MOVE_MISS: base_vars + ["move_name", "target_name"],
			MessageEvent.STATUS_APPLIED: base_vars + ["status", "move_name", "target_name"],
			MessageEvent.FULL_HP_DAMAGE: base_vars + ["damage", "move_name"],
			MessageEvent.HAPPINESS_MAX: base_vars,
			MessageEvent.IV_PERFECT: base_vars + ["perfect_stats"],
			MessageEvent.RARE_ABILITY: base_vars + ["ability_description"],
			MessageEvent.CATCH_FAIL: base_vars + ["shake_count", "ball_type"],
			MessageEvent.CATCH_CRITICAL: base_vars + ["ball_type"],
			MessageEvent.DODGE: base_vars + ["move_name", "attacker_name"],
			MessageEvent.PARALYZED_CANT_MOVE: base_vars,
			MessageEvent.CONFUSED_HURT_ITSELF: base_vars + ["damage"],
			MessageEvent.WEATHER_DAMAGE: base_vars + ["weather", "damage"],
			MessageEvent.RECOIL_DAMAGE: base_vars + ["damage", "move_name"],
			MessageEvent.HEALING: base_vars + ["hp_recovered", "current_hp", "max_hp"],
			MessageEvent.STAT_BOOST: base_vars + ["stat", "stages"],
			MessageEvent.STAT_DROP: base_vars + ["stat", "stages"],
			MessageEvent.MULTI_HIT: base_vars + ["hits", "move_name", "total_damage"],
			MessageEvent.ONE_HIT_KO: base_vars + ["move_name", "target_name"],
			MessageEvent.PARTY_FULL: base_vars,
			MessageEvent.LOW_HP: base_vars + ["current_hp", "max_hp", "hp_percent"],
			MessageEvent.POKEMON_TIRED: base_vars + ["pp_left"],
			MessageEvent.MAX_HAPPINESS: base_vars,
			MessageEvent.LEARNED_MOVE: base_vars + ["move_name", "move_type", "move_power"],
			MessageEvent.FORGOT_MOVE: base_vars + ["move_name"],
			MessageEvent.EGG_HATCHING: ["pokemon_name", "is_shiny", "steps_walked"],
			MessageEvent.TRAINER_BATTLE_START: ["trainer_name", "trainer_class", "pokemon_count"],
			MessageEvent.GYM_BATTLE_START: ["gym_leader", "gym_type", "badge_name"],
			MessageEvent.RIVAL_BATTLE_START: ["rival_name", "location"],
		}
		
		return event_specific.get(event, base_vars)

class MessageContextBuilder:
	@staticmethod
	def from_pokemon(pokemon_data: Dict[str, Any], **extra) -> Dict[str, Any]:
		context = {
			"pokemon_name": pokemon_data.get("nickname") or pokemon_data.get("name", "Unknown"),
			"level": pokemon_data.get("level", 1),
			"is_shiny": pokemon_data.get("is_shiny", False),
			"is_legendary": pokemon_data.get("is_legendary", False),
			"is_mythical": pokemon_data.get("is_mythical", False),
			"types": pokemon_data.get("types", []),
			"nature": pokemon_data.get("nature", ""),
			"ability": pokemon_data.get("ability", ""),
			"gender": pokemon_data.get("gender", ""),
			"happiness": pokemon_data.get("happiness", 0),
		}
		
		if "ivs" in pokemon_data:
			iv_total = sum(pokemon_data["ivs"].values())
			context["iv_total"] = iv_total
			context["iv_percent"] = round((iv_total / 186) * 100, 2)
		
		if "evs" in pokemon_data:
			context["ev_total"] = sum(pokemon_data["evs"].values())
		
		if "current_hp" in pokemon_data and "base_stats" in pokemon_data:
			max_hp = pokemon_data.get("calculated_stats", {}).get("hp", 100)
			current_hp = pokemon_data.get("current_hp", max_hp)
			context["current_hp"] = current_hp
			context["max_hp"] = max_hp
			context["hp_percent"] = round((current_hp / max_hp * 100), 2) if max_hp > 0 else 0
		
		context.update(extra)
		return context
	
	@staticmethod
	def for_capture(pokemon_data: Dict[str, Any], ball_type: str, shake_count: int, critical: bool, already_caught: bool) -> Dict[str, Any]:
		context = MessageContextBuilder.from_pokemon(pokemon_data)
		context.update({
			"ball_type": ball_type,
			"shake_count": shake_count,
			"critical_capture": critical,
			"already_caught": already_caught
		})
		return context
	
	@staticmethod
	def for_evolution(old_data: Dict[str, Any], new_data: Dict[str, Any], method: str) -> Dict[str, Any]:
		context = MessageContextBuilder.from_pokemon(new_data)
		context.update({
			"old_name": old_data.get("nickname") or old_data.get("name", "Unknown"),
			"new_name": new_data.get("nickname") or new_data.get("name", "Unknown"),
			"evolution_method": method,
			"old_level": old_data.get("level", 1)
		})
		return context
	
	@staticmethod
	def for_level_up(pokemon_data: Dict[str, Any], old_level: int, new_level: int, exp_gained: int) -> Dict[str, Any]:
		context = MessageContextBuilder.from_pokemon(pokemon_data)
		context.update({
			"old_level": old_level,
			"new_level": new_level,
			"level": new_level,
			"exp_gained": exp_gained
		})
		return context
	
	@staticmethod
	def for_battle_end(pokemon_data: Dict[str, Any], won: bool, exp_gained: int = 0, money_changed: int = 0, turns: int = 0) -> Dict[str, Any]:
		context = MessageContextBuilder.from_pokemon(pokemon_data)
		context.update({
			"exp_gained": exp_gained,
			"turns": turns
		})
		if won:
			context["money_gained"] = money_changed
		else:
			context["money_lost"] = money_changed
		return context
	
	@staticmethod
	def for_damage(attacker_data: Dict[str, Any], target_data: Dict[str, Any], move_name: str, damage: int, **extra) -> Dict[str, Any]:
		context = MessageContextBuilder.from_pokemon(attacker_data)
		context.update({
			"target_name": target_data.get("nickname") or target_data.get("name", "Unknown"),
			"move_name": move_name,
			"damage": damage
		})
		context.update(extra)
		return context
