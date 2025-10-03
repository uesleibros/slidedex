from typing import Optional, Dict, List, Tuple, Any
from pokemon_sdk.constants import STAT_ALIASES, TYPE_CHART
from __main__ import pm
import discord

class PokeballsView(discord.ui.View):
	def __init__(self, battle, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		self.user_id = battle.user_id
		self.load_pokeballs()
	
	def load_pokeballs(self):
		from .pokeballs import PokeBallSystem, BallType
		
		already_caught = pm.tk.has_caught_species(self.user_id, self.battle.wild.species_id)
		
		available_balls = [
			BallType.POKE_BALL,
			BallType.GREAT_BALL,
			BallType.NET_BALL,
			BallType.NEST_BALL,
			BallType.REPEAT_BALL,
			BallType.TIMER_BALL,
		]
		
		options = []
		for ball_type in available_balls:
			ball_info = PokeBallSystem.BALL_DATA[ball_type]
			modifier = PokeBallSystem.calculate_modifier(
				ball_type,
				self.battle.wild,
				self.battle.turn,
				self.battle.time_of_day,
				self.battle.location_type,
				already_caught
			)
			
			bonus_text = f" [{modifier:.1f}x]" if modifier > 1.0 else ""
			
			options.append(discord.SelectOption(
				label=f"{ball_info['name']}{bonus_text}",
				value=ball_type,
				description=ball_info['description'][:100],
				emoji=ball_info['emoji']
			))
		
		self.children[0].options = options
	
	@discord.ui.select(placeholder="Escolha uma Pokébola...")
	async def select_ball(self, interaction: discord.Interaction, select: discord.ui.Select):
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		
		ball_type = select.values[0]
		self.battle.ball_type = ball_type
		
		await interaction.response.edit_message(view=self.battle.actions_view)
		await self.battle.attempt_capture(ball_type)
	
	@discord.ui.button(style=discord.ButtonStyle.secondary, label="Voltar", emoji="◀️", row=1)
	async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		await interaction.response.edit_message(view=self.battle.actions_view)

class MovesView(discord.ui.View):
	__slots__ = ('battle',)
	
	def __init__(self, battle: object, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		
		for mv in battle.player_active.moves:
			key = _slug(mv["id"])
			md = battle.move_cache.get(key)
			label_text = (md.name if md else key.replace("-", " ").title())
			pp, pp_max = int(mv.get("pp", 0)), int(mv.get("pp_max", 35))
			
			btn = discord.ui.Button(
				style=discord.ButtonStyle.primary if pp > 0 else discord.ButtonStyle.secondary,
				label=f"{label_text} ({pp}/{pp_max})",
				disabled=(pp <= 0)
			)
			btn.callback = self._cb(mv["id"])
			self.add_item(btn)
		
		back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
		async def back_cb(i: discord.Interaction):
			if str(i.user.id) != battle.user_id:
				return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			await i.response.edit_message(view=battle.actions_view)
		back.callback = back_cb
		self.add_item(back)

	def _cb(self, move_id: str):
		async def _run(i: discord.Interaction):
			if str(i.user.id) != self.battle.user_id:
				return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended:
				return await i.response.send_message("A batalha já terminou.", ephemeral=True)
			if getattr(self.battle.actions_view, "force_switch_mode", False):
				return await i.response.send_message("Troque de Pokémon!", ephemeral=True)
			
			await i.response.defer()
			await self.battle.handle_player_move(move_id)
		return _run


class SwitchView(discord.ui.View):
	__slots__ = ('battle',)
	
	def __init__(self, battle: object, force_only: bool = False, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		
		for i, p in enumerate(battle.player_team):
			current_hp = max(0, p.current_hp)
			max_hp = p.stats["hp"]
			hp_percent = (current_hp / max_hp * 100) if max_hp > 0 else 0
			
			lbl = f"{i+1}. {p.display_name} ({current_hp}/{max_hp})"
			
			is_disabled = p.fainted or i == battle.active_player_idx
			
			if p.fainted:
				style = discord.ButtonStyle.secondary
			elif hp_percent > 50:
				style = discord.ButtonStyle.success
			elif hp_percent > 25:
				style = discord.ButtonStyle.primary
			else:
				style = discord.ButtonStyle.danger
			
			btn = discord.ui.Button(
				style=style,
				label=lbl,
				disabled=is_disabled
			)
			btn.callback = self._mk(i)
			self.add_item(btn)
		
		if not force_only:
			back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
			async def back_cb(i: discord.Interaction):
				if str(i.user.id) != battle.user_id:
					return await i.response.send_message("Não é sua batalha!", ephemeral=True)
				await i.response.edit_message(view=battle.actions_view)
			back.callback = back_cb
			self.add_item(back)

	def _mk(self, idx: int):
		async def _run(i: discord.Interaction):
			if str(i.user.id) != self.battle.user_id:
				return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended:
				return await i.response.send_message("A batalha já terminou.", ephemeral=True)
			
			await i.response.defer()
			
			consume = not getattr(self.battle.actions_view, "force_switch_mode", False)
			await self.battle.switch_active(idx, consume_turn=consume)
			
			if getattr(self.battle.actions_view, "force_switch_mode", False):
				self.battle.actions_view.force_switch_mode = False
		return _run


def _get_stat(stats: Dict[str, int], key: str) -> int:
	for alias in STAT_ALIASES.get(key, []):
		if alias in stats:
			return int(stats[alias])
	return 1


def _stage_mult(stage: int) -> float:
	return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def _apply_stage(base: int, stage: int) -> int:
	return max(1, int(base * _stage_mult(stage)))


def _types_of(p: "BattlePokemon") -> List[str]:
	try:
		return [t.type.name.lower() for t in p.pokeapi_data.types]
	except:
		return []


def _type_mult(atk_type: str, def_types: List[str]) -> float:
	atk = (atk_type or "").lower()
	if atk not in TYPE_CHART:
		return 1.0
	m = 1.0
	for d in def_types:
		if d in TYPE_CHART[atk]["immune"]:
			return 0.0
		if d in TYPE_CHART[atk]["super"]:
			m *= 2.0
		elif d in TYPE_CHART[atk]["not"]:
			m *= 0.5
	return m


def _hp_bar(c: int, t: int, l: int = 10) -> str:
	p = 0 if t <= 0 else max(0.0, min(1.0, c / t))
	f = int(round(l * p))
	bar = "█" * f + "░" * (l - f)
	return f"`[{bar}]`"


def _slug(move_id: Any) -> str:
	if move_id is None:
		return ""
	s = str(move_id).strip().lower()
	return s.replace(" ", "-")


def calculate_accuracy_modifier(attacker_acc_stage: int, defender_eva_stage: int) -> float:
	def stage_multiplier(stage: int) -> float:
		if stage >= 0:
			return (3 + stage) / 3
		else:
			return 3 / (3 - stage)
	
	acc_mult = stage_multiplier(attacker_acc_stage)
	eva_mult = stage_multiplier(defender_eva_stage)
	
	return acc_mult / eva_mult


class MoveData:
	__slots__ = (
		'id',
		'name', 'accuracy', 'power', 'priority', 'dmg_class', 'type_name',
		'min_hits', 'max_hits', 'flinch', 'drain', 'recoil', 'healing',
		'ailment', 'ailment_chance', 'stat_changes'
	)
	
	def __init__(
		self,
		name: str,
		accuracy: Optional[int],
		power: int,
		priority: int,
		dmg_class: str,
		type_name: str,
		min_hits: int,
		max_hits: int,
		flinch: int,
		drain: int,
		recoil: int,
		healing: int,
		ailment: Optional[str],
		ailment_chance: int,
		stat_changes: List[Tuple[str, int, bool]]
	):
		self.id = name
		self.name = name
		self.accuracy = accuracy
		self.power = power
		self.priority = priority
		self.dmg_class = dmg_class
		self.type_name = type_name
		self.min_hits = min_hits
		self.max_hits = max_hits
		self.flinch = flinch
		self.drain = drain
		self.recoil = recoil
		self.healing = healing
		self.ailment = ailment
		self.ailment_chance = ailment_chance
		self.stat_changes = stat_changes


def _canon_stat(s: str) -> Optional[str]:
	mapping = {
		"attack": "atk",
		"defense": "def",
		"special-attack": "sp_atk",
		"special-defense": "sp_def",
		"speed": "speed",
		"accuracy": "accuracy",
		"evasion": "evasion"
	}
	return mapping.get(s)


def _pick_frlg(move) -> Dict[str, Optional[int]]:
	try:
		for pv in getattr(move, "past_values", []) or []:
			vg = getattr(pv.version_group, "name", "")
			if vg == "firered-leafgreen":
				return {
					"accuracy": pv.accuracy if pv.accuracy is not None else move.accuracy,
					"power": pv.power if pv.power is not None else move.power,
					"pp": pv.pp if pv.pp is not None else getattr(move, "pp", None),
					"effect_chance": pv.effect_chance if pv.effect_chance is not None else getattr(move, "effect_chance", None)
				}
	except:
		pass
	
	return {
		"accuracy": move.accuracy,
		"power": move.power,
		"pp": getattr(move, "pp", None),
		"effect_chance": getattr(move, "effect_chance", None)
	}


def _normalize_move(move) -> MoveData:
	name = getattr(move, "name", "move").replace("-", " ").title()
	type_name = getattr(getattr(move, "type", None), "name", "normal")
	dc = getattr(getattr(move, "damage_class", None), "name", None)
	dmg_class = dc if dc in {"physical", "special", "status"} else (
		"physical" if (getattr(move, "power", 0) or 0) > 0 else "status"
	)
	
	pv = _pick_frlg(move)
	accuracy = pv["accuracy"]
	power = int(pv["power"] or 0)
	priority = int(getattr(move, "priority", 0) or 0)
	
	meta = getattr(move, "meta", None)
	min_hits = int(getattr(meta, "min_hits", 1) or 1)
	max_hits = int(getattr(meta, "max_hits", 1) or 1)
	flinch = int(getattr(meta, "flinch_chance", 0) or 0)
	drain = int(getattr(meta, "drain", 0) or 0)
	recoil = int(getattr(meta, "recoil", 0) or 0)
	healing = int(getattr(meta, "healing", 0) or 0)
	
	ail = getattr(getattr(meta, "ailment", None), "name", "none")
	ailment = None if ail in {None, "none", "unknown"} else ail
	ailment_chance = int(
		getattr(meta, "ailment_chance", 0) or
		pv["effect_chance"] or
		(100 if (dmg_class == "status" and ailment) else 0) or
		0
	)
	
	stat_changes = []
	try:
		for sc in getattr(move, "stat_changes", []) or []:
			raw = getattr(getattr(sc, "stat", None), "name", None)
			delta = int(getattr(sc, "change", 0) or 0)
			canon = _canon_stat(raw) if raw else None
			if canon and delta != 0:
				target_name = getattr(getattr(move, "target", None), "name", "")
				target_self = target_name in {
					"user", "user-or-ally", "ally", "users-field", "user-and-allies"
				}
				stat_changes.append((canon, delta, target_self))
	except:
		pass
	
	return MoveData(
		name=name,
		accuracy=accuracy,
		power=power,
		priority=priority,
		dmg_class=dmg_class,
		type_name=type_name,
		min_hits=min_hits,
		max_hits=max_hits,
		flinch=flinch,
		drain=drain,
		recoil=recoil,
		healing=healing,
		ailment=ailment,
		ailment_chance=ailment_chance,
		stat_changes=stat_changes
	)
