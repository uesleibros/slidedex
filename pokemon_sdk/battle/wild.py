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

STAT_ALIASES = {
	"hp": ["hp"],
	"atk": ["atk","attack"],
	"def": ["def","defense"],
	"sp_atk": ["sp_atk","spa","special-attack","spatk","sp_att","spatt"],
	"sp_def": ["sp_def","spd","special-defense","spdef","sp_defense"],
	"speed": ["speed","spe"]
}

def _obj(**kw): return type("O", (), kw)()
def _stage_multiplier(s: int) -> float: return (2+s)/2 if s>=0 else 2/(2-s)

def _get_stat(stats: Dict[str,int], key: str) -> int:
	for alias in STAT_ALIASES.get(key, []):
		if alias in stats: return int(stats[alias])
	return 1

def _apply_stage(base: int, stage: int) -> int:
	return max(1, int(base * _stage_multiplier(stage)))

def _types_of(poke: "BattlePokemon") -> List[str]:
	try: return [t.type.name.lower() for t in poke.pokeapi_data.types]
	except: return []

def _type_multiplier(atk_type: str, defender_types: List[str]) -> float:
	atk = (atk_type or "").lower()
	if atk not in TYPE_CHART: return 1.0
	m = 1.0
	for d in defender_types:
		d = d.lower()
		if d in TYPE_CHART[atk]["immune"]: return 0.0
		if d in TYPE_CHART[atk]["super"]: m *= 2.0
		elif d in TYPE_CHART[atk]["not"]: m *= 0.5
	return m

def _hp_bar(c: int, t: int, l: int = 10) -> str:
	p = max(0.0, min(1.0, c / t if t else 0))
	f = int(l*p)
	bar = "█"*f + "░"*(l-f)
	color = "🟢" if p > 0.5 else ("🟡" if p > 0.2 else "🔴")
	return f"{color} `[{bar}]`"

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
	name = "Struggle"
	damage_class = _obj(name="physical")
	type = _obj(name="normal")
	stat_changes = []
	effect_chance = None
	meta = _Meta()

class _FallbackMove:
	def __init__(self, name, power=0, acc=100, prio=0, dmg="status", type_name="normal", sc=None):
		self.name = name
		self.power = power
		self.accuracy = acc
		self.priority = prio
		self.damage_class = _obj(name=dmg)
		self.type = _obj(name=type_name)
		self.stat_changes = sc or []
		self.effect_chance = None
		self.meta = _Meta()

def _fallback_for(name: str) -> _FallbackMove:
	n = name.lower()
	if n in {"growl"}:
		return _FallbackMove(name="Growl", dmg="status", sc=[_obj(stat=_obj(name="attack"), change=-1)])
	if n in {"tail-whip","leer"}:
		return _FallbackMove(name=name.title().replace("-"," "), dmg="status", sc=[_obj(stat=_obj(name="defense"), change=-1)])
	if n in {"string-shot"}:
		return _FallbackMove(name="String Shot", dmg="status", sc=[_obj(stat=_obj(name="speed"), change=-2)])
	if n in {"tackle","scratch","pound"}:
		return _FallbackMove(name=name.title(), power=40, acc=100, prio=0, dmg="physical", type_name="normal")
	return _FallbackMove(name=name.title())

