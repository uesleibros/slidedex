import discord
import aiopoke
import random
import math
import asyncio
from __main__ import pm
from typing import List, Dict, Any, Optional, Tuple, Set
from utils.canvas import compose_battle_async
from pokemon_sdk.calculations import calculate_stats
from utils.preloaded import preloaded_textures
from utils.pokemon_emojis import get_app_emoji
from helpers.effect_mapper import effect_mapper

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

def _get_stat(stats: Dict[str,int], key: str) -> int:
	for alias in STAT_ALIASES.get(key, []):
		if alias in stats: return int(stats[alias])
	return 1

def _stage_mult(stage: int) -> float:
	return (2+stage)/2 if stage>=0 else 2/(2-stage)

def _apply_stage(base: int, stage: int) -> int:
	return max(1, int(base * _stage_mult(stage)))

def _types_of(p: "BattlePokemon") -> List[str]:
	try: return [t.type.name.lower() for t in p.pokeapi_data.types]
	except: return []

def _type_mult(atk_type: str, def_types: List[str]) -> float:
	atk = (atk_type or "").lower()
	if atk not in TYPE_CHART: return 1.0
	m = 1.0
	for d in def_types:
		if d in TYPE_CHART[atk]["immune"]: return 0.0
		if d in TYPE_CHART[atk]["super"]: m *= 2.0
		elif d in TYPE_CHART[atk]["not"]: m *= 0.5
	return m

def _hp_bar(c: int, t: int, l: int=10) -> str:
	p = 0 if t<=0 else max(0.0, min(1.0, c/t))
	f = int(round(l*p))
	bar = "█"*f + "░"*(l-f)
	return f"`[{bar}]`"

def _slug(move_id: Any) -> str:
	if move_id is None: return ""
	s = str(move_id).strip().lower()
	return s.replace(" ", "-")

class MoveData:
	def __init__(self,
		name: str, accuracy: Optional[int], power: int, priority: int, dmg_class: str, type_name: str,
		min_hits: int, max_hits: int, flinch: int, drain: int, recoil: int, healing: int,
		ailment: Optional[str], ailment_chance: int, stat_changes: List[Tuple[str,int,bool]]
	):
		self.name=name; self.accuracy=accuracy; self.power=power; self.priority=priority
		self.dmg_class=dmg_class; self.type_name=type_name
		self.min_hits=min_hits; self.max_hits=max_hits
		self.flinch=flinch; self.drain=drain; self.recoil=recoil; self.healing=healing
		self.ailment=ailment; self.ailment_chance=ailment_chance
		self.stat_changes=stat_changes

def _canon_stat(s: str) -> Optional[str]:
	return {"attack":"atk","defense":"def","special-attack":"sp_atk","special-defense":"sp_def","speed":"speed"}.get(s)

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
	except: pass
	return {"accuracy": move.accuracy, "power": move.power, "pp": getattr(move, "pp", None), "effect_chance": getattr(move, "effect_chance", None)}

