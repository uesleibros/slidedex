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
			return 0.0
		if d in TYPE_CHART[atk]["super"]:
			m *= 2.0
		elif d in TYPE_CHART[atk]["not"]:
			m *= 0.5
	return m

def _stage_multiplier(stage: int) -> float:
	return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)

STAT_ALIASES = {"hp":["hp"],"atk":["atk","attack"],"def":["def","defense"],"sp_atk":["sp_atk","spa","special-attack"],"sp_def":["sp_def","spd","special-defense"],"speed":["speed","spe"]}

def _get_stat_value(stats: Dict[str, int], key: str) -> int:
	for alias in STAT_ALIASES.get(key, []):
		if alias in stats: return int(stats[alias])
	return 1

def _apply_stage(base: int, stage: int) -> int:
	return max(1, int(base * _stage_multiplier(stage)))

def _types_of(poke: "BattlePokemon") -> List[str]:
	return [t.type.name.lower() for t in poke.pokeapi_data.types]

def _hp_bar(current: int, total: int, length: int = 10) -> str:
	pct = current / total
	filled = int(length * pct)
	bar = '█' * filled + '░' * (length - filled)
	color = "🟢" if pct > 0.5 else ("🟡" if pct > 0.2 else "🔴")
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
	power, accuracy, priority, name = 50, None, 0, "Struggle"
	damage_class, type, stat_changes, effect_chance, meta = _obj(name="physical"), _obj(name="normal"), [], None, _Meta()

class _FallbackMove:
	def __init__(self, name="Golpe Falho"):
		self.name, self.power, self.accuracy, self.priority = name, 0, 100, 0
		self.damage_class, self.type, self.stat_changes, self.effect_chance, self.meta = _obj(name="status"), _obj(name="normal"), [], None, _Meta()

class BattlePokemon:
	def __init__(self, raw: Dict[str, Any], pokeapi_data: aiopoke.Pokemon):
		self.raw = raw
		self.species_id = raw["species_id"]
		self.name = raw.get("name")
		self.level = raw["level"]
		base_stats = pm.service.get_base_stats(pokeapi_data)
		self.stats = calculate_stats(base_stats, raw["ivs"], raw["evs"], raw["level"], raw["nature"])
		self.current_hp = raw.get("current_hp") or self.stats["hp"]
		self.moves = raw.get("moves") or [{"id": "tackle", "pp": 35, "pp_max": 35}]
		self.pokeapi_data = pokeapi_data
		self.is_shiny = raw.get("is_shiny", False)
		self.stages = {s: 0 for s in ["atk", "def", "sp_atk", "sp_def", "speed"]}
		self.status = {"name": None, "counter": 0}
		self.volatile = {"flinch": False, "confuse": 0}
		self.sprites = {"front": pokeapi_data.sprites.front_shiny, "back": pokeapi_data.sprites.back_shiny} if self.is_shiny else {"front": pokeapi_data.sprites.front_default, "back": pokeapi_data.sprites.back_default}

	@property
	def fainted(self) -> bool: return self.current_hp <= 0
	def eff_stat(self, key: str) -> int:
		val = _apply_stage(_get_stat_value(self.stats, key), self.stages[key])
		if key == "speed" and self.status["name"] == "paralysis": val = int(val * 0.5)
		return max(1, val)
	def dec_pp(self, move_id: str):
		for m in self.moves:
			if str(m["id"]).lower() == str(move_id).lower() and "pp" in m: m["pp"] = max(0, int(m["pp"]) - 1)
	def get_pp(self, move_id: str) -> Optional[int]:
		for m in self.moves:
			if str(m["id"]).lower() == str(move_id).lower(): return int(m.get("pp", 0))
	def set_status(self, name: str, turns: Optional[int] = None) -> bool:
		if self.status["name"]: return False
		self.status = {"name": name, "counter": turns or (random.randint(1, 3) if name == "sleep" else 0)}
		return True
	def status_tag(self) -> str:
		tags = {"burn":"BRN","poison":"PSN","paralysis":"PAR","sleep":"SLP","freeze":"FRZ"}
		return f" [{tags[self.status['name']]}]" if self.status["name"] in tags else ""

