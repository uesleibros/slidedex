import discord
import random
import asyncio
from __main__ import pm, battle_tracker
from typing import List, Dict, Any, Optional, Set, Tuple
from utils.canvas import compose_battle_async
from utils.preloaded import preloaded_textures
from utils.formatting import format_pokemon_display
from .pokemon import BattlePokemon
from .constants import BattleConstants
from .messages import BattleMessages
from .damage import DamageCalculator
from .effects import EffectHandler
from .status import StatusHandler
from .capture import CaptureSystem
from .helpers import SwitchView, MovesView, MoveData, _normalize_move, _hp_bar, _slug
from .pokeballs import PokeBallSystem, BallType

class WildBattle:
	__slots__ = (
		'user_id', 'interaction', 'player_party_raw', 'active_player_idx',
		'wild_raw', 'ended', 'turn', 'message', 'lock', 'player_team',
		'wild', 'actions_view', 'lines', 'must_redraw_image', 'move_cache',
		'effect_cache', 'weather', 'field', 'damage_calculator', 'effect_handler',
		'ball_type', 'location_type', 'time_of_day', 'battle_participants'
	)
	
	def __init__(
		self,
		player_party: List[Dict[str, Any]],
		wild: Dict[str, Any],
		user_id: str,
		interaction: discord.Interaction
	) -> None:
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
		self.weather = {"type": None, "turns": 0}
		self.field = {"spikes_player": 0, "spikes_wild": 0, "trick_room": 0, "gravity": 0}
		self.damage_calculator = DamageCalculator(self.weather)
		self.effect_handler = EffectHandler()
		self.ball_type = BallType.POKE_BALL
		self.location_type = "normal"
		self.time_of_day = "day"
		self.battle_participants: Set[int] = set()
	
	@property
	def player_active(self) -> BattlePokemon:
		return self.player_team[self.active_player_idx]
	
	def _find_first_available_pokemon(self) -> Optional[int]:
		for idx, pokemon in enumerate(self.player_team):
			if not pokemon.fainted:
				return idx
		return None
	
	def _validate_party(self) -> bool:
		return any(not p.fainted for p in self.player_team)
	
	async def setup(self) -> bool:
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
		
		if not self._validate_party():
			await self.interaction.followup.send(
				"Todos os seus Pokémon estão desmaiados!\n"
				"Cure-os em um Centro Pokémon antes de batalhar.",
				ephemeral=True
			)
			return False
		
		first_available = self._find_first_available_pokemon()
		if first_available is None:
			await self.interaction.followup.send(
				"Nenhum Pokémon disponível para batalha!",
				ephemeral=True
			)
			return False
		
		self.active_player_idx = first_available
		
		await self._preload_move_data()
		return True
	
	async def _preload_move_data(self) -> None:
		move_ids: Set[str] = set()
		for mv in self.wild.moves:
			move_ids.add(_slug(mv["id"]))
		for p in self.player_team:
			for mv in p.moves:
				move_ids.add(_slug(mv["id"]))
		
		if move_ids:
			await asyncio.gather(*[self._fetch_move(mid) for mid in move_ids if mid])
	
	async def _compose_image(self) -> discord.File:
		pb = await self.player_active.sprites["back"].read() if self.player_active.sprites["back"] else None
		ef = await self.wild.sprites["front"].read() if self.wild.sprites["front"] else None
		buf = await compose_battle_async(pb, ef, preloaded_textures["battle"])
		return discord.File(buf, filename="battle.png")
	
	def _generate_hp_display(self, pokemon: BattlePokemon) -> str:
		bar = _hp_bar(pokemon.current_hp, pokemon.stats["hp"])
		hp_percent = (pokemon.current_hp / pokemon.stats["hp"] * 100) if pokemon.stats["hp"] > 0 else 0
		base_display = (
			f"{format_pokemon_display(pokemon.raw, bold_name=True)} "
			f"{pokemon.status_tag()} Lv{pokemon.level}\n"
			f"{bar} {max(0, pokemon.current_hp)}/{pokemon.stats['hp']} ({hp_percent:.1f}%)"
		)

		stage_modifications = []
		if pokemon.stages.get("accuracy", 0) != 0:
			stage_modifications.append(f"ACC: {pokemon.stages['accuracy']:+d}")
		if pokemon.stages.get("evasion", 0) != 0:
			stage_modifications.append(f"EVA: {pokemon.stages['evasion']:+d}")
		
		if stage_modifications:
			base_display += f" [{' | '.join(stage_modifications)}]"
		
		return base_display
	
	def _build_embed(self) -> discord.Embed:
		description_components = [
			self._generate_hp_display(self.player_active),
			"**VS**",
			self._generate_hp_display(self.wild),
			""
		]
		
		weather_icons = {"sun": "☀️", "rain": "🌧️", "hail": "❄️", "sandstorm": "🌪️"}
		if self.weather["type"] and self.weather["turns"] > 0:
			icon = weather_icons.get(self.weather["type"], "🌤️")
			description_components.append(
				f"{icon} {self.weather['type'].title()} ({self.weather['turns']} turnos)"
			)
		
		field_status = []
		if self.field.get("trick_room", 0) > 0:
			field_status.append("🔄 Trick Room")
		if self.field.get("gravity", 0) > 0:
			field_status.append("⬇️ Gravity")
		
		if field_status:
			description_components.extend(field_status)
			description_components.append("")
		
		if self.lines:
			description_components.extend(self.lines[-15:])
		
		embed = discord.Embed(
			title=f"Batalha Selvagem - Turno {self.turn}",
			description="\n".join(description_components),
			color=discord.Color.green()
		)
		
		embed.set_footer(text="Effex Engine v1.4 — alpha")
		embed.set_image(url="attachment://battle.png")
		return embed
	
	async def start(self) -> None:
		self.battle_participants.add(self.active_player_idx)
		self.actions_view = WildBattleView(self)
		self.lines = [f"A batalha começou! Vamos lá, {self.player_active.display_name}!"]

		battle_tracker.add(self.user_id)
		self.message = await self.interaction.channel.send(
			embed=self._build_embed(),
			file=await self._compose_image(),
			view=self.actions_view
		)
		self.must_redraw_image = False

	async def _save_battle_state(self) -> None:
		for idx, pokemon in enumerate(self.player_team):
			pokemon_id = self.player_party_raw[idx]["id"]
			
			pm.repo.tk.set_current_hp(
				self.user_id,
				pokemon_id,
				pokemon.current_hp
			)
			
			pm.repo.tk.set_moves(
				self.user_id,
				pokemon_id,
				pokemon.moves
			)
	
	async def refresh(self) -> None:
		if not self.message:
			return
		
		embed = self._build_embed()

		await self._save_battle_state()
		
		if self.must_redraw_image:
			file = await self._compose_image()
			await self.message.edit(attachments=[file], embed=embed, view=self.actions_view)
			self.must_redraw_image = False
		else:
			await self.message.edit(embed=embed, view=self.actions_view)
	
	async def _fetch_move(self, move_id: str) -> MoveData:
		key = _slug(move_id)
		if not key:
			raise ValueError("Invalid move_id")
		
		if key in self.move_cache:
			return self.move_cache[key]
		
		move_data = await pm.service.get_move(key)
		normalized = _normalize_move(move_data)
		self.move_cache[key] = normalized
		
		from data.effect_mapper import effect_mapper
		effect_entries = getattr(move_data, "effect_entries", [])
		
		for entry in effect_entries:
			if entry.language.name == "en":
				self.effect_cache[key] = effect_mapper.get(entry.short_effect, {})
				break
		
		if key not in self.effect_cache:
			self.effect_cache[key] = {}
		
		return normalized
	
	def _get_effect_data(self, move_id: str) -> Dict[str, Any]:
		return self.effect_cache.get(_slug(move_id), {})
	
	async def _execute_move(
		self,
		user: BattlePokemon,
		target: BattlePokemon,
		move_data: MoveData,
		move_id: Optional[str]
	) -> List[str]:
		is_struggle = move_id == "__struggle__"
		
		if move_id and not is_struggle:
			pp = user.get_pp(move_id)
			if pp is not None and pp <= 0:
				return [f"❌ {user.display_name} não tem PP!"]
			user.dec_pp(move_id)
			user.volatile["last_move_used"] = move_id
		
		effect_data = self._get_effect_data(move_id or "tackle")
		
		if target.volatile.get("protect") and move_data.dmg_class != "status":
			return [BattleMessages.protected(target.display_name)]
		
		if move_data.accuracy is not None and not effect_data.get("bypass_accuracy", False):
			accuracy = move_data.accuracy
			if user.volatile.get("mind_reader_target") == target:
				accuracy = None
				user.volatile["mind_reader_target"] = None
			
			if accuracy is not None and random.randint(1, 100) > int(accuracy):
				return [BattleMessages.miss(user.display_name, move_data.name)]
		
		if move_data.dmg_class == "status" or move_data.power == 0:
			return await self._apply_status_move(user, target, move_data, effect_data)
		
		return await self._apply_damage_move(user, target, move_data, effect_data, is_struggle)
	
	async def _apply_damage_move(
		self,
		user: BattlePokemon,
		target: BattlePokemon,
		move_data: MoveData,
		effect_data: Dict[str, Any],
		is_struggle: bool
	) -> List[str]:
		lines = []
		multi_hit = effect_data.get("multi_hit", {})
		hits = 1
		
		if multi_hit:
			min_hits = multi_hit.get("min", 1)
			max_hits = multi_hit.get("max", 1)
			if max_hits > 1:
				hits = random.randint(min_hits, max_hits)
		
		total_damage = 0
		first_multiplier, first_crit = 1.0, False
		
		for i in range(hits):
			if target.fainted:
				break
			
			damage, multiplier, is_crit = await self.damage_calculator.calculate(
				user, target, move_data, effect_data
			)
			
			if i == 0:
				first_multiplier, first_crit = multiplier, is_crit
			
			if multiplier == 0.0 and not is_struggle:
				return [BattleMessages.no_effect(user.display_name, move_data.name)]
			
			if target.status["name"] == "freeze" and move_data.type_name.lower() == "fire" and damage > 0:
				target.status = {"name": None, "counter": 0}
				lines.append(f"🔥 {target.display_name} descongelou!")
			
			actual_damage = target.take_damage(damage)
			total_damage += actual_damage
			
			if target.fainted:
				if target.volatile.get("destiny_bond"):
					user.current_hp = 0
					lines.append(f"👻 Destiny Bond ativado! {user.display_name} também caiu!")
				break
		
		if is_struggle:
			lines.append(f"💢 {user.display_name} não tem PP!")
			lines.append(f"Usou **Struggle**! ({total_damage} de dano)")
		else:
			lines.append(BattleMessages.damage(user.display_name, move_data.name, total_damage))
		
		detail_line = BattleMessages.details(hits if hits > 1 else None, first_crit, first_multiplier)
		if detail_line:
			lines.append(detail_line)
		
		if target.fainted:
			lines.append(BattleMessages.fainted(target.display_name))
		
		recoil_damage = self._calculate_recoil(total_damage, effect_data, is_struggle, user)
		if recoil_damage:
			lines.append(recoil_damage)
		
		drain_healing = self._calculate_drain(total_damage, effect_data, user)
		if drain_healing:
			lines.append(drain_healing)
		
		for effect in effect_data.get("effects", []):
			effect_results = self.effect_handler.apply_effect(user, target, effect, total_damage)
			if effect_results:
				lines.extend(effect_results)
		
		return lines
	
	def _calculate_recoil(
		self,
		total_damage: int,
		effect_data: Dict[str, Any],
		is_struggle: bool,
		user: BattlePokemon
	) -> Optional[str]:
		if is_struggle:
			recoil = max(1, int(user.stats["hp"] * BattleConstants.STRUGGLE_RECOIL_RATIO))
			actual = user.take_damage(recoil, ignore_substitute=True)
			return BattleMessages.recoil(user.display_name, actual)
		
		if effect_data.get("recoil"):
			recoil = max(1, int(total_damage * effect_data["recoil"]))
			actual = user.take_damage(recoil, ignore_substitute=True)
			return BattleMessages.recoil(user.display_name, actual)
		
		return None
	
	def _calculate_drain(
		self,
		total_damage: int,
		effect_data: Dict[str, Any],
		user: BattlePokemon
	) -> Optional[str]:
		if effect_data.get("drain"):
			drain = max(1, int(total_damage * effect_data["drain"]))
			actual = user.heal(drain)
			if actual > 0:
				return BattleMessages.drain(user.display_name, actual)
		return None
	
	async def _apply_status_move(
		self,
		user: BattlePokemon,
		target: BattlePokemon,
		move_data: MoveData,
		effect_data: Dict[str, Any]
	) -> List[str]:
		lines = [f"✨ {user.display_name} usou **{move_data.name}**!"]
		has_effect = False
		
		effects = effect_data.get("effects", [])
		
		if effects:
			for effect in effects:
				result = self.effect_handler.apply_effect(user, target, effect, 0)
				if result:
					has_effect = True
					lines.extend(result)
		elif move_data.stat_changes:
			for stat_change in move_data.stat_changes:
				stat, stages = stat_change[0], stat_change[1]
				is_self_buff = stat_change[2] if len(stat_change) > 2 else (stages > 0)
				
				affected_pokemon = user if is_self_buff else target
				effect = {"type": "stat_change", "stat": stat, "stages": stages}
				result = self.effect_handler.apply_effect(user, affected_pokemon, effect, 0)
				if result:
					has_effect = True
					lines.extend(result)
		
		if not has_effect:
			lines.append(BattleMessages.failed())
		
		return lines
	
	async def _execute_turn_action(
		self,
		is_player_turn: bool,
		move_id: str,
		move_data: MoveData
	) -> List[str]:
		user = self.player_active if is_player_turn else self.wild
		target = self.wild if is_player_turn else self.player_active
		
		action_blocked, pre_messages = StatusHandler.check_pre_action(user)
		if action_blocked:
			return pre_messages
		
		confusion_blocked, confusion_messages = StatusHandler.check_confusion(user)
		if confusion_blocked:
			return pre_messages + confusion_messages
		
		return pre_messages + confusion_messages + await self._execute_move(user, target, move_data, move_id)
	
	def _select_enemy_move(self) -> str:
		available_moves = [m for m in self.wild.moves if int(m.get("pp", 0)) > 0]
		return str(random.choice(available_moves)["id"]) if available_moves else "__struggle__"
	
	def _determine_turn_order(
		self,
		player_move: MoveData,
		enemy_move: MoveData
	) -> List[str]:
		if player_move.priority != enemy_move.priority:
			return ["player", "enemy"] if player_move.priority > enemy_move.priority else ["enemy", "player"]
		
		player_speed = self.player_active.eff_stat("speed")
		enemy_speed = self.wild.eff_stat("speed")
		
		if player_speed != enemy_speed:
			return ["player", "enemy"] if player_speed > enemy_speed else ["enemy", "player"]
		
		return random.choice([["player", "enemy"], ["enemy", "player"]])
	
	async def handle_player_move(self, move_id: str) -> None:
		async with self.lock:
			if self.ended:
				return
			
			self.lines = []
			
			player_move_data = await self._fetch_move(move_id)
			enemy_move_id = self._select_enemy_move()
			
			if enemy_move_id != "__struggle__":
				enemy_move_data = await self._fetch_move(enemy_move_id)
			else:
				enemy_move_data = MoveData(
					"Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, []
				)
			
			turn_order = self._determine_turn_order(player_move_data, enemy_move_data)
			
			for side in turn_order:
				if self.player_active.fainted or self.wild.fainted:
					break
				
				if side == "player":
					self.lines.extend(
						await self._execute_turn_action(True, move_id, player_move_data)
					)
					if self.wild.fainted:
						await self._handle_victory()
						await self.refresh()
						return
				else:
					if self.lines:
						self.lines.append("")
					self.lines.extend(
						await self._execute_turn_action(False, enemy_move_id, enemy_move_data)
					)
					if self.player_active.fainted:
						await self._handle_player_faint()
						await self.refresh()
						return
			
			end_turn_effects = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
			if end_turn_effects:
				self.lines.append("")
				self.lines.extend(end_turn_effects)
			
			await self._process_weather_effects()
			
			if self.wild.fainted:
				await self._handle_victory()
			elif self.player_active.fainted:
				await self._handle_player_faint()
			
			if not self.ended:
				self.turn += 1
			
			await self.refresh()
	
	async def _process_weather_effects(self) -> None:
		if not self.weather["type"] or self.weather["turns"] <= 0:
			return
		
		self.weather["turns"] -= 1
		
		if self.weather["turns"] == 0:
			self.lines.append("🌤️ O clima voltou ao normal!")
			self.weather["type"] = None
		elif self.weather["type"] == "hail":
			for pokemon, prefix in [(self.player_active, "🔵"), (self.wild, "🔴")]:
				if not pokemon.fainted and "ice" not in pokemon.types:
					damage = max(1, int(pokemon.stats["hp"] * BattleConstants.HAIL_DAMAGE_RATIO))
					actual = pokemon.take_damage(damage, ignore_substitute=True)
					self.lines.append(
						f"❄️ {prefix} {pokemon.display_name} sofreu {actual} de dano da granizo!"
					)
	
	async def switch_active(self, new_index: int, consume_turn: bool = True) -> None:
		async with self.lock:
			if self.ended or new_index == self.active_player_idx:
				return
			if not (0 <= new_index < len(self.player_team)) or self.player_team[new_index].fainted:
				return
			
			self.lines = []
			old_name = self.player_active.display_name
			self.active_player_idx = new_index
			self.battle_participants.add(new_index)
			self.must_redraw_image = True
			
			self.lines.extend([
				f"🔄 {old_name} voltou!",
				f"Vamos lá, {self.player_active.display_name}!"
			])
			
			if consume_turn:
				self.lines.append("")
				enemy_move_id = self._select_enemy_move()
				
				if enemy_move_id != "__struggle__":
					enemy_move_data = await self._fetch_move(enemy_move_id)
				else:
					enemy_move_data = MoveData(
						"Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, []
					)
				
				self.lines.extend(
					await self._execute_turn_action(False, enemy_move_id, enemy_move_data)
				)
				
				end_turn_effects = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
				if end_turn_effects:
					self.lines.append("")
					self.lines.extend(end_turn_effects)
				
				if self.player_active.fainted:
					await self._handle_player_faint()
				
				if not self.ended:
					self.turn += 1
			
			await self.refresh()
	
	async def _calculate_experience_distribution(self) -> List[Tuple[int, Dict[str, Any], int]]:
		base_experience = pm.repo.tk.calc_battle_exp(
			self.player_active.level,
			self.wild.level
		)
		
		participant_count = len(self.battle_participants)
		if participant_count == 0:
			return []
		
		experience_per_pokemon = max(1, base_experience // participant_count)
		
		distribution = []
		for participant_index in self.battle_participants:
			pokemon_data = self.player_party_raw[participant_index]
			exp_result = pm.repo.tk.add_exp(self.user_id, pokemon_data["id"], experience_per_pokemon)

			if exp_result.get("levels_gained"):
				move_result = await pm.process_level_up(
					self.user_id,
					pokemon_data["id"],
					exp_result["levels_gained"]
				)
				
				if move_result.get("learned_moves"):
					for move_name in move_result["learned_moves"]:
						self.lines.append(f"📚 {self.player_team[participant_index].display_name} aprendeu **{move_name}**!")
				
				if move_result.get("pending_moves"):
					for move_name in move_result["pending_moves"]:
						self.lines.append(f"⚠️ {self.player_team[participant_index].display_name} quer aprender **{move_name}**, mas está sem espaço!")
			distribution.append((participant_index, pokemon_data, experience_per_pokemon))
		
		return distribution
	
	def _format_experience_gains(self, distribution: List[Tuple[int, Dict[str, Any], int]]) -> List[str]:
		lines = []
		
		if len(distribution) > 1:
			lines.append(f"⭐ **XP Distribuído** ({len(distribution)} participantes):")
		else:
			lines.append("⭐ **XP Ganho:**")
		
		for index, _, experience in distribution:
			pokemon_name = self.player_team[index].display_name
			lines.append(f"  • {pokemon_name} +{experience} XP")
		
		return lines
	
	async def attempt_capture(self, ball_type: str = BallType.POKE_BALL) -> bool:
		if self.player_active.fainted:
			self.lines = ["Seu Pokémon está desmaiado!"]
			if self.actions_view:
				self.actions_view.force_switch_mode = True
			await self.refresh()
			return False

		already_caught = pm.repo.tk.has_caught_species(self.user_id, self.wild.species_id)
		success, shake_count, modifier = CaptureSystem.attempt_capture_gen3(
			wild=self.wild,
			ball_type=self.ball_type,
			turn=self.turn,
			time_of_day=self.time_of_day,
			location_type=self.location_type,
			already_caught=already_caught
		)
		
		ball_emoji = PokeBallSystem.get_ball_emoji(ball_type)
		ball_name = PokeBallSystem.get_ball_name(ball_type)
		
		if success:
			experience_distribution = await self._calculate_experience_distribution()
			
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
				base_stats=self.wild_raw["base_stats"],
				exp=self.wild_raw.get("exp", 0),
				moves=self.wild_raw.get("moves", []),
				nickname=self.wild_raw.get("nickname"),
				name=self.wild_raw.get("name"),
				current_hp=self.wild_raw.get("current_hp"),
				on_party=pm.repo.tk.can_add_to_party(self.user_id)
			)
			
			self.ended = True
			
			bonus_text = f" (Bônus {modifier:.1f}x)" if modifier > 1.0 else ""
			
			self.lines = [
				"🎉 **CAPTURA!**",
				f"{ball_emoji} Capturado com {ball_name}!{bonus_text}",
				f"✨ {self.wild.display_name} foi adicionado à sua Pokédex!",
				""
			]
			
			self.lines.extend(self._format_experience_gains(experience_distribution))
			
			if self.actions_view:
				self.actions_view.disable_all()
			
			await self.refresh()
			
			total_experience = sum(xp for _, _, xp in experience_distribution)
			await self.interaction.channel.send(
				f"🎉 **Capturou {self.wild.display_name}!** ⭐ +{total_experience} XP distribuído!"
			)
			
			await self.cleanup()
			return True
		else:
			self.lines = []
			shake_display = f"{ball_emoji} " * shake_count if shake_count > 0 else ""
			self.lines.append(f"💢 {shake_display}Escapou! ({shake_count}x)")
			self.lines.append("")
			
			enemy_move_id = self._select_enemy_move()
			
			if enemy_move_id != "__struggle__":
				enemy_move_data = await self._fetch_move(enemy_move_id)
			else:
				enemy_move_data = MoveData(
					"Struggle", None, 50, 0, "physical", "normal", 1, 1, 0, 0, 0, 0, None, 0, []
				)
			
			self.lines.extend(
				await self._execute_turn_action(False, enemy_move_id, enemy_move_data)
			)
			
			end_turn_effects = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
			if end_turn_effects:
				self.lines.append("")
				self.lines.extend(end_turn_effects)
			
			if self.player_active.fainted:
				await self._handle_player_faint()
			
			if not self.ended:
				self.turn += 1
			
			await self.refresh()
			return False
	
	async def _handle_victory(self) -> None:
		experience_distribution = await self._calculate_experience_distribution()
		
		self.ended = True
		self.lines.extend(["", "🏆 **VITÓRIA!**", ""])
		self.lines.extend(self._format_experience_gains(experience_distribution))
		
		if self.actions_view:
			self.actions_view.disable_all()
		
		await self.refresh()
		
		total_experience = sum(xp for _, _, xp in experience_distribution)
		await self.interaction.channel.send(
			f"🏆 **Vitória!** ⭐ +{total_experience} XP distribuído!"
		)
		await self.cleanup()
	
	async def _handle_player_faint(self) -> None:
		remaining_pokemon = [p for p in self.player_team if not p.fainted]
		
		if not remaining_pokemon:
			self.ended = True
			self.lines.extend([
				"",
				"😔 **DERROTA**",
				"Todos os seus pokémon desmaiaram!"
			])
			if self.actions_view:
				self.actions_view.disable_all()
			await self.refresh()
			await self.interaction.channel.send("💀 **Derrota!**")
			await self.cleanup()
			return
		
		self.lines.extend(["", "Escolha outro Pokémon!"])
		if self.actions_view:
			self.actions_view.force_switch_mode = True
	
	async def cleanup(self) -> None:
		battle_tracker.remove(self.user_id)
		self.move_cache.clear()
		self.effect_cache.clear()
		self.battle_participants.clear()
		if self.actions_view:
			self.actions_view.stop()