def _normalize_move(move) -> MoveData:
	name = getattr(move, "name", "move").replace("-"," ").title()
	type_name = getattr(getattr(move, "type", None), "name", "normal")
	dc = getattr(getattr(move, "damage_class", None), "name", None)
	dmg_class = dc if dc in {"physical","special","status"} else ("physical" if (getattr(move,"power",0) or 0) > 0 else "status")
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
	ailment = None if ail in {None,"none","unknown"} else ail
	ailment_chance = int(getattr(meta, "ailment_chance", 0) or pv["effect_chance"] or (100 if (dmg_class=="status" and ailment) else 0) or 0)
	target_self_default = getattr(getattr(move, "target", None), "name", "") in {"user","user-or-ally","ally"}
	stat_changes = []
	try:
		for sc in getattr(move, "stat_changes", []) or []:
			raw = getattr(getattr(sc, "stat", None), "name", None)
			delta = int(getattr(sc, "change", 0) or 0)
			canon = _canon_stat(raw) if raw else None
			if canon and delta != 0:
				target_self = target_self_default if delta>0 else not target_self_default
				stat_changes.append((canon, delta, target_self))
	except: pass
	return MoveData(
		name=name, accuracy=accuracy, power=power, priority=priority, dmg_class=dmg_class, type_name=type_name,
		min_hits=min_hits, max_hits=max_hits, flinch=flinch, drain=drain, recoil=recoil, healing=healing,
		ailment=ailment, ailment_chance=ailment_chance, stat_changes=stat_changes
	)

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
			"back":  pokeapi_data.sprites.back_shiny  if self.is_shiny else pokeapi_data.sprites.back_default
		}

	@property
	def fainted(self) -> bool:
		return self.current_hp <= 0

	def eff_stat(self, key: str) -> int:
		val = _apply_stage(_get_stat(self.stats, key), self.stages[key])
		if key=="speed" and self.status["name"]=="paralysis": val = int(val * 0.5)
		return max(1, val)

	def dec_pp(self, move_id: str):
		for m in self.moves:
			if _slug(m["id"]) == _slug(move_id) and "pp" in m:
				m["pp"] = max(0, int(m["pp"]) - 1)
				return

	def get_pp(self, move_id: str) -> Optional[int]:
		for m in self.moves:
			if _slug(m["id"]) == _slug(move_id):
				return int(m.get("pp", 0))
		return None

	def set_status(self, name: str, turns: Optional[int]=None) -> bool:
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
		self.move_cache: Dict[str, MoveData] = {}

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
		await self._warm_moves()

	async def _warm_moves(self):
		ids: Set[str] = set()
		for mv in self.wild.moves:
			ids.add(_slug(mv["id"]))
		for p in self.player_team:
			for mv in p.moves:
				ids.add(_slug(mv["id"]))
		coros = [self._fetch_move(mid) for mid in ids if mid]
		if coros:
			await asyncio.gather(*coros)

	async def _compose_image(self):
		pb = await self.player_active.sprites["back"].read() if self.player_active.sprites["back"] else None
		ef = await self.wild.sprites["front"].read() if self.wild.sprites["front"] else None
		buf = await compose_battle_async(pb, ef, preloaded_textures["battle"])
		return discord.File(buf, filename="battle.png")

	def _hp_line(self, p: BattlePokemon) -> str:
		emoji = get_app_emoji(f"p_{p.species_id}")
		bar = _hp_bar(p.current_hp, p.stats["hp"])
		return f"{emoji} {p.name.title()}{p.status_tag()} Lv{p.level}\n{bar} {max(0,p.current_hp)}/{p.stats['hp']}"

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

	async def _fetch_move(self, move_id: str) -> MoveData:
		key = _slug(move_id)
		if not key: raise ValueError("move_id vazio")
		if key in self.move_cache: return self.move_cache[key]
		mv = await pm.service.get_move(key)
		md = _normalize_move(mv)
		self.move_cache[key] = md
		return md

	def _pre_action(self, user: BattlePokemon) -> Tuple[bool,List[str]]:
		if user.volatile["flinch"]:
			user.volatile["flinch"] = False
			return True, [f"{user.name.title()} recuou e não agiu!"]
		s, c = user.status["name"], user.status["counter"]
		if s == "sleep":
			if c > 1:
				user.status["counter"] -= 1
				return True, [f"{user.name.title()} está dormindo..."]
			user.status = {"name": None, "counter": 0}
			return False, [f"{user.name.title()} acordou!"]
		if s == "freeze":
			if random.random() < 0.2:
				user.status = {"name": None, "counter": 0}
				return False, [f"{user.name.title()} descongelou!"]
			return True, [f"{user.name.title()} está congelado!"]
		if s == "paralysis" and random.random() < 0.25:
			return True, [f"{user.name.title()} está paralisado!"]
		return False, []

	def _confusion(self, user: BattlePokemon) -> Tuple[bool,List[str]]:
		if user.volatile["confuse"] <= 0: return False, []
		user.volatile["confuse"] -= 1
		if random.random() < 0.33:
			lv = user.level
			atk = user.eff_stat("atk"); df = user.eff_stat("def")
			base = (((2*lv/5)+2)*40*(atk/max(1,df)))/50 + 2
			dmg = max(1, int(base * random.uniform(0.9,1.0)))
			user.current_hp = max(0, user.current_hp - dmg)
			return True, [f"{user.name.title()} está confuso e se atingiu, causando {dmg} de dano."]
		return False, [f"{user.name.title()} está confuso..."]

	def _apply_secondary(self, user: BattlePokemon, target: BattlePokemon, md: MoveData, total: int) -> List[str]:
		out = []
		if md.flinch > 0 and random.randint(1,100) <= md.flinch:
			target.volatile["flinch"] = True
			out.append("O alvo recuou!")
		if md.drain != 0 and total > 0:
			amt = max(1, int(total * abs(md.drain) / 100))
			if md.drain > 0:
				user.current_hp = min(user.stats["hp"], user.current_hp + amt)
				out.append(f"{user.name.title()} recuperou {amt} HP!")
			else:
				user.current_hp = max(0, user.current_hp - amt)
				out.append(f"{user.name.title()} sofreu {amt} de recuo!")
		if md.healing > 0 and md.dmg_class == "status":
			heal = max(1, int(user.stats["hp"] * md.healing / 100))
			user.current_hp = min(user.stats["hp"], user.current_hp + heal)
			out.append(f"{user.name.title()} curou {heal} HP!")
		if md.ailment:
			ch = md.ailment_chance if md.ailment_chance>0 else (100 if md.dmg_class=="status" else 0)
			if random.randint(1,100) <= ch:
				applied = False
				tt = _types_of(target)
				if md.ailment == "poison":
					if "steel" not in tt and "poison" not in tt: applied = target.set_status("poison")
				elif md.ailment == "burn":
					if "fire" not in tt: applied = target.set_status("burn")
				elif md.ailment == "freeze":
					if "ice" not in tt: applied = target.set_status("freeze")
				elif md.ailment == "paralysis":
					applied = target.set_status("paralysis")
				elif md.ailment == "sleep":
					applied = target.set_status("sleep")
				elif md.ailment == "confusion":
					target.volatile["confuse"] = max(target.volatile["confuse"], random.randint(2,4))
					applied = True
				if applied:
					texts = {"burn":"foi queimado","poison":"foi envenenado","paralysis":"ficou paralisado","sleep":"adormeceu","freeze":"foi congelado","confusion":"ficou confuso"}
					out.append(f"O alvo {texts[md.ailment]}!")
		return out

	async def _apply_status_move(self, user: BattlePokemon, target: BattlePokemon, md: MoveData) -> List[str]:
		lines = [f"{user.name.title()} usou {md.name}!"]
		changed = False
		for stat, delta, to_self in md.stat_changes:
			tgt = user if to_self else target
			old = tgt.stages[stat]
			tgt.stages[stat] = max(-6, min(6, tgt.stages[stat] + delta))
			if tgt.stages[stat] != old:
				changed = True
				what = {"atk":"Ataque","def":"Defesa","sp_atk":"Ataque Especial","sp_def":"Defesa Especial","speed":"Velocidade"}[stat]
				lines.append(f"{tgt.name.title()}: {what} {'↑' if delta>0 else '↓'} ({tgt.stages[stat]})")
		sec = self._apply_secondary(user, target, md, 0)
		if sec:
			changed = True
			lines.extend(sec)
		if not changed:
			lines.append("Mas não surtiu efeito.")
		return lines

	async def _calc_damage(self, atk: BattlePokemon, df: BattlePokemon, md: MoveData) -> Tuple[int,float,bool]:
		if md.power <= 0: return 0, 1.0, False
		if md.dmg_class == "special":
			a = atk.eff_stat("sp_atk"); d = df.eff_stat("sp_def")
		else:
			a = atk.eff_stat("atk"); d = df.eff_stat("def")
			if atk.status["name"] == "burn": a = int(a * 0.5)
		base = (((2*atk.level/5)+2) * md.power * (a/max(1,d))) / 50 + 2
		tm = _type_mult(md.type_name, _types_of(df))
		if tm == 0.0: return 0, 0.0, False
		stab = 1.5 if md.type_name.lower() in _types_of(atk) else 1.0
		crit = random.random() < 0.0625
		damage = int(base * stab * tm * random.uniform(0.85, 1.0) * (1.5 if crit else 1.0))
		return max(1, damage), tm, crit

	async def _use_move(self, user: BattlePokemon, target: BattlePokemon, md: MoveData, move_id_for_pp: Optional[str]) -> List[str]:
		if move_id_for_pp and move_id_for_pp != "__struggle__":
			pp = user.get_pp(move_id_for_pp)
			if pp is not None and pp <= 0:
				return [f"{user.name.title()} não tem mais PP para {md.name}!"]
			user.dec_pp(move_id_for_pp)
		if md.accuracy is not None and random.randint(1,100) > int(md.accuracy):
			return [f"{user.name.title()} usou {md.name}, mas errou!"]
		if md.dmg_class == "status":
			return await self._apply_status_move(user, target, md)
		lines = []
		hits = 1 if md.max_hits <= 1 else random.randint(md.min_hits, md.max_hits)
		total = 0
		first_tm, first_crit = 1.0, False
		for i in range(hits):
			dmg, tm, crit = await self._calc_damage(user, target, md)
			if i==0: first_tm, first_crit = tm, crit
			if tm == 0.0:
				lines.append(f"{user.name.title()} usou {md.name}! Não teve efeito.")
				return lines
			if target.status["name"] == "freeze" and md.type_name.lower()=="fire" and dmg>0:
				target.status = {"name": None, "counter": 0}
				lines.append(f"{target.name.title()} descongelou!")
			target.current_hp = max(0, target.current_hp - dmg)
			total += dmg
			if target.fainted: break
		txt = f"{user.name.title()} usou {md.name}! Causou {total} de dano."
		if hits > 1: txt += f" Acertou {hits} vezes."
		if first_crit: txt += " Acerto crítico!"
		if first_tm > 1.0: txt += " É super eficaz!"
		if 0 < first_tm < 1.0: txt += " Não foi muito eficaz..."
		lines.append(txt)
		lines.extend(self._apply_secondary(user, target, md, total))
		return lines

	def _end_of_turn(self) -> List[str]:
		lines = []
		for p, who in [(self.player_active, "Seu"), (self.wild, "O selvagem")]:
			if p.fainted: continue
			if p.status["name"] == "burn":
				d = max(1, p.stats["hp"]//16); p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano da queimadura.")
			elif p.status["name"] == "poison":
				d = max(1, p.stats["hp"]//8); p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano do veneno.")
		return lines

	def _enemy_pick(self) -> str:
		opts = [m for m in self.wild.moves if int(m.get("pp",0))>0]
		return str(random.choice(opts)["id"]) if opts else "__struggle__"

	async def _act(self, player_side: bool, mv_id: str, md: MoveData) -> List[str]:
		user = self.player_active if player_side else self.wild
		target = self.wild if player_side else self.player_active
		block, pre = self._pre_action(user)
		if block: return pre
		conf_block, conf = self._confusion(user)
		if conf_block: return pre + conf
		return pre + conf + await self._use_move(user, target, md, mv_id)

	async def handle_player_move(self, move_id: str):
		async with self.lock:
			if self.ended: return
			pmd = await self._fetch_move(move_id)
			eid = self._enemy_pick()
			emd = await self._fetch_move(eid) if eid != "__struggle__" else MoveData("Struggle", None, 50, 0, "physical", "normal", 1,1, 0,0,0,0, None,0, [])
			if pmd.priority != emd.priority:
				order = ["player","enemy"] if pmd.priority>emd.priority else ["enemy","player"]
			else:
				ps, es = self.player_active.eff_stat("speed"), self.wild.eff_stat("speed")
				order = ["player","enemy"] if ps>es else (["enemy","player"] if es>ps else random.choice([["player","enemy"],["enemy","player"]]))
			lines = []
			for side in order:
				if self.player_active.fainted or self.wild.fainted: continue
				if side=="player":
					lines += await self._act(True, move_id, pmd)
					if self.wild.fainted: await self._on_win(); self.lines=lines; await self.refresh(); return
				else:
					lines += await self._act(False, eid, emd)
					if self.player_active.fainted: await self._on_faint(); self.lines=lines; await self.refresh(); return
			lines += self._end_of_turn()
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
				eid = self._enemy_pick()
				emd = await self._fetch_move(eid) if eid != "__struggle__" else MoveData("Struggle", None, 50, 0, "physical", "normal", 1,1, 0,0,0,0, None,0, [])
				lines += await self._act(False, eid, emd)
				lines += self._end_of_turn()
				if self.player_active.fainted: await self._on_faint()
				if not self.ended: self.turn += 1
			self.lines = lines
			await self.refresh()

	def _gen3_capture(self) -> Tuple[bool,int]:
		max_hp = self.wild.stats["hp"]
		cur_hp = max(1, self.wild.current_hp)
		cr = int(getattr(self.wild.species_data, "capture_rate", 45) or 45)
		ball = 1.0
		status = self.wild.status["name"]
		status_bonus = 2.5 if status in {"sleep","freeze"} else (1.5 if status in {"paralysis","poison","burn"} else 1.0)
		a = int(((3*max_hp - 2*cur_hp) * cr * ball * status_bonus) / (3*max_hp))
		if a >= 255: return True, 4
		if a <= 0: return False, 0
		r = 65536
		b = int(1048560 / math.sqrt(math.sqrt((16711680 / a))))
		shakes = 0
		for _ in range(4):
			if random.randint(0, r-1) < b:
				shakes += 1
			else:
				break
		return shakes == 4, shakes

	async def attempt_capture(self) -> bool:
		if self.player_active.fainted:
			self.lines = ["Seu Pokémon desmaiou! Troque antes de capturar."]
			if self.actions_view: self.actions_view.force_switch_mode = True
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
			self.lines = [f"Captura bem-sucedida! {self.player_active.name.title()} ganhou {xp} XP."]
			if self.actions_view: self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send(f"🎉 Capturou {self.wild.name.title()}! ⭐ {self.player_active.name.title()} recebeu {xp} XP.")
			return True
		else:
			msg = "A Pokébola balançou " + (f"{shakes}x e " if shakes>0 else "") + "o Pokémon escapou!"
			lines = [msg]
			eid = self._enemy_pick()
			emd = await self._fetch_move(eid) if eid != "__struggle__" else MoveData("Struggle", None, 50, 0, "physical", "normal", 1,1, 0,0,0,0, None,0, [])
			lines += await self._act(False, eid, emd)
			lines += self._end_of_turn()
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
			key = _slug(mv["id"])
			md = battle.move_cache.get(key)
			label_text = (md.name if md else key.replace("-"," ").title())
			pp, pp_max = mv["pp"], mv["pp_max"]
			btn = discord.ui.Button(style=discord.ButtonStyle.primary, label=f"{label_text} ({pp}/{pp_max})", disabled=(pp <= 0))
			btn.callback = self._cb(mv["id"])
			self.add_item(btn)
		back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
		async def back_cb(i: discord.Interaction):
			if str(i.user.id)!=battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			await i.response.edit_message(view=battle.actions_view)
		back.callback = back_cb
		self.add_item(back)

	def _cb(self, move_id: str):
		async def _run(i: discord.Interaction):
			if str(i.user.id)!=self.battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
			if getattr(self.battle.actions_view, "force_switch_mode", False): return await i.response.send_message("Troque de Pokémon!", ephemeral=True)
			await i.response.defer()
			await self.battle.handle_player_move(move_id)
		return _run

class SwitchView(discord.ui.View):
	def __init__(self, battle: WildBattle, force_only: bool = False, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		for i, p in enumerate(battle.player_team):
			lbl = f"{i+1}. {p.name.title()} ({max(0,p.current_hp)}/{p.stats['hp']})"
			btn = discord.ui.Button(style=discord.ButtonStyle.success, label=lbl, disabled=p.fainted or i==battle.active_player_idx)
			btn.callback = self._mk(i); self.add_item(btn)
		if not force_only:
			back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
			async def back_cb(i: discord.Interaction):
				if str(i.user.id)!=battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
				await i.response.edit_message(view=battle.actions_view)
			back.callback = back_cb
			self.add_item(back)

	def _mk(self, idx: int):
		async def _run(i: discord.Interaction):
			if str(i.user.id)!=self.battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
			await i.response.defer()
			consume = not getattr(self.battle.actions_view, "force_switch_mode", False)
			await self.battle.switch_active(idx, consume_turn=consume)
			if getattr(self.battle.actions_view, "force_switch_mode", False):
				self.battle.actions_view.force_switch_mode = False
		return _run

class WildBattleView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout=60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		self.user_id = battle.user_id
		self.force_switch_mode = False

	def disable_all(self):
		for item in self.children: item.disabled = True

	@discord.ui.button(style=discord.ButtonStyle.primary, label="Lutar")
	async def fight(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode: return await i.response.edit_message(view=SwitchView(self.battle, force_only=True))
		await i.response.edit_message(view=MovesView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.primary, label="Trocar")
	async def switch(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		await i.response.edit_message(view=SwitchView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
	async def capture(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended: return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode or self.battle.player_active.fainted: return await i.response.send_message("Troque de Pokémon!", ephemeral=True)
		await i.response.defer()
		await self.battle.attempt_capture()