class WildBattle:
	def __init__(self, player_party: List[Dict[str, Any]], wild: Dict[str, Any], user_id: str, interaction: discord.Interaction):
		self.user_id = user_id
		self.interaction = interaction
		self.player_party_raw = player_party
		self.active_player_idx = 0
		self.wild_raw = wild
		self.ended, self.turn, self.must_redraw_image = False, 1, True
		self.lock = asyncio.Lock()
		self.player_team: List[BattlePokemon] = []
		self.wild: Optional[BattlePokemon] = None
		self.actions_view: Optional[WildBattleView] = None
		self.lines: List[str] = []

	@property
	def player_active(self) -> BattlePokemon: return self.player_team[self.active_player_idx]
	async def setup(self):
		self.wild = BattlePokemon(self.wild_raw, await pm.service.get_pokemon(self.wild_raw["species_id"]))
		for p in self.player_party_raw: self.player_team.append(BattlePokemon(p, await pm.service.get_pokemon(p["species_id"])))
	async def _compose_image(self):
		p_sprite = await self.player_active.sprites["back"].read() if self.player_active.sprites["back"] else None
		w_sprite = await self.wild.sprites["front"].read() if self.wild.sprites["front"] else None
		return discord.File(await compose_battle_async(p_sprite, w_sprite, preloaded_textures["battle"]), "battle.png")
	def _hp_line(self, p: BattlePokemon) -> str:
		emoji = get_app_emoji(f"p_{p.species_id}")
		hp_bar = _hp_bar(p.current_hp, p.stats['hp'])
		return f"{emoji} {p.name.title()}{p.status_tag()} Lv{p.level}\n{hp_bar} {max(0, p.current_hp)}/{p.stats['hp']}"
	def _embed(self) -> discord.Embed:
		desc = f"{self._hp_line(self.player_active)}\nvs\n{self._hp_line(self.wild)}\n\n" + "\n".join(self.lines)
		return discord.Embed(title=f"Batalha Selvagem - Turno {self.turn}", description=desc, color=discord.Color.green()).set_image(url="attachment://battle.png")
	async def start(self):
		self.actions_view = WildBattleView(self)
		self.lines = ["A batalha começou!"]
		self.message = await self.interaction.channel.send(embed=self._embed(), file=await self._compose_image(), view=self.actions_view)
		self.must_redraw_image = False
	async def refresh(self):
		if not self.message: return
		args = {"embed": self._embed(), "view": self.actions_view}
		if self.must_redraw_image:
			args["attachments"] = [await self._compose_image()]
			self.must_redraw_image = False
		await self.message.edit(**args)
	async def _get_move(self, move_id: str):
		try: return await pm.service.get_move(str(move_id).strip().lower().replace(" ", "-"))
		except: return None
	def _pre_action_block(self, user: BattlePokemon) -> Optional[List[str]]:
		if user.volatile["flinch"]:
			user.volatile["flinch"] = False
			return [f"{user.name.title()} recuou e não agiu!"]
		s_name, s_counter = user.status["name"], user.status["counter"]
		if s_name == "sleep":
			if s_counter > 1:
				user.status["counter"] -= 1
				return [f"{user.name.title()} está dormindo..."]
			user.status = {"name": None, "counter": 0}
			return [f"{user.name.title()} acordou!"]
		if s_name == "freeze":
			if random.random() < 0.2:
				user.status = {"name": None, "counter": 0}
				return [f"{user.name.title()} descongelou!"]
			return [f"{user.name.title()} está congelado!"]
		if s_name == "paralysis" and random.random() < 0.25:
			return [f"{user.name.title()} está paralisado!"]
		return None
	def _confusion_check(self, user: BattlePokemon) -> Optional[List[str]]:
		if user.volatile["confuse"] <= 0: return None
		user.volatile["confuse"] -= 1
		if random.random() < 0.33:
			dmg = max(1, int(((((2*user.level/5+2)*40*(user.eff_stat("atk")/max(1,user.eff_stat("def"))))/50)+2) * random.uniform(0.9,1.0)))
			user.current_hp = max(0, user.current_hp - dmg)
			return [f"{user.name.title()} está confuso e se atingiu, causando {dmg} de dano."]
		return [f"{user.name.title()} está confuso..."]
	def _apply_secondary_effects(self, user: BattlePokemon, target: BattlePokemon, move, total_damage: int) -> List[str]:
		out, meta = [], getattr(move, "meta", _Meta())
		if random.randint(1,100) <= meta.flinch_chance:
			target.volatile["flinch"] = True
			out.append("O alvo recuou!")
		if meta.drain != 0 and total_damage > 0:
			amount = max(1, int(total_damage * abs(meta.drain) / 100))
			if meta.drain > 0:
				user.current_hp = min(user.stats["hp"], user.current_hp + amount)
				out.append(f"{user.name.title()} recuperou {amount} HP!")
			else:
				user.current_hp = max(0, user.current_hp - amount)
				out.append(f"{user.name.title()} sofreu {amount} de recuo!")
		if meta.healing > 0 and getattr(move.damage_class,"name","") == "status":
			heal = max(1, int(user.stats["hp"] * meta.healing/100))
			user.current_hp = min(user.stats["hp"], user.current_hp + heal)
			out.append(f"{user.name.title()} curou {heal} HP!")
		ail_name, ail_chance = meta.ailment.name, meta.ailment_chance or getattr(move, "effect_chance", 0)
		if ail_name != "none" and random.randint(1,100) <= ail_chance:
			tt, applied = _types_of(target), False
			if ail_name == "poison" and not ("steel" in tt or "poison" in tt): applied = target.set_status("poison")
			elif ail_name == "burn" and "fire" not in tt: applied = target.set_status("burn")
			elif ail_name == "freeze" and "ice" not in tt: applied = target.set_status("freeze")
			elif ail_name == "paralysis" and "ground" not in tt: applied = target.set_status("paralysis")
			elif ail_name == "sleep": applied = target.set_status("sleep")
			elif ail_name == "confusion": target.volatile["confuse"] = max(target.volatile["confuse"], random.randint(2, 4)); applied = True
			if applied:
				status_texts = {
					'burn': 'foi queimado',
					'poison': 'foi envenenado',
					'paralysis': 'ficou paralisado',
					'sleep': 'adormeceu',
					'freeze': 'foi congelado',
					'confusion': 'ficou confuso'
				}
				text = status_texts.get(ail_name, "sofreu um efeito desconhecido")
				out.append(f"O alvo {text}!")
		return out
	async def _apply_status_move(self, user: BattlePokemon, target: BattlePokemon, move) -> str:
		out, sc = [], getattr(move, "stat_changes", [])
		if sc and (not getattr(move,"effect_chance",None) or random.randint(1,100) <= move.effect_chance):
			for s in sc:
				stat, delta = {"attack":"atk","defense":"def","special-attack":"sp_atk","special-defense":"sp_def","speed":"speed"}.get(s.stat.name), s.change
				if stat:
					tgt = user if delta > 0 else target
					tgt.stages[stat] = max(-6, min(6, tgt.stages[stat] + delta))
					out.append(f"{stat.upper()} de {'você' if tgt is user else 'o alvo'} {'aumentou' if delta > 0 else 'diminuiu'}!")
		out.extend(self._apply_secondary_effects(user, target, move, 0))
		return " ".join(out) or "Mas falhou."
	async def _calc_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move):
		power = int(getattr(move, "power", 0) or 0)
		if power <= 0: return 0, 1.0, False
		dmg_class = getattr(move.damage_class, "name", "physical")
		atk_stat = attacker.eff_stat("sp_atk") if dmg_class == "special" else attacker.eff_stat("atk")
		def_stat = defender.eff_stat("sp_def") if dmg_class == "special" else defender.eff_stat("def")
		if attacker.status["name"] == "burn" and dmg_class == "physical": atk_stat = int(atk_stat * 0.5)
		base = ((((2*attacker.level/5)+2)*power*(atk_stat/max(1,def_stat)))/50)+2
		type_mult = _type_multiplier(getattr(move.type, "name", "normal"), _types_of(defender))
		if type_mult == 0: return 0, 0, False
		stab = 1.5 if getattr(move.type, "name", "").lower() in _types_of(attacker) else 1.0
		crit = random.random() < 0.0625
		damage = int(base * stab * type_mult * random.uniform(0.9, 1.0) * (1.5 if crit else 1.0))
		return max(1, damage), type_mult, crit
	async def _use_move(self, user: BattlePokemon, target: BattlePokemon, move, move_id: str) -> List[str]:
		if move is None: move = _FallbackMove(name=move_id.replace("-", " ").title())
		mname = getattr(move, "name", "Golpe").replace("-", " ").title()
		if move_id != "__struggle__":
			if user.get_pp(move_id) == 0: return [f"{user.name.title()} não tem mais PP para {mname}!"]
			user.dec_pp(move_id)
		if not (getattr(move, "accuracy", None) is None or random.randint(1,100) <= move.accuracy): return [f"{user.name.title()} usou {mname}, mas errou!"]
		if getattr(move.damage_class, "name", "") == "status": return [f"{user.name.title()} usou {mname}! {await self._apply_status_move(user, target, move)}"]
		lines, total_damage, hits = [], 0, random.randint(getattr(move.meta,"min_hits",1) or 1, getattr(move.meta,"max_hits",1) or 1)
		for i in range(hits):
			dmg, eff, crit = await self._calc_damage(user, target, move)
			if eff == 0: return [f"{user.name.title()} usou {mname}! Não teve efeito."]
			if target.status["name"] == "freeze" and getattr(move.type,"name","").lower() == "fire" and dmg > 0:
				target.status = {"name":None,"counter":0}; lines.append(f"{target.name.title()} descongelou!")
			target.current_hp = max(0, target.current_hp - dmg)
			total_damage += dmg
			if i==0: first_eff, first_crit = eff, crit
			if target.fainted: break
		txt = f"{user.name.title()} usou {mname}! Causou {total_damage} de dano."
		if hits > 1: txt += f" Acertou {hits} vezes."
		if first_crit: txt += " Acerto crítico!"
		if first_eff > 1: txt += " É super eficaz!"
		if 0 < first_eff < 1: txt += " Não foi muito eficaz..."
		lines.append(txt)
		lines.extend(self._apply_secondary_effects(user, target, move, total_damage))
		return lines
	def _end_of_turn_effects(self) -> List[str]:
		lines = []
		for p, who in [(self.player_active, "Seu"), (self.wild, "O selvagem")]:
			if p.fainted: continue
			if p.status["name"] == "burn": dmg = max(1, p.stats["hp"]//16); p.current_hp -= dmg; lines.append(f"{who} {p.name.title()} sofreu {dmg} de dano da queimadura.")
			elif p.status["name"] == "poison": dmg = max(1, p.stats["hp"]//8); p.current_hp -= dmg; lines.append(f"{who} {p.name.title()} sofreu {dmg} de dano do veneno.")
		return lines
	async def _act(self, is_player: bool, move_id: str, move_obj) -> List[str]:
		user, target = (self.player_active, self.wild) if is_player else (self.wild, self.player_active)
		lines = self._pre_action_block(user) or []
		if any("não agiu" in l or "dormindo" in l or "congelado" in l or "paralisado" in l for l in lines): return lines
		conf = self._confusion_check(user)
		if conf and any("se atingiu" in l for l in conf): return lines + conf
		return lines + (conf or []) + await self._use_move(user, target, move_obj, move_id)
	async def handle_player_move(self, move_id: str):
		async with self.lock:
			if self.ended: return
			player_move = await self._get_move(move_id)
			enemy_move_id = random.choice([m["id"] for m in self.wild.moves if m["pp"] > 0] or ["__struggle__"])
			enemy_move = _Struggle() if enemy_move_id == "__struggle__" else await self._get_move(enemy_move_id)
			p_prio = getattr(player_move,"priority",0) or 0 if player_move else 0
			e_prio = getattr(enemy_move,"priority",0) or 0 if enemy_move else 0
			order = ["player","enemy"] if p_prio>e_prio or (p_prio==e_prio and self.player_active.eff_stat("speed")>self.wild.eff_stat("speed")) else ["enemy","player"]
			lines = []
			for side in order:
				if self.player_active.fainted or self.wild.fainted: continue
				lines.extend(await self._act(side=="player", move_id if side=="player" else enemy_move_id, player_move if side=="player" else enemy_move))
				if self.wild.fainted: await self._on_enemy_defeated(); self.lines = lines; await self.refresh(); return
				if self.player_active.fainted: await self._on_player_fainted(); self.lines = lines; await self.refresh(); return
			lines.extend(self._end_of_turn_effects())
			if self.wild.fainted: await self._on_enemy_defeated()
			elif self.player_active.fainted: await self._on_player_fainted()
			if not self.ended: self.turn += 1
			self.lines = lines
			await self.refresh()
	async def switch_active(self, new_index: int, consume_turn: bool = True):
		async with self.lock:
			if self.ended or new_index == self.active_player_idx or not (0<=new_index<len(self.player_team)) or self.player_team[new_index].fainted: return
			self.active_player_idx = new_index
			self.must_redraw_image = True
			lines = [f"Você trocou para {self.player_active.name.title()}!"]
			if consume_turn:
				enemy_move_id = random.choice([m["id"] for m in self.wild.moves if m["pp"] > 0] or ["__struggle__"])
				lines.extend(await self._act(False, enemy_move_id, await self._get_move(enemy_move_id)))
				lines.extend(self._end_of_turn_effects())
				if self.player_active.fainted: await self._on_player_fainted()
				if not self.ended: self.turn += 1
			self.lines = lines
			await self.refresh()
	async def attempt_capture(self) -> bool:
		if self.player_active.fainted:
			self.lines = ["Troque de Pokémon antes de tentar capturar."]
			if self.actions_view: self.actions_view.force_switch_mode = True
			await self.refresh()
			return False
		if random.randint(1, 100) <= (max(5, 50-(self.wild.level//2)) + (10 if self.wild.is_shiny else 0)):
			xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
			pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
			pm.repo.tk.add_pokemon(owner_id=self.user_id, **self.wild_raw)
			self.ended = True
			self.lines = [f"Captura bem-sucedida! {self.player_active.name.title()} ganhou {xp} XP."]
			if self.actions_view: self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send(f"🎉 Capturou {self.wild.name.title()}! ⭐ {self.player_active.name.title()} recebeu {xp} XP.")
			return True
		else:
			lines = ["A Pokébola balançou... mas o Pokémon escapou!"]
			enemy_move_id = random.choice([m["id"] for m in self.wild.moves if m["pp"] > 0] or ["__struggle__"])
			lines.extend(await self._act(False, enemy_move_id, await self._get_move(enemy_move_id)))
			lines.extend(self._end_of_turn_effects())
			if self.player_active.fainted: await self._on_player_fainted()
			if not self.ended: self.turn += 1
			self.lines = lines
			await self.refresh()
			return False
	async def _on_enemy_defeated(self):
		xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
		pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
		self.ended = True
		self.lines = [f"O Pokémon selvagem caiu! {self.player_active.name.title()} ganhou {xp} XP."]
		if self.actions_view: self.actions_view.disable_all()
		await self.refresh()
		await self.interaction.channel.send(f"🏆 Vitória! ⭐ {self.player_active.name.title()} recebeu {xp} XP.")
	async def _on_player_fainted(self):
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
			label, pp, pp_max = mv["id"].replace("-"," ").title(), mv["pp"], mv["pp_max"]
			btn = discord.ui.Button(style=discord.ButtonStyle.primary, label=f"{label} ({pp}/{pp_max})", disabled=pp<=0)
			btn.callback = self._make_cb(mv["id"])
			self.add_item(btn)
		back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
		async def back_cb(i: discord.Interaction):
			if str(i.user.id) != battle.user_id: return await i.response.send_message("Não é sua batalha!", ephemeral=True)
			await i.response.edit_message(view=battle.actions_view)
		back.callback = back_cb
		self.add_item(back)
	def _make_cb(self, move_id: str):
		async def _cb(i: discord.Interaction):
			if str(i.user.id)!=self.battle.user_id: return await i.response.send_message("Não é sua batalha!",ephemeral=True)
			if self.battle.ended: return await i.response.send_message("A batalha já terminou.",ephemeral=True)
			if getattr(self.battle.actions_view,"force_switch_mode",False): return await i.response.send_message("Troque de Pokémon!",ephemeral=True)
			await i.response.defer()
			await self.battle.handle_player_move(move_id)
		return _cb

class SwitchView(discord.ui.View):
	def __init__(self, battle: WildBattle, force_only: bool = False, timeout: float = 60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		for i, p in enumerate(battle.player_team):
			label = f"{i+1}. {p.name.title()} (HP {max(0,p.current_hp)}/{p.stats['hp']})"
			btn = discord.ui.Button(style=discord.ButtonStyle.success, label=label, disabled=p.fainted or i==battle.active_player_idx)
			btn.callback = self._make_cb(i)
			self.add_item(btn)
		if not force_only:
			back = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Voltar")
			async def back_cb(i: discord.Interaction):
				if str(i.user.id)!=battle.user_id: return await i.response.send_message("Não é sua batalha!",ephemeral=True)
				await i.response.edit_message(view=battle.actions_view)
			back.callback = back_cb
			self.add_item(back)
	def _make_cb(self, idx: int):
		async def _cb(i: discord.Interaction):
			if str(i.user.id)!=self.battle.user_id: return await i.response.send_message("Não é sua batalha!",ephemeral=True)
			if self.battle.ended: return await i.response.send_message("A batalha já terminou.",ephemeral=True)
			await i.response.defer()
			consume = not getattr(self.battle.actions_view,"force_switch_mode",False)
			await self.battle.switch_active(idx, consume_turn=consume)
			if getattr(self.battle.actions_view,"force_switch_mode",False): self.battle.actions_view.force_switch_mode = False
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
		if str(i.user.id)!=self.user_id or self.battle.ended: return
		await i.response.edit_message(view=SwitchView(self.battle,True) if self.force_switch_mode else MovesView(self.battle))
	@discord.ui.button(style=discord.ButtonStyle.success, emoji="🔁", label="Trocar")
	async def switch(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id or self.battle.ended: return
		await i.response.edit_message(view=SwitchView(self.battle))
	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
	async def capture(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id)!=self.user_id or self.battle.ended: return
		if self.force_switch_mode or self.battle.player_active.fainted: return await i.response.send_message("Troque de Pokémon!",ephemeral=True)
		await i.response.defer()
		await self.battle.attempt_capture()

