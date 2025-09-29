import discord
import aiopoke
import random
import asyncio
from __main__ import pm
from typing import List, Dict, Any, Optional
from utils.canvas import compose_battle_async
from pokemon_sdk.calculations import calculate_stats
from utils.preloaded import preloaded_textures
from utils.pokemon_emojis import get_app_emoji

TYPE_CHART = {
	"normal":   {"super": set(),                              "not": {"rock","steel"},                "immune": {"ghost"}},
	"fire":     {"super": {"grass","ice","bug","steel"},      "not": {"fire","water","rock","dragon"},"immune": set()},
	"water":    {"super": {"fire","ground","rock"},           "not": {"water","grass","dragon"},      "immune": set()},
	"grass":    {"super": {"water","ground","rock"},          "not": {"fire","grass","poison","flying","bug","dragon","steel"}, "immune": set()},
	"electric": {"super": {"water","flying"},                 "not": {"electric","grass","dragon"},   "immune": {"ground"}},
	"ice":      {"super": {"grass","ground","flying","dragon"},"not": {"fire","water","ice","steel"},"immune": set()},
	"fighting": {"super": {"normal","ice","rock","dark","steel"}, "not": {"poison","flying","psychic","bug","fairy"}, "immune": {"ghost"}},
	"poison":   {"super": {"grass","fairy"},                  "not": {"poison","ground","rock","ghost"}, "immune": {"steel"}},
	"ground":   {"super": {"fire","electric","poison","rock","steel"}, "not": {"grass","bug"}, "immune": {"flying"}},
	"flying":   {"super": {"grass","fighting","bug"},         "not": {"electric","rock","steel"},     "immune": set()},
	"psychic":  {"super": {"fighting","poison"},              "not": {"psychic","steel"},             "immune": {"dark"}},
	"bug":      {"super": {"grass","psychic","dark"},         "not": {"fire","fighting","poison","flying","ghost","steel","fairy"}, "immune": set()},
	"rock":     {"super": {"fire","ice","flying","bug"},      "not": {"fighting","ground","steel"},   "immune": set()},
	"ghost":    {"super": {"psychic","ghost"},                "not": {"dark"},                        "immune": {"normal"}},
	"dragon":   {"super": {"dragon"},                         "not": {"steel"},                       "immune": {"fairy"}},
	"dark":     {"super": {"psychic","ghost"},                "not": {"fighting","dark","fairy"},     "immune": set()},
	"steel":    {"super": {"ice","rock","fairy"},             "not": {"fire","water","electric","steel"}, "immune": set()},
	"fairy":    {"super": {"fighting","dragon","dark"},       "not": {"fire","poison","steel"},       "immune": set()},
}

def _obj(**kw):
	return type("O", (), kw)()

def _type_multiplier(atk_type: str, defender_types: List[str]) -> float:
	atk = atk_type.lower()
	if atk not in TYPE_CHART:
		return 1.0
	m = 1.0
	for d in defender_types:
		d = d.lower()
		if d in TYPE_CHART[atk]["immune"]:
			m *= 0.0
		elif d in TYPE_CHART[atk]["super"]:
			m *= 2.0
		elif d in TYPE_CHART[atk]["not"]:
			m *= 0.5
	return m

def _stage_multiplier(stage: int) -> float:
	if stage >= 0:
		return (2 + stage) / 2
	return 2 / (2 - stage)

STAT_ALIASES = {
	"hp": ["hp"],
	"atk": ["atk","attack"],
	"def": ["def","defense"],
	"sp_atk": ["sp_atk","spa","special-attack","spatk","sp_att","spatt"],
	"sp_def": ["sp_def","spd","special-defense","spdef","sp_defense"],
	"speed": ["speed","spe"]
}

def _get_stat_value(stats: Dict[str, int], canonical: str) -> int:
	for name in STAT_ALIASES.get(canonical, []):
		if name in stats:
			return int(stats[name])
	if canonical in stats:
		return int(stats[canonical])
	return 1

