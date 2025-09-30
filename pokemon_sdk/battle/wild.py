import discord
import aiopoke
import random
import math
import asyncio
from __main__ import pm
from typing import List, Dict, Any, Optional, Tuple, Set
from utils.canvas import compose_battle_async
from pokemon_sdk.calculations import calculate_stats
from pokemon_sdk.constants import TYPE_CHART, STAT_ALIASES
from utils.preloaded import preloaded_textures
from utils.pokemon_emojis import get_app_emoji
from helpers.effect_mapper import effect_mapper
from .helpers import SwitchView, MovesView, MoveData, _normalize_move, _pick_frlg, _canon_stat, _get_stat, _stage_mult, _apply_stage, _types_of, _type_mult, _hp_bar, _slug

STAT_NAMES = {
	"atk": "Ataque",
	"def": "Defesa",
	"sp_atk": "Ataque Especial",
	"sp_def": "Defesa Especial",
	"speed": "Velocidade",
	"accuracy": "Precisão",
	"evasion": "Evasão"
}

STATUS_TAGS = {
	"burn": "BRN",
	"poison": "PSN",
	"paralysis": "PAR",
	"sleep": "SLP",
	"freeze": "FRZ",
	"toxic": "TOX"
}

STATUS_MESSAGES = {
	"burn": "foi queimado",
	"poison": "foi envenenado",
	"paralysis": "foi paralisado",
	"sleep": "adormeceu",
	"freeze": "foi congelado",
	"toxic": "foi gravemente envenenado",
	"confusion": "ficou confuso"
}

class BattlePokemon:
	def __init__(self, raw: Dict[str, Any], pokeapi_data: aiopoke.Pokemon, species_data: aiopoke.PokemonSpecies):
		self.raw = raw
		self.species_id = raw["species_id"]
		self.name = raw.get("name")
		self.level = raw["level"]
		base_stats = pm.service.get_base_stats(pokeapi_data)
		self.stats = calculate_stats(base_stats, raw["ivs"], raw["evs"], raw["level"], raw["nature"])
		self.current_hp = raw.get("current_hp") or self.stats["hp"]
		self.moves = raw.get("moves") or [{"id":"tackle","pp":35,"pp_max":35}]
		self.pokeapi_data = pokeapi_data
		self.species_data = species_data
		self.is_shiny = raw.get("is_shiny", False)
		self.stages = {key: 0 for key in ["atk","def","sp_atk","sp_def","speed","accuracy","evasion"]}
		self.status = {"name": None, "counter": 0}
		self.volatile = {"flinch": False, "confuse": 0}
		self.sprites = {
			"front": pokeapi_data.sprites.front_shiny if self.is_shiny else pokeapi_data.sprites.front_default,
			"back": pokeapi_data.sprites.back_shiny if self.is_shiny else pokeapi_data.sprites.back_default
		}

	@property
	def fainted(self) -> bool:
		return self.current_hp <= 0

	@property
	def display_name(self) -> str:
		return self.name.title() if self.name else "Pokémon"

	def eff_stat(self, key: str) -> int:
		val = _apply_stage(_get_stat(self.stats, key), self.stages.get(key, 0))
		if key == "speed" and self.status["name"] == "paralysis":
			val = int(val * 0.5)
		return max(1, val)

	def dec_pp(self, move_id: str) -> bool:
		slug = _slug(move_id)
		for m in self.moves:
			if _slug(m["id"]) == slug and "pp" in m:
				m["pp"] = max(0, int(m["pp"]) - 1)
				return True
		return False

	def get_pp(self, move_id: str) -> Optional[int]:
		slug = _slug(move_id)
		for m in self.moves:
			if _slug(m["id"]) == slug:
				return int(m.get("pp", 0))
		return None

	def set_status(self, name: str, turns: Optional[int] = None) -> bool:
		if self.status["name"]:
			return False
		self.status = {
			"name": name,
			"counter": turns if turns is not None else (random.randint(1, 3) if name == "sleep" else 0)
		}
		return True

	def status_tag(self) -> str:
		return f" [{STATUS_TAGS[self.status['name']]}]" if self.status["name"] in STATUS_TAGS else ""

	def take_damage(self, damage: int) -> int:
		actual = min(damage, self.current_hp)
		self.current_hp = max(0, self.current_hp - damage)
		return actual

	def heal(self, amount: int) -> int:
		actual = min(amount, self.stats["hp"] - self.current_hp)
		self.current_hp = min(self.stats["hp"], self.current_hp + amount)
		return actual

