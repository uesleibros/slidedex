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

def _stage_multiplier(stage: int) -> float:
	if stage >= 0:
		return (2 + stage) / 2
	return 2 / (2 - stage)

STAT_ALIASES = {
	"atk": ["atk", "attack"],
	"def": ["def", "defense"],
	"sp_atk": ["sp_atk", "spa", "special-attack", "spatk", "sp_att", "spatt"],
	"sp_def": ["sp_def", "spd", "special-defense", "spdef", "sp_defense"],
	"speed": ["speed", "spe"]
}

def _get_stat_value(stats: Dict[str, int], canonical: str) -> int:
	for name in STAT_ALIASES.get(canonical, []):
		if name in stats:
			return int(stats[name])
	if canonical in stats:
		return int(stats[canonical])
	raise KeyError(f"stat {canonical}")

def _apply_stage(stat_base: int, stage: int) -> int:
	return max(1, int(stat_base * _stage_multiplier(stage)))

def _has_type(poke: "BattlePokemon", type_name: str) -> bool:
	try:
		return any(t.type.name.lower() == type_name.lower() for t in poke.pokeapi_data.types)
	except Exception:
		return False

class _Struggle:
	power = 50
	accuracy = None
	priority = 0
	damage_class = type("dc", (), {"name": "physical"})
	type = type("tp", (), {"name": "normal"})
	name = "Struggle"