def _apply_stage(stat_base: int, stage: int) -> int:
	return max(1, int(stat_base * _stage_multiplier(stage)))

def _types_of(poke: "BattlePokemon") -> List[str]:
	try:
		return [t.type.name.lower() for t in poke.pokeapi_data.types]
	except Exception:
		return []

class _Meta:
	def __init__(self):
		self.ailment = _obj(name="none")
		self.ailment_chance = 0
		self.flinch_chance = 0
		self.drain = 0
		self.recoil = 0
		self.min_hits = 1
		self.max_hits = 1
		self.healing = 0

class _Struggle:
	power = 50
	accuracy = None
	priority = 0
	damage_class = _obj(name="physical")
	type = _obj(name="normal")
	name = "Struggle"
	stat_changes = []
	effect_chance = None
	meta = _Meta()

class _FakeMove:
	def __init__(self, name="Desconhecido", power=0, accuracy=100, priority=0, dmg="status", type_name="normal"):
		self.name = name
		self.power = power
		self.accuracy = accuracy
		self.priority = priority
		self.damage_class = _obj(name=dmg)
		self.type = _obj(name=type_name)
		self.stat_changes = []
		self.effect_chance = None
		self.meta = _Meta()

class BattlePokemon:
	def __init__(self, raw: Dict[str, Any], pokeapi_data: aiopoke.Pokemon):
		self.raw = raw
		self.species_id = raw["species_id"]
		self.name = raw.get("name")
		self.nickname = raw.get("nickname")
		self.level = raw["level"]
		base_stats = pm.service.get_base_stats(pokeapi_data)
		self.stats = calculate_stats(base_stats, raw["ivs"], raw["evs"], raw["level"], raw["nature"])
		self.current_hp = raw.get("current_hp") or self.stats["hp"]
		self.moves = raw.get("moves", [])
		self.pokeapi_data = pokeapi_data
		self.is_shiny = raw.get("is_shiny", False)
		self.stages = {"atk": 0, "def": 0, "sp_atk": 0, "sp_def": 0, "speed": 0}
		self.status = {"name": None, "counter": 0}
		self.volatile = {"flinch": False, "confuse": 0}
		if self.is_shiny:
			self.sprites = {"front": pokeapi_data.sprites.front_shiny, "back": pokeapi_data.sprites.back_shiny}
		else:
			self.sprites = {"front": pokeapi_data.sprites.front_default, "back": pokeapi_data.sprites.back_default}
		if not self.moves:
			self.moves = [{"id": "tackle", "pp": 35, "pp_max": 35}]

	@property
	def fainted(self) -> bool:
		return self.current_hp <= 0

	def eff_stat(self, key: str) -> int:
		base = _get_stat_value(self.stats, key)
		val = _apply_stage(base, self.stages[key])
		if key == "speed" and self.status["name"] == "paralysis":
			val = int(val * 0.5)
		return max(1, val)

	def dec_pp(self, move_id: str):
		for m in self.moves:
			if str(m["id"]).lower() == str(move_id).lower():
				if "pp" in m:
					m["pp"] = max(0, int(m["pp"]) - 1)
				return

	def get_pp(self, move_id: str) -> Optional[int]:
		for m in self.moves:
			if str(m["id"]).lower() == str(move_id).lower():
				return int(m.get("pp", 0))
		return None

	def list_moves(self) -> List[Dict[str, Any]]:
		out = []
		for m in self.moves:
			out.append({"id": m["id"], "pp": int(m.get("pp", 0)), "pp_max": int(m.get("pp_max", m.get("pp", 0)))})
		return out

	def set_status(self, name: str, turns: Optional[int] = None) -> bool:
		if self.status["name"] is not None:
			return False
		if name in {"burn","poison","paralysis"}:
			self.status = {"name": name, "counter": 0}
		elif name == "sleep":
			self.status = {"name": "sleep", "counter": turns or random.randint(1, 3)}
		elif name == "freeze":
			self.status = {"name": "freeze", "counter": 0}
		else:
			return False
		return True

	def status_tag(self) -> str:
		n = self.status["name"]
		if n == "burn": return " [BRN]"
		if n == "poison": return " [PSN]"
		if n == "paralysis": return " [PAR]"
		if n == "sleep": return " [SLP]"
		if n == "freeze": return " [FRZ]"
		return ""

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

	@property
	def player_active(self) -> BattlePokemon:
		return self.player_team[self.active_player_idx]

	async def setup(self):
		pokeapi_wild: aiopoke.Pokemon = await pm.service.get_pokemon(self.wild_raw["species_id"])
		self.wild = BattlePokemon(self.wild_raw, pokeapi_wild)
		for p in self.player_party_raw:
			api_p = await pm.service.get_pokemon(p["species_id"])
			self.player_team.append(BattlePokemon(p, api_p))

	async def _compose_image(self):
		player_sprite = None
		if self.player_active.sprites["back"]:
			player_sprite = await self.player_active.sprites["back"].read()
		enemy_sprite = None
		if self.wild and self.wild.sprites["front"]:
			enemy_sprite = await self.wild.sprites["front"].read()
		background = preloaded_textures["battle"]
		buf = await compose_battle_async(player_sprite, enemy_sprite, background)
		return discord.File(buf, filename="battle.png")

	def _hp_line(self, p: BattlePokemon, is_enemy=False) -> str:
		emoji = get_app_emoji(f"p_{p.species_id}")
		return f"Lv{p.level} {emoji} {p.name.title()}{p.status_tag()} (HP {max(0, p.current_hp)}/{p.stats['hp']}) {'*Wild*' if is_enemy else ''}"

	def _desc(self) -> str:
		top = self._hp_line(self.player_active, is_enemy=False)
		bot = self._hp_line(self.wild, is_enemy=True)
		lines = [top, "VS", bot]
		if self.lines:
			lines.append("")
			lines.extend(self.lines)
		return "\n".join(lines)

	def _embed(self) -> discord.Embed:
		embed = discord.Embed(title=f"Luta - Turno {self.turn}", description=self._desc(), color=discord.Color.green())
		embed.set_image(url="attachment://battle.png")
		return embed

	async def start(self):
		self.actions_view = WildBattleView(self)
		self.lines = ["A batalha começou!"]
		file = await self._compose_image()
		embed = self._embed()
		self.message = await self.interaction.channel.send(embed=embed, file=file, view=self.actions_view)
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

	async def _get_move(self, move_id: str):
		key = str(move_id).strip().lower().replace(" ", "-")
		try:
			return await pm.service.get_move(key)
		except Exception:
			try:
				if key.isdigit():
					return await pm.service.get_move(int(key))
			except Exception:
				return None
		return None

	def _pre_action_block(self, user: BattlePokemon) -> List[str] | None:
		out = []
		if user.volatile["flinch"]:
			user.volatile["flinch"] = False
			out.append(f"{user.name.title()} hesitou e não conseguiu agir!")
			return out
		if user.status["name"] == "sleep":
			user.status["counter"] = max(0, user.status["counter"] - 1)
			if user.status["counter"] > 0:
				out.append(f"{user.name.title()} está dormindo...")
				return out
			else:
				user.status = {"name": None, "counter": 0}
				out.append(f"{user.name.title()} acordou!")
		if user.status["name"] == "freeze":
			if random.random() < 0.2:
				user.status = {"name": None, "counter": 0}
				out.append(f"{user.name.title()} descongelou!")
			else:
				out.append(f"{user.name.title()} está congelado e não pode agir!")
				return out
		if user.status["name"] == "paralysis":
			if random.random() < 0.25:
				out.append(f"{user.name.title()} está paralisado! Não se moveu!")
				return out
		return out if out else None

	def _confusion_check(self, user: BattlePokemon) -> List[str] | None:
		if user.volatile["confuse"] <= 0:
			return None
		user.volatile["confuse"] -= 1
		if random.random() < 0.33:
			atk_stat = user.eff_stat("atk")
			def_stat = user.eff_stat("def")
			level = user.level
			base = (((2 * level / 5) + 2) * 40 * (atk_stat / max(1, def_stat))) / 50 + 2
			rand = random.uniform(0.9, 1.0)
			damage = max(1, int(base * rand))
			user.current_hp = max(0, user.current_hp - damage)
			return [f"{user.name.title()} está confuso! Atingiu a si mesmo e perdeu {damage} HP."]
		return [f"{user.name.title()} está confuso, mas conseguiu agir!"]

	def _secondary_effects(self, user: BattlePokemon, target: BattlePokemon, move, total_damage: int) -> List[str]:
		out = []
		meta = getattr(move, "meta", None)
		if meta:
			fc = int(getattr(meta, "flinch_chance", 0) or 0)
			if fc > 0 and random.randint(1, 100) <= fc:
				target.volatile["flinch"] = True
				out.append("O alvo recuou!")
			drain = int(getattr(meta, "drain", 0) or 0)
			if drain > 0 and total_damage > 0:
				heal = max(1, int(total_damage * drain / 100))
				user.current_hp = min(user.stats["hp"], user.current_hp + heal)
				out.append(f"{user.name.title()} recuperou {heal} HP!")
			if drain < 0 and total_damage > 0:
				rc = max(1, int(total_damage * abs(drain) / 100))
				user.current_hp = max(0, user.current_hp - rc)
				out.append(f"{user.name.title()} sofreu {rc} de recuo!")
			heal_pct = int(getattr(meta, "healing", 0) or 0)
			if heal_pct > 0 and getattr(move.damage_class, "name", "physical") == "status":
				heal = max(1, int(user.stats["hp"] * heal_pct / 100))
				user.current_hp = min(user.stats["hp"], user.current_hp + heal)
				out.append(f"{user.name.title()} curou {heal} HP!")
			ail = getattr(meta, "ailment", None)
			if ail:
				an = getattr(ail, "name", "none")
				if an not in {"none","unknown"}:
					ch = int(getattr(meta, "ailment_chance", 0) or 0) or int(getattr(move, "effect_chance", 0) or 0)
					if ch <= 0 or random.randint(1, 100) <= ch:
						applied = False
						tt = _types_of(target)
						if an == "poison":
							if "steel" in tt or "poison" in tt:
								applied = False
							else:
								applied = target.set_status("poison")
						elif an == "burn":
							if "fire" in tt:
								applied = False
							else:
								applied = target.set_status("burn")
						elif an == "paralysis":
							if ("electric" in tt and getattr(move.type, "name", "").lower() == "electric"):
								applied = False
							else:
								applied = target.set_status("paralysis")
						elif an == "sleep":
							applied = target.set_status("sleep", turns=random.randint(1,3))
						elif an == "freeze":
							if "ice" in tt:
								applied = False
							else:
								applied = target.set_status("freeze")
						elif an == "confusion":
							target.volatile["confuse"] = max(target.volatile["confuse"], random.randint(2, 4))
							applied = True
						if applied:
							txt = {"burn":"foi queimado!","poison":"foi envenenado!","paralysis":"ficou paralisado!","sleep":"adormeceu!","freeze":"foi congelado!","confusion":"ficou confuso!"}.get(an, "sofreu um efeito!")
							out.append(f"O alvo {txt}")
		return out

	async def _apply_status_moves(self, user: BattlePokemon, target: BattlePokemon, move) -> str:
		txts = []
		sc = getattr(move, "stat_changes", []) or []
		eff_chance = getattr(move, "effect_chance", None)
		if sc:
			if eff_chance is None or random.randint(1, 100) <= int(eff_chance):
				for s in sc:
					raw_name = s.stat.name
					delta = int(s.change)
					canonical = {"attack":"atk","defense":"def","special-attack":"sp_atk","special-defense":"sp_def","speed":"speed"}.get(raw_name)
					if not canonical:
						continue
					tgt = user if delta > 0 else target
					tgt.stages[canonical] = max(-6, min(6, tgt.stages[canonical] + delta))
					alvo = "Você" if tgt is user else "O alvo"
					what = {"atk":"Ataque","def":"Defesa","sp_atk":"Ataque Especial","sp_def":"Defesa Especial","speed":"Velocidade"}[canonical]
					txts.append(f"{alvo}: {what} {'+' if delta>0 else ''}{delta} ({tgt.stages[canonical]})")
		sec = self._secondary_effects(user, target, move, 0)
		txts.extend(sec)
		return " ".join(txts) if txts else "Nada aconteceu."

	async def _calc_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move):
		power = int(getattr(move, "power", 0) or 0)
		if power <= 0:
			return 0, 1.0, False
		dmg_class = getattr(move.damage_class, "name", "physical")
		if dmg_class == "special":
			atk_stat = attacker.eff_stat("sp_atk")
			def_stat = defender.eff_stat("sp_def")
		else:
			atk_stat = attacker.eff_stat("atk")
			if attacker.status["name"] == "burn":
				atk_stat = int(atk_stat * 0.5)
			def_stat = defender.eff_stat("def")
		level = attacker.level
		base = (((2 * level / 5) + 2) * power * (atk_stat / max(1, def_stat))) / 50 + 2
		stab = 1.5 if getattr(move.type, "name", "").lower() in _types_of(attacker) else 1.0
		def_types = _types_of(defender)
		type_mult = _type_multiplier(getattr(move.type, "name", "normal"), def_types)
		if type_mult == 0.0:
			return 0, 0.0, False
		rand = random.uniform(0.9, 1.0)
		crit = random.random() < 0.0625
		crit_mult = 1.5 if crit else 1.0
		damage = int(base * stab * type_mult * rand * crit_mult)
		return max(1, damage), type_mult, crit

	async def _use_move(self, user: BattlePokemon, target: BattlePokemon, move, move_id_for_pp: Optional[str]) -> List[str]:
		if move is None:
			move = _FakeMove(name=(move_id_for_pp or "Desconhecido").replace("-", " ").title())
		lines = []
		mname = getattr(move, "name", "Golpe").replace("-", " ").title()
		if move_id_for_pp and move_id_for_pp != "__struggle__":
			pp = user.get_pp(move_id_for_pp)
			if pp is not None and pp <= 0:
				return [f"{user.name.title()} tentou usar {mname}, mas não tem PP!"]
			user.dec_pp(move_id_for_pp)
		acc = getattr(move, "accuracy", None)
		hit = True if (acc is None or int(acc) <= 0) else (random.randint(1, 100) <= int(acc))
		if not hit:
			return [f"{user.name.title()} usou {mname}, mas errou!"]
		if getattr(move.damage_class, "name", "physical") == "status":
			txt = await self._apply_status_moves(user, target, move)
			return [f"{user.name.title()} usou {mname}! {txt}"]
		meta = getattr(move, "meta", None)
		min_hits = 1
		max_hits = 1
		if meta:
			min_hits = int(getattr(meta, "min_hits", 1) or 1)
			max_hits = int(getattr(meta, "max_hits", 1) or 1)
		hits = 1 if max_hits <= 1 else random.randint(min_hits, max_hits)
		total_damage = 0
		first_eff = 1.0
		first_crit = False
		for i in range(hits):
			dmg, eff, crit = await self._calc_damage(user, target, move)
			if i == 0:
				first_eff = eff
				first_crit = crit
			if eff == 0.0:
				lines.append(f"{user.name.title()} usou {mname}! Não teve efeito.")
				return lines
			if target.status["name"] == "freeze" and getattr(move.type, "name", "").lower() == "fire" and dmg > 0:
				target.status = {"name": None, "counter": 0}
				lines.append(f"{target.name.title()} descongelou!")
			target.current_hp = max(0, target.current_hp - dmg)
			total_damage += dmg
			if target.fainted:
				break
		txt = f"{user.name.title()} usou {mname}! Causou {total_damage} de dano."
		if hits > 1: txt += f" Acertou {hits} vezes."
		if first_crit: txt += " Acerto crítico!"
		if first_eff > 1.0: txt += " É super eficaz!"
		if 0 < first_eff < 1.0: txt += " Não foi muito eficaz..."
		lines.append(txt)
		sec = self._secondary_effects(user, target, move, total_damage)
		if sec: lines.extend(sec)
		return lines

	def _end_of_turn(self) -> List[str]:
		lines = []
		for p, who in [(self.player_active, "Seu"), (self.wild, "O selvagem")]:
			if p.fainted: continue
			if p.status["name"] == "burn":
				d = max(1, p.stats["hp"] // 16)
				p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano da queimadura.")
			elif p.status["name"] == "poison":
				d = max(1, p.stats["hp"] // 8)
				p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano do veneno.")
		return lines

	def _enemy_choose_move_id(self) -> str:
		moves = [m for m in self.wild.list_moves() if int(m.get("pp", 0)) > 0]
		if moves:
			return str(random.choice(moves)["id"])
		return "__struggle__"

	async def _act(self, user_is_player: bool, chosen_move_id: str, chosen_move_obj) -> List[str]:
		user = self.player_active if user_is_player else self.wild
		target = self.wild if user_is_player else self.player_active
		pre = self._pre_action_block(user) or []
		if pre and any("não pode agir" in x or "dormindo" in x or "paralisado" in x or "hesitou" in x for x in pre):
			return pre
		conf = self._confusion_check(user)
		if conf and any("atingiu a si mesmo" in x.lower() for x in conf):
			return pre + conf
		lines = await self._use_move(user, target, chosen_move_obj, chosen_move_id)
		return pre + (conf or []) + lines

	async def handle_player_move(self, move_id: str):
		async with self.lock:
			if self.ended:
				return
			player_move = await self._get_move(move_id)
			enemy_move_id = self._enemy_choose_move_id()
			enemy_move = _Struggle() if enemy_move_id == "__struggle__" else (await self._get_move(enemy_move_id) or _FakeMove(name=enemy_move_id))
			p_prio = int(getattr(player_move, "priority", 0) or 0) if player_move else 0
			e_prio = int(getattr(enemy_move, "priority", 0) or 0)
			ps = self.player_active.eff_stat("speed")
			es = self.wild.eff_stat("speed")
			if p_prio > e_prio:
				order = ["player","enemy"]
			elif e_prio > p_prio:
				order = ["enemy","player"]
			else:
				if ps > es: order = ["player","enemy"]
				elif es > ps: order = ["enemy","player"]
				else: order = random.choice([["player","enemy"],["enemy","player"]])
			lines = []
			for side in order:
				if side == "player":
					if self.player_active.fainted or self.wild.fainted: continue
					lines += await self._act(True, move_id, player_move or _FakeMove(name=move_id))
					if self.wild.fainted:
						await self._on_enemy_defeated()
						self.lines = lines
						await self.refresh()
						return
				else:
					if self.player_active.fainted or self.wild.fainted: continue
					lines += await self._act(False, enemy_move_id, enemy_move)
					if self.player_active.fainted:
						await self._on_player_fainted()
						self.lines = lines
						await self.refresh()
						return
			lines += self._end_of_turn()
			if self.player_active.fainted:
				await self._on_player_fainted()
			if self.wild.fainted:
				await self._on_enemy_defeated()
			if not self.ended:
				self.turn += 1
			self.lines = lines
			await self.refresh()

	async def switch_active(self, new_index: int, consume_turn: bool = True):
		async with self.lock:
			if self.ended: return
			if new_index == self.active_player_idx: return
			if not (0 <= new_index < len(self.player_team)): return
			if self.player_team[new_index].fainted: return
			self.active_player_idx = new_index
			self.must_redraw_image = True
			lines = [f"Você trocou para {self.player_active.name.title()}!"]
			if consume_turn:
				enemy_move_id = self._enemy_choose_move_id()
				enemy_move = _Struggle() if enemy_move_id == "__struggle__" else (await self._get_move(enemy_move_id) or _FakeMove(name=enemy_move_id))
				lines += await self._act(False, enemy_move_id, enemy_move)
				lines += self._end_of_turn()
				if self.player_active.fainted:
					await self._on_player_fainted()
				if not self.ended:
					self.turn += 1
			self.lines = lines
			await self.refresh()

	async def attempt_capture(self) -> bool:
		if self.player_active.fainted:
			self.lines = ["Seu Pokémon desmaiou! Troque antes de tentar capturar."]
			if self.actions_view:
				self.actions_view.force_switch_mode = True
			await self.refresh()
			return False
		level = self.wild_raw.get("level", 10)
		base_chance = max(5, 50 - (level // 2))
		if self.wild_raw.get("is_shiny"):
			base_chance += 10
		if random.randint(1, 100) <= base_chance:
			xp_gain = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
			pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp_gain)
			pm.repo.tk.add_pokemon(
				owner_id=self.user_id,
				species_id=self.wild_raw["species_id"],
				ivs=self.wild_raw["ivs"],
				nature=self.wild_raw["nature"],
				ability=self.wild_raw["ability"],
				gender=self.wild_raw["gender"],
				shiny=self.wild_raw.get("is_shiny", False),
				level=self.wild_raw["level"],
				exp=self.wild_raw.get("exp", 0),
				moves=self.wild_raw.get("moves", []),
				nickname=self.wild_raw.get("nickname"),
				name=self.wild_raw.get("name"),
				current_hp=self.wild_raw.get("current_hp"),
				on_party=pm.repo.tk.can_add_to_party(self.user_id)
			)
			self.ended = True
			self.lines = [f"Captura bem-sucedida! {self.player_active.name.title()} ganhou {xp_gain} XP."]
			if self.actions_view:
				for item in self.actions_view.children:
					item.disabled = True
			await self.refresh()
			await self.interaction.channel.send(f"🎉 Capturou {self.wild_raw['name'].title()}! ⭐ {self.player_active.name.title()} recebeu {xp_gain} XP.")
			return True
		else:
			enemy_move_id = self._enemy_choose_move_id()
			enemy_move = _Struggle() if enemy_move_id == "__struggle__" else (await self._get_move(enemy_move_id) or _FakeMove(name=enemy_move_id))
			lines = ["A Pokébola balançou... e o Pokémon escapou!"]
			lines += await self._act(False, enemy_move_id, enemy_move)
			lines += self._end_of_turn()
			if self.player_active.fainted:
				await self._on_player_fainted()
			if not self.ended:
				self.turn += 1
			self.lines = lines
			await self.refresh()
			return False

	async def _on_enemy_defeated(self):
		xp_gain = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
		pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp_gain)
		self.ended = True
		self.lines = [f"O Pokémon selvagem caiu! {self.player_active.name.title()} ganhou {xp_gain} XP."]
		if self.actions_view:
			for item in self.actions_view.children:
				item.disabled = True
		await self.refresh()
		await self.interaction.channel.send(f"🏆 Vitória! ⭐ {self.player_active.name.title()} recebeu {xp_gain} XP.")

	async def _on_player_fainted(self):
		next_idx = None
		for i, p in enumerate(self.player_team):
			if not p.fainted:
				next_idx = i
				break
		if next_idx is None:
			self.ended = True
			self.lines = ["Seus Pokémon desmaiaram. Derrota!"]
			if self.actions_view:
				for item in self.actions_view.children:
					item.disabled = True
			await self.refresh()
			await self.interaction.channel.send("💀 Você foi derrotado...")
			return
		if self.actions_view:
			self.actions_view.force_switch_mode = True
		self.lines = ["Seu Pokémon desmaiou! Escolha outro."]

class MovesView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		for mv in battle.player_active.list_moves():
			label = str(mv["id"]).replace("-", " ").title()
			pp = mv["pp"]; pp_max = mv["pp_max"]
			btn = discord.ui.Button(style=discord.ButtonStyle.primary, label=f"{label} ({pp}/{pp_max})", disabled=(pp <= 0))
			btn.callback = self._make_move_callback(str(mv["id"]))
			self.add_item(btn)
		back_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
		async def go_back(_interaction: discord.Interaction):
			if str(_interaction.user.id) != str(self.battle.user_id):
				return await _interaction.response.send_message("Não é sua batalha!", ephemeral=True)
			await _interaction.response.edit_message(view=self.battle.actions_view)
		back_btn.callback = go_back
		self.add_item(back_btn)

	def _make_move_callback(self, move_id: str):
		async def _cb(interaction: discord.Interaction):
			if str(interaction.user.id) != str(self.battle.user_id):
				return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended:
				return await interaction.response.send_message("A batalha já terminou.", ephemeral=True)
			if getattr(self.battle.actions_view, "force_switch_mode", False):
				return await interaction.response.send_message("Seu Pokémon desmaiou! Troque antes.", ephemeral=True)
			await interaction.response.defer()
			await self.battle.handle_player_move(move_id)
		return _cb

class SwitchView(discord.ui.View):
	def __init__(self, battle: WildBattle, force_only: bool = False, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		self.force_only = force_only
		for i, p in enumerate(battle.player_team):
			label = f"{i+1}. {p.name.title()} (HP {max(0,p.current_hp)}/{p.stats['hp']})"
			disabled = p.fainted or (i == battle.active_player_idx)
			btn = discord.ui.Button(style=discord.ButtonStyle.success, label=label, disabled=disabled)
			btn.callback = self._make_switch_cb(i)
			self.add_item(btn)
		if not force_only:
			back_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
			async def go_back(_interaction: discord.Interaction):
				if str(_interaction.user.id) != str(self.battle.user_id):
					return await _interaction.response.send_message("Não é sua batalha!", ephemeral=True)
				await _interaction.response.edit_message(view=self.battle.actions_view)
			back_btn.callback = go_back
			self.add_item(back_btn)

	def _make_switch_cb(self, idx: int):
		async def _cb(interaction: discord.Interaction):
			if str(interaction.user.id) != str(self.battle.user_id):
				return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended:
				return await interaction.response.send_message("A batalha já terminou.", ephemeral=True)
			await interaction.response.defer()
			consume = not getattr(self.battle.actions_view, "force_switch_mode", False)
			await self.battle.switch_active(idx, consume_turn=consume)
			if getattr(self.battle.actions_view, "force_switch_mode", False):
				self.battle.actions_view.force_switch_mode = False
		return _cb

class WildBattleView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout=60.0) -> None:
		super().__init__(timeout=timeout)
		self.battle = battle
		self.user_id = battle.user_id
		self.force_switch_mode = False

	@discord.ui.button(style=discord.ButtonStyle.primary, emoji="⚔️", label="Lutar")
	async def fight_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != str(self.user_id):
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode:
			return await interaction.response.edit_message(view=SwitchView(self.battle, force_only=True))
		await interaction.response.edit_message(view=MovesView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.success, emoji="🔁", label="Trocar")
	async def switch_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != str(self.user_id):
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("A batalha já terminou.", ephemeral=True)
		await interaction.response.edit_message(view=SwitchView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
	async def capture_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != str(self.user_id):
			return await interaction.response.send_message("Esse Pokémon não é seu para capturar!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode or self.battle.player_active.fainted:
			return await interaction.response.send_message("Seu Pokémon desmaiou! Troque antes de capturar.", ephemeral=True)
		await interaction.response.defer()
		success = await self.battle.attempt_capture()
		if self.battle.ended:
			for item in self.children:
				item.disabled = True
		if success:
			await self.battle.interaction.channel.send("🎉 Captura realizada!")