class WildBattleView(discord.ui.View):
	__slots__ = ('battle', 'user_id', 'force_switch_mode')
	
	def __init__(self, battle: WildBattle, timeout: float = 180.0) -> None:
		super().__init__(timeout=timeout)
		self.battle = battle
		self.user_id = battle.user_id
		self.force_switch_mode = False
		
	async def on_timeout(self) -> None:
		if not self.battle.ended:
			self.battle.ended = True
			self.disable_all()
			
			await self.battle.cleanup()
			
			if self.battle.message:
				await self.battle.message.edit(
					content="Batalha Expirada!\nA batalha foi encerrada por inatividade.", 
					view=self
				)
	
	def disable_all(self) -> None:
		for item in self.children:
			item.disabled = True
	
	@discord.ui.button(style=discord.ButtonStyle.primary, label="Lutar", emoji="⚔️")
	async def fight(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("Batalha encerrada.", ephemeral=True)
		if self.force_switch_mode:
			return await interaction.response.edit_message(view=SwitchView(self.battle, force_only=True))
		await interaction.response.edit_message(view=MovesView(self.battle))
	
	@discord.ui.button(style=discord.ButtonStyle.primary, label="Trocar", emoji="🔄")
	async def switch(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("Batalha encerrada.", ephemeral=True)
		await interaction.response.edit_message(view=SwitchView(self.battle))
	
	@discord.ui.button(style=discord.ButtonStyle.secondary, emoji="<:PokeBall:1345558169090265151>", label="Capturar")
	async def capture(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("Batalha encerrada.", ephemeral=True)
		if self.force_switch_mode or self.battle.player_active.fainted:
			return await interaction.response.send_message("Troque de Pokémon!", ephemeral=True)
		await interaction.response.defer()

		await self.battle.attempt_capture()