class _FakeMove:
	def __init__(self, name="Tackle", power=40, accuracy=100, priority=0, dmg="physical", type_name="normal"):
		self.name = name
		self.power = power
		self.accuracy = accuracy
		self.priority = priority
		self.damage_class = type("dc", (), {"name": dmg})
		self.type = type("tp", (), {"name": type_name})
		self.stat_changes = []
		self.effect_chance = None

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
		return _apply_stage(base, self.stages[key])

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
		self.last_lines: List[str] = []

	@property
	def player_active(self) -> BattlePokemon:
		return self.player_team[self.active_player_idx]

	async def setup(self):
		pokeapi_wild: aiopoke.Pokemon = await pm.service.get_pokemon(self.wild_raw["species_id"])
		self.wild = BattlePokemon(self.wild_raw, pokeapi_wild)
		for p in self.player_party_raw:
			api_p = await pm.service.get_pokemon(p["species_id"])
			self.player_team.append(BattlePokemon(p, api_p))

	async def _compose_image_once(self):
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
		return f"Lv{p.level} {emoji} {p.name.title()} (HP {max(0, p.current_hp)}/{p.stats['hp']}) {'*Wild*' if is_enemy else ''}"

	def _desc(self) -> str:
		top = self._hp_line(self.player_active, is_enemy=False)
		bot = self._hp_line(self.wild, is_enemy=True)
		lines = [top, "VS", bot]
		if self.last_lines:
			lines.append("")
			lines.extend(self.last_lines[-2:])
		return "\n".join(lines)

	def _embed(self) -> discord.Embed:
		embed = discord.Embed(title=f"Luta - Turno {self.turn}", description=self._desc(), color=discord.Color.green())
		embed.set_image(url="attachment://battle.png")
		return embed

	async def start(self):
		file = await self._compose_image_once()
		self.actions_view = WildBattleView(self)
		self.last_lines = ["A batalha começou!"]
		embed = self._embed()
		self.message = await self.interaction.channel.send(embed=embed, file=file, view=self.actions_view)

	async def refresh(self):
		if not self.message:
			return
		embed = self._embed()
		await self.message.edit(embed=embed, view=self.actions_view)

	async def _get_move(self, move_id: str):
		key = str(move_id).strip().lower()
		try:
			return await pm.service.get_move(key)
		except Exception:
			try:
				if key.isdigit():
					return await pm.service.get_move(int(key))
			except Exception:
				return None
		return None

	async def _apply_status_effects(self, user: BattlePokemon, target: BattlePokemon, move) -> Optional[str]:
		try:
			if move.damage_class.name != "status":
				return None
		except Exception:
			return None
		txts = []
		sc = getattr(move, "stat_changes", []) or []
		eff_chance = getattr(move, "effect_chance", None)
		if eff_chance is not None and random.randint(1, 100) > int(eff_chance):
			return "Sem efeito."
		for s in sc:
			raw_name = s.stat.name
			delta = int(s.change)
			canonical = {
				"attack": "atk",
				"defense": "def",
				"special-attack": "sp_atk",
				"special-defense": "sp_def",
				"speed": "speed"
			}.get(raw_name)
			if not canonical:
				continue
			tgt = user if delta > 0 else target
			tgt.stages[canonical] = max(-6, min(6, tgt.stages[canonical] + delta))
			who = "Você" if tgt is user else "Inimigo"
			what = {"atk": "Ataque", "def": "Defesa", "sp_atk": "Ataque Especial", "sp_def": "Defesa Especial", "speed": "Velocidade"}[canonical]
			arrow = "↑" if delta > 0 else "↓"
			txts.append(f"{who}: {what} {arrow} ({tgt.stages[canonical]})")
		return "\n".join(txts) if txts else "Nada aconteceu."

	async def _calc_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move) -> int:
		power = getattr(move, "power", None) or 0
		if power <= 0:
			return 0
		dmg_class = getattr(move.damage_class, "name", "physical")
		if dmg_class == "special":
			atk_stat = attacker.eff_stat("sp_atk")
			def_stat = defender.eff_stat("sp_def")
		else:
			atk_stat = attacker.eff_stat("atk")
			def_stat = defender.eff_stat("def")
		level = attacker.level
		base = (((2 * level / 5) + 2) * power * (atk_stat / max(1, def_stat))) / 50 + 2
		stab = 1.5 if _has_type(attacker, move.type.name) else 1.0
		rand = random.uniform(0.9, 1.0)
		crit = 1.5 if random.random() < 0.0625 else 1.0
		damage = int(base * stab * rand * crit)
		return max(1, damage)

	async def _use_move(self, user: BattlePokemon, target: BattlePokemon, move, move_id_for_pp: Optional[str]) -> str:
		if move is None:
			move = _FakeMove()
		mname = getattr(move, "name", "Golpe").replace("-", " ").title()
		if move_id_for_pp and move_id_for_pp != "__struggle__":
			pp = user.get_pp(move_id_for_pp)
			if pp is not None and pp <= 0:
				return f"{user.name.title()} tentou usar {mname}, mas não tem PP!"
			user.dec_pp(move_id_for_pp)
		acc = getattr(move, "accuracy", None)
		hit = True if (acc is None or int(acc) <= 0) else (random.randint(1, 100) <= int(acc))
		if not hit:
			return f"{user.name.title()} usou {mname}, mas errou!"
		damage = await self._calc_damage(user, target, move)
		if damage > 0:
			target.current_hp = max(0, target.current_hp - damage)
			return f"{user.name.title()} usou {mname}! Dano {damage}."
		eff_txt = await self._apply_status_effects(user, target, move)
		return f"{user.name.title()} usou {mname}! {eff_txt or ''}".strip()

	def _next_alive_index(self) -> Optional[int]:
		for i, p in enumerate(self.player_team):
			if not p.fainted:
				return i
		return None

	def _enemy_choose_move_id(self) -> str:
		moves = [m for m in self.wild.list_moves() if int(m.get("pp", 0)) > 0]
		if moves:
			return str(random.choice(moves)["id"])
		return "__struggle__"

	async def handle_player_move(self, move_id: str):
		async with self.lock:
			if self.ended:
				return
			player_move = await self._get_move(move_id) or _FakeMove()
			enemy_move_id = self._enemy_choose_move_id()
			enemy_move = _Struggle() if enemy_move_id == "__struggle__" else (await self._get_move(enemy_move_id) or _FakeMove())
			p_prio = int(getattr(player_move, "priority", 0) or 0)
			e_prio = int(getattr(enemy_move, "priority", 0) or 0)
			player_speed = self.player_active.eff_stat("speed")
			enemy_speed = self.wild.eff_stat("speed")
			order = []
			if p_prio > e_prio:
				order = ["player", "enemy"]
			elif e_prio > p_prio:
				order = ["enemy", "player"]
			else:
				if player_speed > enemy_speed:
					order = ["player", "enemy"]
				elif enemy_speed > player_speed:
					order = ["enemy", "player"]
				else:
					order = random.choice([["player", "enemy"], ["enemy", "player"]])
			lines = []
			for side in order:
				if side == "player":
					if self.player_active.fainted or self.wild.fainted:
						continue
					lines.append(await self._use_move(self.player_active, self.wild, player_move, move_id))
					if self.wild.fainted:
						await self._on_enemy_defeated()
						self.last_lines = lines[-2:]
						await self.refresh()
						return
				else:
					if self.player_active.fainted or self.wild.fainted:
						continue
					lines.append(await self._use_move(self.wild, self.player_active, enemy_move, enemy_move_id))
					if self.player_active.fainted:
						await self._on_player_fainted()
						self.last_lines = lines[-2:]
						await self.refresh()
						return
			self.turn += 1
			self.last_lines = lines[-2:]
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
			lines = [f"Você trocou para {self.player_active.name.title()}!"]
			if consume_turn:
				enemy_move_id = self._enemy_choose_move_id()
				enemy_move = _Struggle() if enemy_move_id == "__struggle__" else (await self._get_move(enemy_move_id) or _FakeMove())
				lines.append(await self._use_move(self.wild, self.player_active, enemy_move, enemy_move_id))
				if self.player_active.fainted:
					await self._on_player_fainted()
					self.last_lines = lines[-2:]
					await self.refresh()
					return
				self.turn += 1
			self.last_lines = lines[-2:]
			await self.refresh()

	async def attempt_capture(self) -> bool:
		level = self.wild_raw.get("level", 10)
		base_chance = max(5, 50 - (level // 2))
		if self.wild_raw.get("is_shiny"):
			base_chance += 10
		roll = random.randint(1, 100)
		if roll <= base_chance:
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
			self.last_lines = [f"Captura bem-sucedida! {self.player_active.name.title()} ganhou {xp_gain} XP."]
			if self.actions_view:
				for item in self.actions_view.children:
					item.disabled = True
			return True
		else:
			enemy_move_id = self._enemy_choose_move_id()
			enemy_move = _Struggle() if enemy_move_id == "__struggle__" else (await self._get_move(enemy_move_id) or _FakeMove())
			line1 = "A Pokébola balançou... e o Pokémon escapou!"
			line2 = await self._use_move(self.wild, self.player_active, enemy_move, enemy_move_id)
			if self.player_active.fainted:
				await self._on_player_fainted()
			self.turn += 1
			self.last_lines = [line1, line2]
			await self.refresh()
			return False

	async def _on_enemy_defeated(self):
		xp_gain = pm.repo.tk.calc_battle_exp(self.player_active.level, self.wild.level)
		pm.repo.tk.add_exp(self.user_id, self.player_party_raw[self.active_player_idx]["id"], xp_gain)
		self.ended = True
		self.last_lines = [f"O Pokémon selvagem caiu! {self.player_active.name.title()} ganhou {xp_gain} XP."]
		if self.actions_view:
			for item in self.actions_view.children:
				item.disabled = True

	async def _on_player_fainted(self):
		next_idx = None
		for i, p in enumerate(self.player_team):
			if not p.fainted:
				next_idx = i
				break
		if next_idx is None:
			self.ended = True
			self.last_lines = ["Seus Pokémon desmaiaram. Derrota!"]
			if self.actions_view:
				for item in self.actions_view.children:
					item.disabled = True
			return
		if self.actions_view:
			self.actions_view.force_switch_mode = True
		self.last_lines = ["Seu Pokémon desmaiou! Escolha outro."]

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
		await interaction.response.defer()
		success = await self.battle.attempt_capture()
		if self.battle.ended:
			for item in self.children:
				item.disabled = True
		await self.battle.refresh()
		if success:
			await self.battle.interaction.channel.send("🎉 Captura realizada!")