class WildBattle:
	def __init__(self, player_party: List[Dict[str, Any]], wild: Dict[str, Any], user_id: str, interaction: discord.Interaction) -> None:
		self.user_id = user_id
		self.interaction = interaction
		self.player_party_raw = player_party
		self.active_player_idx = 0
		self.wild_raw = wild
		self.ended = False
		self.turn = 1
		self.message: Optional[discord.Message] = None
		self.lock = asyncio.Lock()
		self.player_team: List[BattlePokemon] = []
		self.wild: Optional[BattlePokemon] = None
		self.actions_view: Optional[WildBattleView] = None
		self.lines: List[str] = []
		self.must_redraw_image = True
		self.move_cache: Dict[str, MoveData] = {}
		self.effect_cache: Dict[str, Dict[str, Any]] = {}

	@property
	def player_active(self) -> BattlePokemon:
		return self.player_team[self.active_player_idx]

	async def setup(self):
		w_api, w_spec = await asyncio.gather(
			pm.service.get_pokemon(self.wild_raw["species_id"]),
			pm.service.get_species(self.wild_raw["species_id"])
		)
		self.wild = BattlePokemon(self.wild_raw, w_api, w_spec)
		
		party_coros = []
		for p in self.player_party_raw:
			party_coros.extend([
				pm.service.get_pokemon(p["species_id"]),
				pm.service.get_species(p["species_id"])
			])
		
		party_data = await asyncio.gather(*party_coros)
		for i in range(0, len(party_data), 2):
			self.player_team.append(BattlePokemon(
				self.player_party_raw[i // 2],
				party_data[i],
				party_data[i + 1]
			))
		
		await self._warm_moves()

	async def _warm_moves(self):
		ids: Set[str] = set()
		for mv in self.wild.moves:
			ids.add(_slug(mv["id"]))
		for p in self.player_team:
			for mv in p.moves:
				ids.add(_slug(mv["id"]))
		
		if ids:
			await asyncio.gather(*[self._fetch_move(mid) for mid in ids if mid])

	async def _compose_image(self):
		pb = await self.player_active.sprites["back"].read() if self.player_active.sprites["back"] else None
		ef = await self.wild.sprites["front"].read() if self.wild.sprites["front"] else None
		buf = await compose_battle_async(pb, ef, preloaded_textures["battle"])
		return discord.File(buf, filename="battle.png")

	def _hp_line(self, p: BattlePokemon) -> str:
		emoji = get_app_emoji(f"p_{p.species_id}")
		bar = _hp_bar(p.current_hp, p.stats["hp"])
		hp_percent = (p.current_hp / p.stats["hp"] * 100) if p.stats["hp"] > 0 else 0
		return f"{emoji} **{p.display_name}**{p.status_tag()} Lv{p.level}\n{bar} {max(0, p.current_hp)}/{p.stats['hp']} ({hp_percent:.1f}%)"

	def _embed(self) -> discord.Embed:
		desc_parts = [
			self._hp_line(self.player_active),
			"**VS**",
			self._hp_line(self.wild),
			""
		]
		
		if self.lines:
			desc_parts.extend(self.lines)
		
		embed = discord.Embed(
			title=f"Batalha Selvagem - Turno {self.turn}",
			description="\n".join(desc_parts),
			color=discord.Color.green()
		)

		embed.set_footer(text="Effex Engine v1.2")
		embed.set_image(url="attachment://battle.png")
		return embed

	async def start(self):
		self.actions_view = WildBattleView(self)
		self.lines = ["A batalha começou!"]
		self.message = await self.interaction.channel.send(
			embed=self._embed(),
			file=await self._compose_image(),
			view=self.actions_view
		)
		self.must_redraw_image = False

	async def refresh(self):
		if not self.message:
			return
		embed = self._embed()
		if self.must_redraw_image:
			file = await self._compose_image()
			await self.message.edit(attachments=[file], embed=embed, view=self.actions_view)
			self.must_redraw_image = False
		else:
			await self.message.edit(embed=embed, view=self.actions_view)

	async def _fetch_move(self, move_id: str) -> MoveData:
		key = _slug(move_id)
		if not key:
			raise ValueError("move_id vazio")
		if key in self.move_cache:
			return self.move_cache[key]
		
		mv = await pm.service.get_move(key)
		md = _normalize_move(mv)
		self.move_cache[key] = md
		
		effect_text = getattr(mv, "effect_entries", [])
		for entry in effect_text:
			if entry.language.name == "en":
				self.effect_cache[key] = effect_mapper.get(entry.short_effect, {})
				break
		
		if key not in self.effect_cache:
			self.effect_cache[key] = {}
		
		return md

	def _get_effect_data(self, move_id: str) -> Dict[str, Any]:
		return self.effect_cache.get(_slug(move_id), {})

	def _pre_action(self, user: BattlePokemon) -> Tuple[bool, List[str]]:
		if user.volatile["flinch"]:
			user.volatile["flinch"] = False
			return True, [f"💨 {user.display_name} recuou de medo e não conseguiu agir!"]
		
		status = user.status["name"]
		counter = user.status["counter"]
		
		if status == "sleep":
			if counter > 1:
				user.status["counter"] -= 1
				return True, [f"💤 {user.display_name} está dormindo... (resta {user.status['counter']} turno(s))"]
			user.status = {"name": None, "counter": 0}
			return False, [f"👁️ {user.display_name} acordou!"]
		
		if status == "freeze":
			if random.random() < 0.2:
				user.status = {"name": None, "counter": 0}
				return False, [f"🔥 {user.display_name} descongelou!"]
			return True, [f"❄️ {user.display_name} está congelado e não pode se mover!"]
		
		if status == "paralysis" and random.random() < 0.25:
			return True, [f"⚡ {user.display_name} está paralisado e não consegue se mover!"]
		
		return False, []

	def _confusion(self, user: BattlePokemon) -> Tuple[bool, List[str]]:
		if user.volatile["confuse"] <= 0:
			return False, []
		
		user.volatile["confuse"] -= 1
		
		if user.volatile["confuse"] == 0:
			return False, [f"✨ {user.display_name} não está mais confuso!"]
		
		if random.random() < 0.33:
			atk = user.eff_stat("atk")
			df = user.eff_stat("def")
			base = (((2 * user.level / 5) + 2) * 40 * (atk / max(1, df))) / 50 + 2
			dmg = max(1, int(base * random.uniform(0.85, 1.0)))
			user.take_damage(dmg)
			return True, [f"😵 {user.display_name} está confuso e se atingiu causando {dmg} de dano!"]
		
		return False, [f"😵 {user.display_name} está confuso... (resta {user.volatile['confuse']} turno(s))"]

	def _apply_stat_change(self, target: BattlePokemon, stat: str, stages: int) -> Optional[str]:
		stat_map = {
			"attack": "atk",
			"defense": "def",
			"special_attack": "sp_atk",
			"special-attack": "sp_atk",
			"special_defense": "sp_def",
			"special-defense": "sp_def",
			"speed": "speed",
			"accuracy": "accuracy",
			"evasion": "evasion"
		}
		
		mapped_stat = stat_map.get(stat, stat)
		if mapped_stat not in target.stages:
			return None
		
		old = target.stages[mapped_stat]
		target.stages[mapped_stat] = max(-6, min(6, target.stages[mapped_stat] + stages))
		
		if target.stages[mapped_stat] == old:
			if old == 6 and stages > 0:
				return f"   └─ 💢 {STAT_NAMES[mapped_stat]} de {target.display_name} já está no máximo!"
			elif old == -6 and stages < 0:
				return f"   └─ 💢 {STAT_NAMES[mapped_stat]} de {target.display_name} já está no mínimo!"
			return None
		
		change = target.stages[mapped_stat] - old
		
		if change > 0:
			level = "drasticamente" if abs(change) >= 2 else ""
			arrows = "↑" * abs(change)
			return f"   └─ 📈 {STAT_NAMES[mapped_stat]} de {target.display_name} aumentou {level} {arrows}".strip()
		else:
			level = "drasticamente" if abs(change) >= 2 else ""
			arrows = "↓" * abs(change)
			return f"   └─ 📉 {STAT_NAMES[mapped_stat]} de {target.display_name} diminuiu {level} {arrows}".strip()

	def _apply_status_effect(self, target: BattlePokemon, effect_type: str) -> Optional[str]:
		tt = _types_of(target)
		
		immunity_checks = {
			"burn": ("fire", f"   └─ 💢 {target.display_name} é do tipo Fogo e não pode ser queimado!"),
			"poison": (["steel", "poison"], f"   └─ 💢 {target.display_name} é imune a veneno!"),
			"freeze": ("ice", f"   └─ 💢 {target.display_name} é do tipo Gelo e não pode ser congelado!")
		}
		
		if effect_type in immunity_checks:
			immune_types, message = immunity_checks[effect_type]
			immune_types = [immune_types] if isinstance(immune_types, str) else immune_types
			if any(t in tt for t in immune_types):
				return message
		
		if target.set_status(effect_type):
			status_icons = {
				"burn": "🔥",
				"poison": "☠️",
				"toxic": "☠️☠️",
				"paralysis": "⚡",
				"sleep": "💤",
				"freeze": "❄️"
			}
			
			status_effects = {
				"burn": "Sofrerá dano todo turno e terá Ataque reduzido!",
				"poison": "Sofrerá dano todo turno!",
				"toxic": "Sofrerá dano crescente a cada turno!",
				"paralysis": "Velocidade reduzida e pode falhar ao agir!",
				"sleep": "Não poderá agir por alguns turnos!",
				"freeze": "Não poderá agir até descongelar!"
			}
			
			icon = status_icons.get(effect_type, "💫")
			main = f"   └─ {icon} {target.display_name} {STATUS_MESSAGES[effect_type]}!"
			effect = status_effects.get(effect_type, "")
			
			if effect:
				return f"{main}\n   └─ ⚠️ {effect}"
			return main
		
		return f"   └─ 💢 {target.display_name} já está afetado por outro status!"

	def _apply_effect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage_dealt: int) -> List[str]:
		lines = []
		eff_type = effect.get("type")
		chance = effect.get("chance", 100)
		tgt_type = effect.get("target", "opponent")
		
		if chance < 100 and random.randint(1, 100) > chance:
			return lines
		
		actual_target = user if tgt_type == "self" else target

		if eff_type == "stat_change":
			stat = effect.get("stat")
			stages = effect.get("stages", 0)
			result = self._apply_stat_change(actual_target, stat, stages)
			if result:
				lines.append(result)

		elif eff_type in ["burn", "poison", "paralysis", "sleep", "freeze", "toxic"]:
			result = self._apply_status_effect(actual_target, eff_type)
			if result:
				lines.append(result)

		elif eff_type == "confusion":
			actual_target.volatile["confuse"] = max(actual_target.volatile["confuse"], random.randint(2, 4))
			lines.append(f"   └─ 😵 {actual_target.display_name} ficou confuso!")
			lines.append(f"   └─ ⚠️ Pode atacar a si mesmo nos próximos turnos!")

		elif eff_type == "flinch":
			actual_target.volatile["flinch"] = True

		elif eff_type == "heal":
			amount = effect.get("amount", 0.5)
			heal = max(1, int(user.stats["hp"] * amount))
			actual = user.heal(heal)
			if actual > 0:
				lines.append(f"   └─ 💚 {user.display_name} recuperou {actual} HP!")

		return lines

	def _apply_recoil(self, user: BattlePokemon, recoil: float, damage: int) -> List[str]:
		if recoil <= 0 or damage <= 0:
			return []
		recoil_dmg = max(1, int(damage * recoil))
		actual = user.take_damage(recoil_dmg)
		return [f"   └─ 💥 {user.display_name} sofreu {actual} de dano de recuo!"]

	def _apply_drain(self, user: BattlePokemon, drain: float, damage: int) -> List[str]:
		if drain <= 0 or damage <= 0:
			return []
		heal_amt = max(1, int(damage * drain))
		actual = user.heal(heal_amt)
		if actual > 0:
			return [f"   └─ 💉 {user.display_name} drenou {actual} HP do oponente!"]
		return []

	async def _calc_damage(self, atk: BattlePokemon, df: BattlePokemon, md: MoveData, effect_data: Dict[str, Any]) -> Tuple[int, float, bool]:
		if md.power <= 0 and not effect_data.get("damage", False):
			return 0, 1.0, False
		
		power = md.power
		if effect_data.get("fixed_damage"):
			return effect_data["fixed_damage"], 1.0, False

		if power <= 0:
			return 0, 1.0, False

		if md.dmg_class == "special":
			a = atk.eff_stat("sp_atk")
			d = df.eff_stat("sp_def")
		else:
			a = atk.eff_stat("atk")
			d = df.eff_stat("def")
			if atk.status["name"] == "burn":
				a = int(a * 0.5)

		base = (((2 * atk.level / 5) + 2) * power * (a / max(1, d))) / 50 + 2
		tm = _type_mult(md.type_name, _types_of(df))
		
		if tm == 0.0:
			return 0, 0.0, False

		stab = 1.5 if md.type_name.lower() in _types_of(atk) else 1.0
		
		crit_ratio = effect_data.get("critical_hit_ratio", 0)
		crit_chance = 0.0625 * (2 ** crit_ratio) if crit_ratio > 0 else 0.0625
		crit = random.random() < crit_chance

		damage = int(base * stab * tm * random.uniform(0.85, 1.0) * (1.5 if crit else 1.0))
		return max(1, damage), tm, crit

	async def _use_move(self, user: BattlePokemon, target: BattlePokemon, md: MoveData, move_id_for_pp: Optional[str]) -> List[str]:
		if move_id_for_pp and move_id_for_pp != "__struggle__":
			pp = user.get_pp(move_id_for_pp)
			if pp is not None and pp <= 0:
				return [f"❌ {user.display_name} não tem mais PP para usar {md.name}!"]
			user.dec_pp(move_id_for_pp)

		effect_data = self._get_effect_data(move_id_for_pp or "tackle")
		
		if md.accuracy is not None and not effect_data.get("bypass_accuracy", False):
			if random.randint(1, 100) > int(md.accuracy):
				return [f"💨 {user.display_name} usou **{md.name}**, mas errou!"]

		if md.dmg_class == "status" or md.power == 0:
			return await self._apply_status_move(user, target, md, effect_data)

		lines = []
		multi_hit = effect_data.get("multi_hit", {})
		hits = 1
		if multi_hit:
			min_hits = multi_hit.get("min", 1)
			max_hits = multi_hit.get("max", 1)
			if max_hits > 1:
				hits = random.randint(min_hits, max_hits)

		total_damage = 0
		first_tm, first_crit = 1.0, False

		for i in range(hits):
			dmg, tm, crit = await self._calc_damage(user, target, md, effect_data)
			if i == 0:
				first_tm, first_crit = tm, crit
			
			if tm == 0.0:
				lines.append(f"🚫 {user.display_name} usou **{md.name}**!")
				lines.append(f"   └─ Não teve efeito em {target.display_name}...")
				return lines

			if target.status["name"] == "freeze" and md.type_name.lower() == "fire" and dmg > 0:
				target.status = {"name": None, "counter": 0}
				lines.append(f"🔥 O calor derreteu o gelo! {target.display_name} descongelou!")

			actual = target.take_damage(dmg)
			total_damage += actual

			if target.fainted:
				break

		main_line = f"⚔️ {user.display_name} usou **{md.name}**!"
		
		if total_damage > 0:
			main_line += f" Causou **{total_damage} de dano**!"
		
		lines.append(main_line)
		
		details = []
		if hits > 1:
			details.append(f"🎯 Acertou {hits}x")
		if first_crit:
			details.append(f"💥 CRÍTICO")
		if first_tm > 1.0:
			details.append(f"✨ Super eficaz")
		elif 0 < first_tm < 1.0:
			details.append(f"💢 Não muito eficaz")
		
		if details:
			lines.append("   └─ " + " • ".join(details))

		if target.fainted:
			lines.append(f"💀 **{target.display_name} foi derrotado!**")

		if effect_data.get("recoil"):
			lines.extend(self._apply_recoil(user, effect_data["recoil"], total_damage))

		if effect_data.get("drain"):
			lines.extend(self._apply_drain(user, effect_data["drain"], total_damage))

		for effect in effect_data.get("effects", []):
			effect_lines = self._apply_effect(user, target, effect, total_damage)
			if effect_lines:
				lines.extend(effect_lines)

		return lines

	async def _apply_status_move(self, user: BattlePokemon, target: BattlePokemon, md: MoveData, effect_data: Dict[str, Any]) -> List[str]:
		lines = [f"✨ {user.display_name} usou **{md.name}**!"]
		changed = False

		effects = effect_data.get("effects", [])
		
		if effects:
			for effect in effects:
				result = self._apply_effect(user, target, effect, 0)
				if result:
					changed = True
					lines.extend(result)
		elif md.stat_changes:
			for stat, delta, to_self in md.stat_changes:
				tgt = user if to_self else target
				result = self._apply_stat_change(tgt, stat, delta)
				if result:
					changed = True
					lines.append(result)

		if not changed:
			lines.append("   └─ 💢 Mas não surtiu efeito...")

		return lines

	def _end_of_turn(self) -> List[str]:
		lines = []
		for p, prefix in [(self.player_active, "🔵"), (self.wild, "🔴")]:
			if p.fainted:
				continue
			
			status = p.status["name"]
			if status == "burn":
				d = max(1, p.stats["hp"] // 16)
				actual = p.take_damage(d)
				lines.append(f"🔥 {prefix} {p.display_name} sofreu {actual} de dano da queimadura")
			elif status == "poison":
				d = max(1, p.stats["hp"] // 8)
				actual = p.take_damage(d)
				lines.append(f"☠️ {prefix} {p.display_name} sofreu {actual} de dano do envenenamento")
			elif status == "toxic":
				p.status["counter"] += 1
				d = max(1, (p.stats["hp"] // 16) * p.status["counter"])
				actual = p.take_damage(d)
				lines.append(f"☠️☠️ {prefix} {p.display_name} sofreu {actual} de dano do envenenamento grave (nível {p.status['counter']})")
			
			if p.fainted:
				lines.append(f"💀 **{p.display_name} foi derrotado pelo status!**")

		return lines

	def _enemy_pick(self) -> str:
		opts = [m for m in self.wild.moves if int(m.get("pp", 0)) > 0]
		return str(random.choice(opts)["id"]) if opts else "__struggle__"

	async def _act(self, player_side: bool, mv_id: str, md: MoveData) -> List[str]:
		user = self.player_active if player_side else self.wild
		target = self.wild if player_side else self.player_active
		
		block, pre = self._pre_action(user)
		if block:
			return pre
		
		conf_block, conf = self._confusion(user)
		if conf_block:
			return pre + conf

		return pre + conf + await self._use_move(user, target, md, mv_id)

	async def handle_player_move(self, move_id: str):
		async with self.lock:
			if self.ended:
				return

			self.lines = []

			pmd = await self._fetch_move(move_id)
			eid = self._enemy_pick()
			
			if eid != "__struggle__":
				emd = await self._fetch_move(eid)
			else:
				emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])

			ps = self.player_active.eff_stat("speed")
			es = self.wild.eff_stat("speed")
			
			if pmd.priority != emd.priority:
				order = ["player", "enemy"] if pmd.priority > emd.priority else ["enemy", "player"]
			elif ps != es:
				order = ["player", "enemy"] if ps > es else ["enemy", "player"]
			else:
				order = random.choice([["player", "enemy"], ["enemy", "player"]])

			for side in order:
				if self.player_active.fainted or self.wild.fainted:
					break

				if side == "player":
					self.lines.extend(await self._act(True, move_id, pmd))
					if self.wild.fainted:
						await self._on_win()
						await self.refresh()
						return
				else:
					if self.lines:
						self.lines.append("")
					self.lines.extend(await self._act(False, eid, emd))
					if self.player_active.fainted:
						await self._on_faint()
						await self.refresh()
						return

			end_turn = self._end_of_turn()
			if end_turn:
				self.lines.append("")
				self.lines.extend(end_turn)

			if self.wild.fainted:
				await self._on_win()
			elif self.player_active.fainted:
				await self._on_faint()

			if not self.ended:
				self.turn += 1

			await self.refresh()

	async def switch_active(self, new_index: int, consume_turn: bool = True):
		async with self.lock:
			if self.ended or new_index == self.active_player_idx:
				return
			if not (0 <= new_index < len(self.player_team)) or self.player_team[new_index].fainted:
				return

			self.lines = []
			old_name = self.player_active.display_name
			self.active_player_idx = new_index
			self.must_redraw_image = True
			
			self.lines.extend([
				f"🔄 {old_name} voltou!",
				f"Vamos lá, {self.player_active.display_name}!"
			])

			if consume_turn:
				self.lines.append("")
				eid = self._enemy_pick()
				if eid != "__struggle__":
					emd = await self._fetch_move(eid)
				else:
					emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])
				
				self.lines.extend(await self._act(False, eid, emd))
				
				end_turn = self._end_of_turn()
				if end_turn:
					self.lines.append("")
					self.lines.extend(end_turn)

				if self.player_active.fainted:
					await self._on_faint()

				if not self.ended:
					self.turn += 1

			await self.refresh()

	def _gen3_capture(self) -> Tuple[bool, int]:
		max_hp = self.wild.stats["hp"]
		cur_hp = max(1, self.wild.current_hp)
		cr = int(getattr(self.wild.species_data, "capture_rate", 45) or 45)
		ball = 1.0
		status = self.wild.status["name"]
		status_bonus = 2.5 if status in {"sleep", "freeze"} else (1.5 if status in {"paralysis", "poison", "burn", "toxic"} else 1.0)
		a = int(((3 * max_hp - 2 * cur_hp) * cr * ball * status_bonus) / (3 * max_hp))
		
		if a >= 255:
			return True, 4
		if a <= 0:
			return False, 0

		r = 65536
		b = int(1048560 / math.sqrt(math.sqrt((16711680 / a))))
		shakes = 0

		for _ in range(4):
			if random.randint(0, r - 1) < b:
				shakes += 1
			else:
				break

		return shakes == 4, shakes

	async def attempt_capture(self) -> bool:
		if self.player_active.fainted:
			self.lines = ["Seu Pokémon está desmaiado! Troque antes de capturar."]
			if self.actions_view:
				self.actions_view.force_switch_mode = True
			await self.refresh()
			return False

		success, shakes = self._gen3_capture()

		if success:
			xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
			pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
			pm.repo.tk.add_pokemon(
				owner_id=self.user_id,
				species_id=self.wild_raw["species_id"],
				ivs=self.wild_raw["ivs"],
				nature=self.wild_raw["nature"],
				ability=self.wild_raw["ability"],
				gender=self.wild_raw["gender"],
				shiny=self.wild_raw.get("is_shiny", False),
				level=self.wild_raw["level"],
				is_legendary=self.wild_raw["is_legendary"],
				is_mythical=self.wild_raw["is_mythical"],
				types=self.wild_raw["types"],
				region=self.wild_raw["region"],
				stats=self.wild_raw["stats"],
				exp=self.wild_raw.get("exp", 0),
				moves=self.wild_raw.get("moves", []),
				nickname=self.wild_raw.get("nickname"),
				name=self.wild_raw.get("name"),
				current_hp=self.wild_raw.get("current_hp"),
				on_party=pm.repo.tk.can_add_to_party(self.user_id)
			)
			self.ended = True
			self.lines = [
				f"**CAPTURA BEM-SUCEDIDA!**",
				f"{self.wild.display_name} foi capturado!",
				f"{self.player_active.display_name} ganhou {xp} XP!"
			]
			if self.actions_view:
				self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send(
				f"**Parabéns!** Você capturou **{self.wild.display_name}**!\n⭐ {self.player_active.display_name} recebeu **{xp} XP**."
			)
			return True
		else:
			self.lines = []
			shake_text = f"{'<:PokeBall:1345558169090265151> ' * shakes}" if shakes > 0 else ""
			self.lines.append(f"💢 {shake_text}Pokébola balançou {shakes}x... {self.wild.display_name} escapou!")
			self.lines.append("")
			
			eid = self._enemy_pick()
			if eid != "__struggle__":
				emd = await self._fetch_move(eid)
			else:
				emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])
			
			self.lines.extend(await self._act(False, eid, emd))
			
			end_turn = self._end_of_turn()
			if end_turn:
				self.lines.append("")
				self.lines.extend(end_turn)

			if self.player_active.fainted:
				await self._on_faint()

			if not self.ended:
				self.turn += 1

			await self.refresh()
			return False

	async def _on_win(self):
		xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
		pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
		self.ended = True
		self.lines.extend([
			"",
			f"**VITÓRIA!**",
			f"{self.player_active.display_name} ganhou {xp} XP!"
		])
		if self.actions_view:
			self.actions_view.disable_all()
		await self.refresh()
		await self.interaction.channel.send(
			f"**VITÓRIA!** Você derrotou {self.wild.display_name}!\n⭐ {self.player_active.display_name} recebeu **{xp} XP**."
		)

	async def _on_faint(self):
		alive = [p for p in self.player_team if not p.fainted]
		
		if not alive:
			self.ended = True
			self.lines.extend([
				"",
				f"**DERROTA...**",
				f"Todos os seus Pokémon foram derrotados!"
			])
			if self.actions_view:
				self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send("💀 **Você foi derrotado...** Todos os seus Pokémon desmaiaram.")
			return

		self.lines.extend([
			"",
			f"Escolha outro Pokémon para continuar!"
		])
		if self.actions_view:
			self.actions_view.force_switch_mode = True

class WildBattleView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout=180.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		self.user_id = battle.user_id
		self.force_switch_mode = False

	def disable_all(self):
		for item in self.children:
			item.disabled = True

	@discord.ui.button(style=discord.ButtonStyle.primary, label="Lutar", emoji="⚔️")
	async def fight(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id:
			return await i.response.send_message("Esta não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode:
			return await i.response.edit_message(view=SwitchView(self.battle, force_only=True))
		await i.response.edit_message(view=MovesView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.primary, label="Trocar", emoji="🔄")
	async def switch(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id:
			return await i.response.send_message("Esta não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		await i.response.edit_message(view=SwitchView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
	async def capture(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id:
			return await i.response.send_message("Esta não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode or self.battle.player_active.fainted:
			return await i.response.send_message("Troque de Pokémon antes de tentar capturar!", ephemeral=True)
		await i.response.defer()
		await self.battle.attempt_capture()
