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
		self.stages = {"atk":0,"def":0,"sp_atk":0,"sp_def":0,"speed":0,"accuracy":0,"evasion":0}
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
		val = _apply_stage(_get_stat(self.stats, key), self.stages.get(key, 0))
		if key == "speed" and self.status["name"] == "paralysis":
			val = int(val * 0.5)
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

	def set_status(self, name: str, turns: Optional[int] = None) -> bool:
		if self.status["name"]:
			return False
		self.status = {
			"name": name,
			"counter": turns if turns is not None else (random.randint(1, 3) if name == "sleep" else 0)
		}
		return True

	def status_tag(self) -> str:
		tags = {"burn": "BRN", "poison": "PSN", "paralysis": "PAR", "sleep": "SLP", "freeze": "FRZ", "toxic": "TOX"}
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
		self.effect_cache: Dict[str, Dict[str, Any]] = {}

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
		return f"{emoji} {p.name.title()}{p.status_tag()} Lv{p.level}\n{bar} {max(0, p.current_hp)}/{p.stats['hp']}"

	def _embed(self) -> discord.Embed:
		desc = f"{self._hp_line(self.player_active)}\nvs\n{self._hp_line(self.wild)}\n\n"
		desc += "\n".join(self.lines) if self.lines else ""
		embed = discord.Embed(title=f"Batalha Selvagem - Turno {self.turn}", description=desc, color=discord.Color.green())
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
		key = _slug(move_id)
		return self.effect_cache.get(key, {})

	def _pre_action(self, user: BattlePokemon) -> Tuple[bool, List[str]]:
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

	def _confusion(self, user: BattlePokemon) -> Tuple[bool, List[str]]:
		if user.volatile["confuse"] <= 0:
			return False, []
		user.volatile["confuse"] -= 1
		if user.volatile["confuse"] == 0:
			return False, [f"{user.name.title()} não está mais confuso!"]
		if random.random() < 0.33:
			lv = user.level
			atk = user.eff_stat("atk")
			df = user.eff_stat("def")
			base = (((2 * lv / 5) + 2) * 40 * (atk / max(1, df))) / 50 + 2
			dmg = max(1, int(base * random.uniform(0.85, 1.0)))
			user.current_hp = max(0, user.current_hp - dmg)
			return True, [f"{user.name.title()} está confuso e se atingiu, causando {dmg} de dano."]
		return False, [f"{user.name.title()} está confuso..."]

	def _apply_effect(self, user: BattlePokemon, target: BattlePokemon, effect: Dict[str, Any], damage_dealt: int) -> List[str]:
		lines = []
		eff_type = effect.get("type")
		chance = effect.get("chance", 100)
		tgt = effect.get("target", "opponent")
		
		if chance < 100 and random.randint(1, 100) > chance:
			return lines

		actual_target = user if tgt == "self" else target

		if eff_type == "stat_change":
			stat = effect.get("stat")
			stages = effect.get("stages", 0)
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
			if mapped_stat in actual_target.stages:
				old = actual_target.stages[mapped_stat]
				actual_target.stages[mapped_stat] = max(-6, min(6, actual_target.stages[mapped_stat] + stages))
				if actual_target.stages[mapped_stat] != old:
					stat_names = {
						"atk": "Ataque",
						"def": "Defesa",
						"sp_atk": "Ataque Especial",
						"sp_def": "Defesa Especial",
						"speed": "Velocidade",
						"accuracy": "Precisão",
						"evasion": "Evasão"
					}
					lines.append(f"{actual_target.name.title()}: {stat_names.get(mapped_stat, mapped_stat)} {'↑' if stages > 0 else '↓'}")

		elif eff_type in ["burn", "poison", "paralysis", "sleep", "freeze"]:
			tt = _types_of(actual_target)
			can_apply = True
			if eff_type == "burn" and "fire" in tt:
				can_apply = False
			elif eff_type == "poison" and ("steel" in tt or "poison" in tt):
				can_apply = False
			elif eff_type == "freeze" and "ice" in tt:
				can_apply = False
			
			if can_apply and actual_target.set_status(eff_type):
				texts = {
					"burn": "foi queimado",
					"poison": "foi envenenado",
					"paralysis": "ficou paralisado",
					"sleep": "adormeceu",
					"freeze": "foi congelado"
				}
				lines.append(f"{actual_target.name.title()} {texts[eff_type]}!")

		elif eff_type == "toxic":
			tt = _types_of(actual_target)
			if "steel" not in tt and "poison" not in tt:
				if actual_target.set_status("toxic"):
					lines.append(f"{actual_target.name.title()} foi gravemente envenenado!")

		elif eff_type == "confusion":
			actual_target.volatile["confuse"] = max(actual_target.volatile["confuse"], random.randint(2, 4))
			lines.append(f"{actual_target.name.title()} ficou confuso!")

		elif eff_type == "flinch":
			actual_target.volatile["flinch"] = True
			lines.append(f"{actual_target.name.title()} recuou!")

		elif eff_type == "heal":
			amount = effect.get("amount", 0.5)
			heal = max(1, int(user.stats["hp"] * amount))
			user.current_hp = min(user.stats["hp"], user.current_hp + heal)
			lines.append(f"{user.name.title()} recuperou {heal} HP!")

		return lines

	def _apply_recoil(self, user: BattlePokemon, recoil: float, damage: int) -> List[str]:
		if recoil <= 0 or damage <= 0:
			return []
		recoil_dmg = max(1, int(damage * recoil))
		user.current_hp = max(0, user.current_hp - recoil_dmg)
		return [f"{user.name.title()} sofreu {recoil_dmg} de recuo!"]

	def _apply_drain(self, user: BattlePokemon, drain: float, damage: int) -> List[str]:
		if drain <= 0 or damage <= 0:
			return []
		heal_amt = max(1, int(damage * drain))
		user.current_hp = min(user.stats["hp"], user.current_hp + heal_amt)
		return [f"{user.name.title()} drenou {heal_amt} HP!"]

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
				return [f"{user.name.title()} não tem mais PP para {md.name}!"]
			user.dec_pp(move_id_for_pp)

		effect_data = self._get_effect_data(move_id_for_pp or "tackle")
		
		if md.accuracy is not None and not effect_data.get("bypass_accuracy", False):
			if random.randint(1, 100) > int(md.accuracy):
				return [f"{user.name.title()} usou {md.name}, mas errou!"]

		if not effect_data.get("damage", True) and md.dmg_class == "status":
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
				lines.append(f"{user.name.title()} usou {md.name}! Não teve efeito.")
				return lines

			if target.status["name"] == "freeze" and md.type_name.lower() == "fire" and dmg > 0:
				target.status = {"name": None, "counter": 0}
				lines.append(f"{target.name.title()} descongelou!")

			target.current_hp = max(0, target.current_hp - dmg)
			total_damage += dmg

			if target.fainted:
				break

		txt = f"{user.name.title()} usou {md.name}!"
		if total_damage > 0:
			txt += f" Causou {total_damage} de dano."
		if hits > 1:
			txt += f" Acertou {hits} vezes."
		if first_crit:
			txt += " Acerto crítico!"
		if first_tm > 1.0:
			txt += " É super eficaz!"
		elif 0 < first_tm < 1.0:
			txt += " Não foi muito eficaz..."
		lines.append(txt)

		if effect_data.get("recoil"):
			lines.extend(self._apply_recoil(user, effect_data["recoil"], total_damage))

		if effect_data.get("drain"):
			lines.extend(self._apply_drain(user, effect_data["drain"], total_damage))

		for effect in effect_data.get("effects", []):
			lines.extend(self._apply_effect(user, target, effect, total_damage))

		return lines

	async def _apply_status_move(self, user: BattlePokemon, target: BattlePokemon, md: MoveData, effect_data: Dict[str, Any]) -> List[str]:
		lines = [f"{user.name.title()} usou {md.name}!"]
		changed = False

		for effect in effect_data.get("effects", []):
			result = self._apply_effect(user, target, effect, 0)
			if result:
				changed = True
				lines.extend(result)

		if not changed and not effect_data.get("effects"):
			lines.append("Mas não surtiu efeito.")

		return lines

	def _end_of_turn(self) -> List[str]:
		lines = []
		for p, who in [(self.player_active, "Seu"), (self.wild, "O selvagem")]:
			if p.fainted:
				continue
			
			status = p.status["name"]
			if status == "burn":
				d = max(1, p.stats["hp"] // 16)
				p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano da queimadura.")
			elif status == "poison":
				d = max(1, p.stats["hp"] // 8)
				p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano do veneno.")
			elif status == "toxic":
				p.status["counter"] += 1
				d = max(1, (p.stats["hp"] // 16) * p.status["counter"])
				p.current_hp = max(0, p.current_hp - d)
				lines.append(f"{who} {p.name.title()} sofreu {d} de dano do envenenamento grave.")

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

			pmd = await self._fetch_move(move_id)
			eid = self._enemy_pick()
			
			if eid != "__struggle__":
				emd = await self._fetch_move(eid)
			else:
				emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])

			if pmd.priority != emd.priority:
				order = ["player", "enemy"] if pmd.priority > emd.priority else ["enemy", "player"]
			else:
				ps = self.player_active.eff_stat("speed")
				es = self.wild.eff_stat("speed")
				if ps > es:
					order = ["player", "enemy"]
				elif es > ps:
					order = ["enemy", "player"]
				else:
					order = random.choice([["player", "enemy"], ["enemy", "player"]])

			lines = []
			for side in order:
				if self.player_active.fainted or self.wild.fainted:
					continue

				if side == "player":
					lines += await self._act(True, move_id, pmd)
					if self.wild.fainted:
						await self._on_win()
						self.lines = lines
						await self.refresh()
						return
				else:
					lines += await self._act(False, eid, emd)
					if self.player_active.fainted:
						await self._on_faint()
						self.lines = lines
						await self.refresh()
						return

			lines += self._end_of_turn()

			if self.wild.fainted:
				await self._on_win()
			elif self.player_active.fainted:
				await self._on_faint()

			if not self.ended:
				self.turn += 1

			self.lines = lines
			await self.refresh()

	async def switch_active(self, new_index: int, consume_turn: bool = True):
		async with self.lock:
			if self.ended:
				return
			if new_index == self.active_player_idx:
				return
			if not (0 <= new_index < len(self.player_team)):
				return
			if self.player_team[new_index].fainted:
				return

			self.active_player_idx = new_index
			self.must_redraw_image = True
			lines = [f"Você trocou para {self.player_active.name.title()}!"]

			if consume_turn:
				eid = self._enemy_pick()
				if eid != "__struggle__":
					emd = await self._fetch_move(eid)
				else:
					emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])
				
				lines += await self._act(False, eid, emd)
				lines += self._end_of_turn()

				if self.player_active.fainted:
					await self._on_faint()

				if not self.ended:
					self.turn += 1

			self.lines = lines
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
			self.lines = ["Seu Pokémon desmaiou! Troque antes de capturar."]
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
			self.lines = [f"Captura bem-sucedida! {self.player_active.name.title()} ganhou {xp} XP."]
			if self.actions_view:
				self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send(
				f"🎉 Capturou {self.wild.name.title()}! ⭐ {self.player_active.name.title()} recebeu {xp} XP."
			)
			return True
		else:
			msg = "A Pokébola balançou " + (f"{shakes}x e " if shakes > 0 else "") + "o Pokémon escapou!"
			lines = [msg]
			
			eid = self._enemy_pick()
			if eid != "__struggle__":
				emd = await self._fetch_move(eid)
			else:
				emd = MoveData("Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, [])
			
			lines += await self._act(False, eid, emd)
			lines += self._end_of_turn()

			if self.player_active.fainted:
				await self._on_faint()

			if not self.ended:
				self.turn += 1

			self.lines = lines
			await self.refresh()
			return False

	async def _on_win(self):
		xp = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
		pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp)
		self.ended = True
		self.lines = [f"O Pokémon selvagem caiu! {self.player_active.name.title()} ganhou {xp} XP."]
		if self.actions_view:
			self.actions_view.disable_all()
		await self.refresh()
		await self.interaction.channel.send(
			f"🏆 Vitória! ⭐ {self.player_active.name.title()} recebeu {xp} XP."
		)

	async def _on_faint(self):
		if not any(not p.fainted for p in self.player_team):
			self.ended = True
			self.lines = ["Todos os seus Pokémon desmaiaram. Derrota!"]
			if self.actions_view:
				self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send("💀 Você foi derrotado...")
			return

		if self.actions_view:
			self.actions_view.force_switch_mode = True
		self.lines = ["Seu Pokémon desmaiou! Escolha outro."]

class WildBattleView(discord.ui.View):
	def __init__(self, battle: WildBattle, timeout=60.0):
		super().__init__(timeout=timeout)
		self.battle = battle
		self.user_id = battle.user_id
		self.force_switch_mode = False

	def disable_all(self):
		for item in self.children:
			item.disabled = True

	@discord.ui.button(style=discord.ButtonStyle.primary, label="Lutar")
	async def fight(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id:
			return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode:
			return await i.response.edit_message(view=SwitchView(self.battle, force_only=True))
		await i.response.edit_message(view=MovesView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.primary, label="Trocar")
	async def switch(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id:
			return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		await i.response.edit_message(view=SwitchView(self.battle))

	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
	async def capture(self, i: discord.Interaction, b: discord.ui.Button):
		if str(i.user.id) != self.user_id:
			return await i.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await i.response.send_message("A batalha já terminou.", ephemeral=True)
		if self.force_switch_mode or self.battle.player_active.fainted:
			return await i.response.send_message("Troque de Pokémon!", ephemeral=True)
		await i.response.defer()
		await self.battle.attempt_capture()