def _eff_damage_class(move) -> str:
	try:
		dc = getattr(move, "damage_class", None)
		if dc and getattr(dc, "name", None): return dc.name
	except: pass
	p = int(getattr(move, "power", 0) or 0)
	return "physical" if p > 0 else "status"

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
		self.stages = {"atk":0,"def":0,"sp_atk":0,"sp_def":0,"speed":0}
		self.status = {"name": None, "counter": 0}
		self.volatile = {"flinch": False, "confuse": 0}
		self.sprites = {
			"front": pokeapi_data.sprites.front_shiny if self.is_shiny else pokeapi_data.sprites.front_default,
			"back": pokeapi_data.sprites.back_shiny if self.is_shiny else pokeapi_data.sprites.back_default
		}

	@property
	def fainted(self) -> bool:
		return self.current_hp <= 0

	def eff_stat(self, key: str) -> int:
		val = _apply_stage(_get_stat(self.stats, key), self.stages[key])
		if key == "speed" and self.status["name"] == "paralysis": val = int(val * 0.5)
		return max(1, val)

	def dec_pp(self, move_id: str):
		for m in self.moves:
			if str(m["id"]).lower() == str(move_id).lower() and "pp" in m:
				m["pp"] = max(0, int(m["pp"]) - 1)
				return

	def get_pp(self, move_id: str) -> Optional[int]:
		for m in self.moves:
			if str(m["id"]).lower() == str(move_id).lower():
				return int(m.get("pp", 0))
		return None

	def set_status(self, name: str, turns: Optional[int] = None) -> bool:
		if self.status["name"]: return False
		self.status = {"name": name, "counter": (turns if turns is not None else (random.randint(1,3) if name=="sleep" else 0))}
		return True

	def status_tag(self) -> str:
		tags = {"burn":"BRN","poison":"PSN","paralysis":"PAR","sleep":"SLP","freeze":"FRZ"}
		return f" [{tags[self.status['name']]}]" if self.status["name"] in tags else ""

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
		self.move_cache: Dict[str, Any] = {}

	@property
	def player_active(self) -> BattlePokemon:
		return self.player_team[self.active_player_idx]

	async def setup(self):
		w_api = await pm.service.get_pokemon(self.wild_raw["species_id"])
		w_spec = await pm.service.get_species(self.wild_raw["species_id"])
		self.wild = BattlePokemon(self.wild_raw, w_api, w_spec)
		for p in self.player_party_raw:
			api_p = await pm.service.get_pokemon(p["species_id"])
			spec_p = await pm.service.get_species(p["species_id"])
			self.player_team.append(BattlePokemon(p, api_p, spec_p))

	async def _compose_image(self):
		pb = await self.player_active.sprites["back"].read() if self.player_active.sprites["back"] else None
		ef = await self.wild.sprites["front"].read() if self.wild.sprites["front"] else None
		buf = await compose_battle_async(pb, ef, preloaded_textures["battle"])
		return discord.File(buf, filename="battle.png")

	def _hp_line(self, p: BattlePokemon) -> str:
		emoji = get_app_emoji(f"p_{p.species_id}")
		bar = _hp_bar(p.current_hp, p.stats['hp'])
		return f"{emoji} {p.name.title()}{p.status_tag()} Lv{p.level}\n{bar} {max(0, p.current_hp)}/{p.stats['hp']}"

	def _embed(self) -> discord.Embed:
		desc = f"{self._hp_line(self.player_active)}\nvs\n{self._hp_line(self.wild)}\n\n" + ("\n".join(self.lines) if self.lines else "")
		embed = discord.Embed(title=f"Batalha Selvagem - Turno {self.turn}", description=desc, color=discord.Color.green())
		embed.set_image(url="attachment://battle.png")
		return embed

	async def start(self):
		self.actions_view = WildBattleView(self)
		self.lines = ["A batalha começou!"]
		self.message = await self.interaction.channel.send(embed=self._embed(), file=await self._compose_image(), view=self.actions_view)
		self.must_redraw_image = False

	async def refresh(self):
		if not self.message: return
		embed = self._embed()
		if self.must_redraw_image:
			file = await self._compose_image()
			await self.message.edit(attachments=[file], embed=embed, view=self.actions_view)
			self.must_redraw_image = False
		else:
			await self.message.edit(embed=embed, view=self.actions_view)

	async def _get_move(self, move_id: str):
		key = str(move_id).strip().lower().replace(" ", "-")
		if key in self.move_cache: return self.move_cache[key]
		try:
			mv = await pm.service.get_move(key)
			self.move_cache[key] = mv
			return mv
		except:
			return None

	def _pre_action(self, user: BattlePokemon) -> Optional[List[str]]:
		if user.volatile["flinch"]:
			user.volatile["flinch"] = False
			return [f"{user.name.title()} recuou e não agiu!"]
		s, c = user.status["name"], user.status["counter"]
		if s == "sleep":
			if c > 1:
				user.status["counter"] -= 1
				return [f"{user.name.title()} está dormindo..."]
			user.status = {"name": None, "counter": 0}
			return [f"{user.name.title()} acordou!"]
		if s == "freeze":
			if random.random() < 0.2:
				user.status = {"name": None, "counter": 0}
				return [f"{user.name.title()} descongelou!"]
			return [f"{user.name.title()} está congelado!"]
		if s == "paralysis" and random.random() < 0.25:
			return [f"{user.name.title()} está paralisado!"]
		return None

	def _confusion(self, user: BattlePokemon) -> Optional[List[str]]:
		if user.volatile["confuse"] <= 0: return None
		user.volatile["confuse"] -= 1
		if random.random() < 0.33:
			lv = user.level
			atk = user.eff_stat("atk"); df = user.eff_stat("def")
			base = (((2*lv/5)+2)*40*(atk/max(1,df)))/50 + 2
			dmg = max(1, int(base * random.uniform(0.9, 1.0)))
			user.current_hp = max(0, user.current_hp - dmg)
			return [f"{user.name.title()} está confuso e se atingiu, causando {dmg} de dano."]
		return [f"{user.name.title()} está confuso..."]

	def _secondary_effects(self, user: BattlePokemon, target: BattlePokemon, move, total_damage: int) -> List[str]:
		out = []
		meta = getattr(move, "meta", None) or _Meta()
		fc = int(getattr(meta, "flinch_chance", 0) or 0)
		if fc > 0 and random.randint(1,100) <= fc:
			target.volatile["flinch"] = True
			out.append("O alvo recuou!")
		drain = int(getattr(meta, "drain", 0) or 0)
		if drain != 0 and total_damage > 0:
			amt = max(1, int(total_damage * abs(drain) / 100))
			if drain > 0:
				user.current_hp = min(user.stats["hp"], user.current_hp + amt)
				out.append(f"{user.name.title()} recuperou {amt} HP!")
			else:
				user.current_hp = max(0, user.current_hp - amt)
				out.append(f"{user.name.title()} sofreu {amt} de recuo!")
		heal_pct = int(getattr(meta, "healing", 0) or 0)
		if heal_pct > 0 and _eff_damage_class(move) == "status":
			heal = max(1, int(user.stats["hp"] * heal_pct / 100))
			user.current_hp = min(user.stats["hp"], user.current_hp + heal)
			out.append(f"{user.name.title()} curou {heal} HP!")
		ail = getattr(meta, "ailment", None)
		ail_name = getattr(ail, "name", "none")
		ch = int(getattr(meta, "ailment_chance", 0) or getattr(move, "effect_chance", 0) or 0)
		if ail_name != "none" and (ch <= 0 or random.randint(1,100) <= ch):
			tt = _types_of(target)
			applied = False
			if ail_name == "poison":
				if "steel" not in tt and "poison" not in tt:
					applied = target.set_status("poison")
			elif ail_name == "burn":
				if "fire" not in tt:
					applied = target.set_status("burn")
			elif ail_name == "freeze":
				if "ice" not in tt:
					applied = target.set_status("freeze")
			elif ail_name == "paralysis":
				if not ("ground" in tt and getattr(move.type, "name", "").lower() == "electric"):
					applied = target.set_status("paralysis")
			elif ail_name == "sleep":
				applied = target.set_status("sleep")
			elif ail_name == "confusion":
				target.volatile["confuse"] = max(target.volatile["confuse"], random.randint(2,4))
				applied = True
			if applied:
				mapper = {"burn":"foi queimado","poison":"foi envenenado","paralysis":"ficou paralisado","sleep":"adormeceu","freeze":"foi congelado","confusion":"ficou confuso"}
				text = mapper.get(ail_name, "sofreu um efeito")
				out.append(f"O alvo {text}!")
		return out

	async def _apply_status_move(self, user: BattlePokemon, target: BattlePokemon, move) -> str:
		txts = []
		sc = getattr(move, "stat_changes", []) or []
		ec = getattr(move, "effect_chance", None)
		if sc and (ec is None or random.randint(1,100) <= int(ec)):
			for s in sc:
				raw = s.stat.name
				delta = int(s.change)
				canon = {"attack":"atk","defense":"def","special-attack":"sp_atk","special-defense":"sp_def","speed":"speed"}.get(raw)
				if not canon: continue
				tgt = user if delta > 0 else target
				tgt.stages[canon] = max(-6, min(6, tgt.stages[canon] + delta))
				txts.append(f"O {canon.upper()} de {tgt.name.title()} {'aumentou' if delta>0 else 'diminuiu'}!")
		txts.extend(self._secondary_effects(user, target, move, 0))
		return " ".join(txts) if txts else "Mas não surtiu efeito."

	async def _calc_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move):
		power = int(getattr(move, "power", 0) or 0)
		if power <= 0: return 0, 1.0, False
		dc = _eff_damage_class(move)
		atk = attacker.eff_stat("sp_atk") if dc == "special" else attacker.eff_stat("atk")
		dfn = defender.eff_stat("sp_def") if dc == "special" else defender.eff_stat("def")
		if attacker.status["name"] == "burn" and dc == "physical": atk = int(atk * 0.5)
		level = attacker.level
		base = (((2*level/5)+2) * power * (atk/max(1,dfn))) / 50 + 2
		t_mult = _type_multiplier(getattr(move.type, "name", "normal"), _types_of(defender))
		if t_mult == 0: return 0, 0.0, False
		stab = 1.5 if getattr(move.type, "name", "").lower() in _types_of(attacker) else 1.0
		rand = random.uniform(0.85, 1.0)
		crit = random.random() < 0.0625
		damage = int(base * stab * t_mult * rand * (1.5 if crit else 1.0))
		return max(1, damage), t_mult, crit

	async def _use_move(self, user: BattlePokemon, target: BattlePokemon, move, move_id: str) -> List[str]:
		if move is None:
			move = _fallback_for(move_id)
		mname = getattr(move, "name", str(move_id)).replace("-"," ").title()
		if move_id != "__struggle__":
			pp = user.get_pp(move_id)
			if pp is not None and pp <= 0:
				return [f"{user.name.title()} não tem mais PP para {mname}!"]
			user.dec_pp(move_id)
		acc = getattr(move, "accuracy", None)
		if not (acc is None or random.randint(1,100) <= int(acc)):
			return [f"{user.name.title()} usou {mname}, mas errou!"]
		if _eff_damage_class(move) == "status":
			return [f"{user.name.title()} usou {mname}! {await self._apply_status_move(user, target, move)}"]
		meta = getattr(move, "meta", None) or _Meta()
		minh = int(getattr(meta, "min_hits", 1) or 1)
		maxh = int(getattr(meta, "max_hits", 1) or 1)
		hits = 1 if maxh <= 1 else random.randint(minh, maxh)
		lines = []
		total = 0
		first_eff = 1.0
		first_crit = False
		for i in range(hits):
			dmg, eff, crit = await self._calc_damage(user, target, move)
			if i == 0: first_eff, first_crit = eff, crit
			if eff == 0.0:
				lines.append(f"{user.name.title()} usou {mname}! Não teve efeito.")
				return lines
			if target.status["name"] == "freeze" and getattr(move.type, "name", "").lower() == "fire" and dmg > 0:
				target.status = {"name": None, "counter": 0}
				lines.append(f"{target.name.title()} descongelou!")
			target.current_hp = max(0, target.current_hp - dmg)
			total += dmg
			if target.fainted: break
		txt = f"{user.name.title()} usou {mname}! Causou {total} de dano."
		if hits > 1: txt += f" Acertou {hits} vezes."
		if first_crit: txt += " Acerto crítico!"
		if first_eff > 1.0: txt += " É super eficaz!"
		if 0 < first_eff < 1.0: txt += " Não foi muito eficaz..."
		lines.append(txt)
		lines.extend(self._secondary_effects(user, target, move, total))
		return lines

	def _eot(self) -> List[str]:
		lines = []
		for p, who in [(self.player_active, "Seu"), (self.wild, "O selvagem")]:
			if p.fainted: continue
			if p.status["name"] == "burn":
				d = max(1, p.stats["hp"] // 16); p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano da queimadura.")
			elif p.status["name"] == "poison":
				d = max(1, p.stats["hp"] // 8); p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano do veneno.")
		return lines

	def _enemy_move_id(self) -> str:
		mv = [m for m in self.wild.moves if int(m.get("pp", 0)) > 0]
		return str(random.choice(mv)["id"]) if mv else "__struggle__"

	async def _act(self, is_player: bool, mv_id: str, mv_obj) -> List[str]:
		user = self.player_active if is_player else self.wild
		target = self.wild if is_player else self.player_active
		pre = self._pre_action(user)
		if pre and any(x for x in pre if any(t in x for t in ["não agiu","dormindo","congelado","paralisado"])): return pre
		conf = self._confusion(user)
		if conf and any("se atingiu" in x for x in conf): return (pre or []) + conf
		return (pre or []) + (conf or []) + await self._use_move(user, target, mv_obj, mv_id)

	async def handle_player_move(self, move_id: str):
		async with self.lock:
			if self.ended: return
			player_move = await self._get_move(move_id) or _fallback_for(move_id)
			enemy_id = self._enemy_move_id()
			enemy_move = _Struggle() if enemy_id == "__struggle__" else (await self._get_move(enemy_id) or _fallback_for(enemy_id))
			p_prio = int(getattr(player_move, "priority", 0) or 0)
			e_prio = int(getattr(enemy_move, "priority", 0) or 0)
			if p_prio != e_prio:
				order = ["player","enemy"] if p_prio > e_prio else ["enemy","player"]
			else:
				ps, es = self.player_active.eff_stat("speed"), self.wild.eff_stat("speed")
				order = ["player","enemy"] if ps > es else (["enemy","player"] if es > ps else random.choice([["player","enemy"], ["enemy","player"]]))
			lines = []
			for side in order:
				if self.player_active.fainted or self.wild.fainted: continue
				if side == "player":
					lines += await self._act(True, move_id, player_move)
					if self.wild.fainted:
						await self._on_win(); self.lines = lines; await self.refresh(); return
				else:
					lines += await self._act(False, enemy_id, enemy_move)
					if self.player_active.fainted:
						await self._on_faint(); self.lines = lines; await self.refresh(); return
			lines += self._eot()
			if self.wild.fainted: await self._on_win()
			elif self.player_active.fainted: await self._on_faint()
			if not self.ended: self.turn += 1
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
				enemy_id = self._enemy_move_id()
				enemy_move = _Struggle() if enemy_id == "__struggle__" else (await self._get_move(enemy_id) or _fallback_for(enemy_id))
				lines += await self._act(False, enemy_id, enemy_move)
				lines += self._eot()
				if self.player_active.fainted: await self._on_faint()
				if not self.ended: self.turn += 1
			self.lines = lines
			await self.refresh()

	async def attempt_capture(self) -> bool:
		if self.player_active.fainted:
			self.lines = ["Seu Pokémon desmaiou! Troque antes de capturar."]
			if self.actions_view: self.actions_view.force_switch_mode = True
			await self.refresh()
			return False
		max_hp = self.wild.stats["hp"]
		cur_hp = max(1, self.wild.current_hp)
		cr = int(getattr(self.wild.species_data, "capture_rate", 45) or 45)
		status_bonus = 2.5 if self.wild.status["name"] in ["sleep","freeze"] else (1.5 if self.wild.status["name"] else 1.0)
		a = ((3 * max_hp - 2 * cur_hp) * cr * status_bonus) / (3 * max_hp)
		a = max(1, min(255, int(a)))
		if random.randint(1, 255) <= a:
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
				exp=self.wild_raw.get("exp", 0),
				moves=self.wild_raw.get("moves", []),
				nickname=self.wild_raw.get("nickname"),
				name=self.wild_raw.get("name"),
				current_hp=self.wild_raw.get("current_hp"),
				on_party=pm.repo.tk.can_add_to_party(self.user_id)
			)
			self.ended = True
			self.lines = [f"Captura bem-sucedida! {self.player_active.name.title()} ganhou {xp} XP."]
			if self.actions_view: self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send(f"🎉 Capturou {self.wild.name.title()}! ⭐ {self.player_active.name.title()} recebeu {xp} XP.")
			return True
		else:
			lines = ["A Pokébola balançou... mas o Pokémon escapou!"]
			enemy_id = self._enemy_move_id()
			enemy_move = _Struggle() if enemy_id == "__struggle__" else (await self._get_move(enemy_id) or _fallback_for(enemy_id))
			lines += await self._act(False, enemy_id, enemy_move)
			lines += self._eot()
			if self.player_active.fainted: await self._on_faint()
			if not self.ended: self.turn += 1
			self.lines = lines
			await self.refresh()
			return False

	async def _on_win(self):
		xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
		pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
		self.ended = True
		self.lines = [f"O Pokémon selvagem caiu! {self.player_active.name.title()} ganhou {xp} XP."]
		if self.actions_view: self.actions_view.disable_all()
		await self.refresh()
		await self.interaction.channel.send(f"🏆 Vitória! ⭐ {self.player_active.name.title()} recebeu {xp} XP.")

	async def _on_faint(self):
		if not any(not p.fainted for p in self.player_team):
			self.ended = True
			self.lines = ["Todos os seus Pokémon desmaiaram. Derrota!"]
			if self.actions_view: self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send("💀 Você foi derrotado...")
			return
		if self.actions_view: self.actions_view.force_switch_mode = True
		self.lines = ["Seu Pokémon desmaiou! Escolha outro."]

class MovesView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		for mv in battle.player_active.moves:
			lbl = mv["id"].replace("-"," ").title()
			pp = mv["pp"]; pp_max = mv["pp_max"]
			btn = discord.ui.Button(style=discord.ButtonStyle.primary, label=f"{lbl} ({pp}/{pp_max})", disabled=(pp <= 0))
			btn.callback = self._mk_cb(mv["id"])
			self.add_item(btn)
		back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
		async def back_cb(i: discord.Interaction):
			if str(i.user.id) != battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			await i.response.edit_message(view=battle.actions_view)
		back.callback = back_cb
		self.add_item(back)

	def _mk_cb(self, move_id: str):
		async def _cb(i: discord.Interaction):
			if str(i.user.id) != self.battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
			if getattr(self.battle.actions_view, "force_switch_mode", False): return await i.response.send_message("Troque de Pokémon!", ephemeral=True)
			await i.response.defer()
			await self.battle.handle_player_move(move_id)
		return _cb

class SwitchView(discord.ui.View):
	def __init__(self, battle: WildBattle, force_only: bool = False, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		for i, p in enumerate(battle.player_team):
			lbl = f"{i+1}. {p.name.title()} ({max(0,p.current_hp)}/{p.stats['hp']})"
			btn = discord.ui.Button(style=discord.ButtonStyle.success, label=lbl, disabled=p.fainted or i == battle.active_player_idx)
			btn.callback = self._mk_cb(i)
			self.add_item(btn)
		if not force_only:
			back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
			async def back_cb(i: discord.Interaction):
				if str(i.user.id) != battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
				await i.response.edit_message(view=battle.actions_view)
			back.callback = back_cb
			self.add_item(back)

	def _mk_cb(self, idx: int):
		async def _cb(i: discord.Interaction):
			if str(i.user.id) != self.battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
			await i.response.defer()
			consume = not getattr(self.battle.actions_view, "force_switch_mode", False)
			await self.battle.switch_active(idx, consume_turn=consume)
			if getattr(self.battle.actions_view, "force_switch_mode", False):
				self.battle.actions_view.force_switch_mode = False
		return _cb

class WildBattleView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout=60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		self.user_id = battle.user_id
		self.force_switch_mode = False

	def disable_all(self):
		for item in self.children: item.disabled = True

	@discord.ui.button(style=discord.ButtonStyle.primary, emoji="⚔️", label="Lutar")
	async def fight(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode: return await i.response.edit_message(view=SwitchView(self.battle, force_only=True))
		await i.response.edit_message(view=MovesView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.success, emoji="🔁", label="Trocar")
	async def switch(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		await i.response.edit_message(view=SwitchView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
	async def capture(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode or self.battle.player_active.fainted: return await i.response.send_message("Troque de Pokémon!", ephemeral=True)
		await i.response.defer()
		await self.battle.attempt_capture()
