import discord
import random
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from __main__ import pm, battle_tracker
from utils.canvas import compose_battle_async
from utils.preloaded import preloaded_textures
from utils.formatting import format_pokemon_display
from .pokemon import BattlePokemon
from .messages import BattleMessages
from .status import StatusHandler
from .capture import CaptureSystem
from .helpers import SwitchView, MovesView, MoveData, _hp_bar
from .pokeballs import PokeBallSystem, BallType
from .engine import BattleEngine

class WildBattle(BattleEngine):
	
	def __init__(
		self,
		player_party: List[Dict[str, Any]],
		wild: Dict[str, Any],
		user_id: str,
		interaction: discord.Interaction
	) -> None:
		super().__init__(battle_type="single")
		
		self.user_id = user_id
		self.interaction = interaction
		self.player_party_raw = player_party
		self.active_player_idx = 0
		self.wild_raw = wild
		self.message: Optional[discord.Message] = None
		self.player_team: List[BattlePokemon] = []
		self.wild: Optional[BattlePokemon] = None
		self.actions_view: Optional[WildBattleView] = None
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
	
	def _has_remaining_pokemon(self) -> bool:
		return any(not p.fainted for p in self.player_team)
	
	def _check_battle_state(self) -> Optional[str]:
		wild_alive = not self.wild.fainted
		player_alive = not self.player_active.fainted
		has_backup = any(idx != self.active_player_idx and not p.fainted for idx, p in enumerate(self.player_team))
		
		if not wild_alive and not player_alive:
			if has_backup:
				return "both_fainted_has_backup"
			else:
				return "both_fainted_no_backup"
		
		if not wild_alive:
			return "wild_fainted"
		
		if not player_alive:
			if has_backup:
				return "player_fainted_has_backup"
			else:
				return "player_fainted_no_backup"
		
		return "ongoing"
	
	async def _resolve_battle_state(self, state: str) -> bool:
		if state == "wild_fainted":
			await self._handle_victory()
			return True
		
		elif state == "player_fainted_no_backup" or state == "both_fainted_no_backup":
			await self._handle_defeat()
			return True
		
		elif state == "player_fainted_has_backup" or state == "both_fainted_has_backup":
			if state == "both_fainted_has_backup":
				self.lines.append("")
				self.lines.append("Ambos os Pokémon desmaiaram!")
			await self._handle_forced_switch()
			return True
		
		return False
	
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
		
		self.battle_context.team1 = [self.player_active]
		self.battle_context.team2 = [self.wild]
		
		await self._preload_move_data()
		return True
	
	async def _preload_move_data(self) -> None:
		from .helpers import _slug
		
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
		for stat_key in ["atk", "def", "sp_atk", "sp_def", "speed"]:
			stage_value = pokemon.stages.get(stat_key, 0)
			if stage_value != 0:
				stat_abbrev = stat_key.upper().replace("_", "")
				stage_modifications.append(f"{stat_abbrev}: {stage_value:+d}")
		
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
			field_status.append(f"🔄 Trick Room ({self.field['trick_room']})")
		if self.field.get("gravity", 0) > 0:
			field_status.append(f"⬇️ Gravity ({self.field['gravity']})")
		if self.field.get("mud_sport", 0) > 0:
			field_status.append(f"⚡ Mud Sport ({self.field['mud_sport']})")
		if self.field.get("water_sport", 0) > 0:
			field_status.append(f"🔥 Water Sport ({self.field['water_sport']})")
		if self.field.get("spikes_player", 0) > 0:
			field_status.append(f"⚠️ Spikes (Player: {self.field['spikes_player']})")
		if self.field.get("spikes_wild", 0) > 0:
			field_status.append(f"⚠️ Spikes (Wild: {self.field['spikes_wild']})")
		
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
		
		embed.set_footer(text="Effex Engine v1.6 — alpha")
		embed.set_image(url="attachment://battle.png")
		return embed
	
	async def start(self) -> None:
		self.battle_participants.add(self.active_player_idx)
		self.actions_view = WildBattleView(self)
		self.lines = [f"A batalha começou! Vamos lá, {self.player_active.display_name}!"]
		
		entry_damage = self._process_entry_hazards(self.player_active, is_player=True)
		if entry_damage:
			self.lines.extend(entry_damage)

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
			
			pm.tk.set_current_hp(
				self.user_id,
				pokemon_id,
				pokemon.current_hp
			)
			
			pm.tk.set_moves(
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
	
	def _select_enemy_move(self) -> str:
		from .helpers import _slug
		
		available_moves = []
		
		for m in self.wild.moves:
			move_id = str(m["id"])
			pp = int(m.get("pp", 0))
			
			if pp <= 0:
				continue
			
			if self.wild.is_move_disabled(move_id):
				continue
			
			available_moves.append(m)
		
		if not available_moves:
			return "__struggle__"
		
		return str(random.choice(available_moves)["id"])
	
	def _determine_turn_order(
		self,
		player_move: MoveData,
		enemy_move: MoveData
	) -> List[str]:
		player_priority = self._get_move_priority(player_move, self.player_active)
		enemy_priority = self._get_move_priority(enemy_move, self.wild)
		
		if player_priority != enemy_priority:
			return ["player", "enemy"] if player_priority > enemy_priority else ["enemy", "player"]
		
		player_speed = self.player_active.eff_stat("speed")
		enemy_speed = self.wild.eff_stat("speed")
		
		player_item = self.player_active.volatile.get("held_item", "")
		enemy_item = self.wild.volatile.get("held_item", "")
		
		if player_item == "quick_claw" and random.random() < 0.2:
			return ["player", "enemy"]
		if enemy_item == "quick_claw" and random.random() < 0.2:
			return ["enemy", "player"]
		
		if self.field.get("trick_room", 0) > 0:
			if player_speed != enemy_speed:
				return ["player", "enemy"] if player_speed < enemy_speed else ["enemy", "player"]
		else:
			if player_speed != enemy_speed:
				return ["player", "enemy"] if player_speed > enemy_speed else ["enemy", "player"]
		
		return random.choice([["player", "enemy"], ["enemy", "player"]])
	
	async def handle_player_move(self, move_id: str) -> None:
		async with self.lock:
			if self.ended:
				return
			
			self.lines = []
			
			self.player_active.clear_turn_volatiles()
			self.wild.clear_turn_volatiles()
			
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
				if side == "player":
					if self.player_active.fainted:
						continue
					
					self.lines.extend(
						await self._execute_turn_action(True, move_id, player_move_data, self.player_active, self.wild)
					)
					
					state = self._check_battle_state()
					if state != "ongoing":
						resolved = await self._resolve_battle_state(state)
						if resolved:
							await self.refresh()
							return
				
				else:
					if self.wild.fainted:
						continue
					
					if self.lines:
						self.lines.append("")
					
					self.lines.extend(
						await self._execute_turn_action(False, enemy_move_id, enemy_move_data, self.wild, self.player_active)
					)
					
					state = self._check_battle_state()
					if state != "ongoing":
						resolved = await self._resolve_battle_state(state)
						if resolved:
							await self.refresh()
							return
			
			end_turn_effects = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
			if end_turn_effects:
				self.lines.append("")
				self.lines.extend(end_turn_effects)
			
			state = self._check_battle_state()
			if state != "ongoing":
				resolved = await self._resolve_battle_state(state)
				if resolved:
					await self.refresh()
					return
			
			self.lines.append("")
			await self._process_end_of_turn([self.player_active, self.wild])
			await self._process_weather_effects([self.player_active, self.wild])
			await self._process_field_effects()
			
			state = self._check_battle_state()
			if state != "ongoing":
				resolved = await self._resolve_battle_state(state)
				if resolved:
					await self.refresh()
					return
			
			self.turn += 1
			await self.refresh()
	
	async def switch_active(self, new_index: int, consume_turn: bool = True) -> None:
		async with self.lock:
			if self.ended or new_index == self.active_player_idx:
				return
			if not (0 <= new_index < len(self.player_team)) or self.player_team[new_index].fainted:
				return
			
			self.lines = []
			old_name = self.player_active.display_name
			
			if self.player_active.volatile.get("baton_pass_active"):
				effects_to_pass = self.player_active.volatile.get("baton_pass_effects", {})
				self.player_active.volatile["baton_pass_active"] = False
			else:
				effects_to_pass = None
			
			self.active_player_idx = new_index
			self.battle_participants.add(new_index)
			self.must_redraw_image = True
			
			if effects_to_pass:
				self.player_active._apply_baton_pass_effects(effects_to_pass)
				self.lines.append(f"🎯 {old_name} passou seus efeitos!")
			
			self.lines.extend([
				f"🔄 {old_name} voltou!" if not effects_to_pass else "",
				f"Vamos lá, {self.player_active.display_name}!"
			])
			
			self.battle_context.team1 = [self.player_active]
			
			entry_damage = self._process_entry_hazards(self.player_active, is_player=True)
			if entry_damage:
				self.lines.extend(entry_damage)
			
			ability = self.player_active.get_effective_ability()
			if ability == "intimidate":
				self.wild.modify_stat_stage("atk", -1)
				self.lines.append(f"😤 Intimidate baixou o ataque de {self.wild.display_name}!")
			
			if self.actions_view:
				self.actions_view.force_switch_mode = False
			
			state = self._check_battle_state()
			if state != "ongoing":
				resolved = await self._resolve_battle_state(state)
				if resolved:
					await self.refresh()
					return
			
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
					await self._execute_turn_action(False, enemy_move_id, enemy_move_data, self.wild, self.player_active)
				)
				
				state = self._check_battle_state()
				if state != "ongoing":
					resolved = await self._resolve_battle_state(state)
					if resolved:
						await self.refresh()
						return
				
				end_turn_effects = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
				if end_turn_effects:
					self.lines.append("")
					self.lines.extend(end_turn_effects)
				
				state = self._check_battle_state()
				if state != "ongoing":
					resolved = await self._resolve_battle_state(state)
					if resolved:
						await self.refresh()
						return
				
				self.lines.append("")
				await self._process_end_of_turn([self.player_active, self.wild])
				await self._process_weather_effects([self.player_active, self.wild])
				await self._process_field_effects()
				
				state = self._check_battle_state()
				if state != "ongoing":
					resolved = await self._resolve_battle_state(state)
					if resolved:
						await self.refresh()
						return
				
				self.turn += 1
			
			await self.refresh()
	
	def _calculate_ev_yield(self) -> Dict[str, int]:
		base_stats = self.wild.raw.get("base_stats", {})
		ev_yield = {}
		
		stats_map = {
			"hp": "hp",
			"attack": "attack",
			"defense": "defense",
			"special-attack": "special-attack",
			"special-defense": "special-defense",
			"speed": "speed"
		}
		
		for stat_key, stat_name in stats_map.items():
			base_value = base_stats.get(stat_key, 0)
			
			if base_value >= 120:
				ev_yield[stat_name] = 3
			elif base_value >= 100:
				ev_yield[stat_name] = 2
			elif base_value >= 70:
				ev_yield[stat_name] = 1
			else:
				ev_yield[stat_name] = 0
		
		total_evs = sum(ev_yield.values())
		if total_evs == 0:
			highest_stat = max(stats_map.keys(), key=lambda k: base_stats.get(k, 0))
			ev_yield[stats_map[highest_stat]] = 1
		
		return ev_yield
	
	async def _distribute_evs(self) -> List[Tuple[int, Dict[str, Any], Dict[str, int]]]:
		ev_yield = self._calculate_ev_yield()
		
		distribution = []
		for participant_index in self.battle_participants:
			pokemon_data = self.player_party_raw[participant_index]
			
			evs_to_give = ev_yield.copy()
			
			if self.player_team[participant_index].volatile.get("held_item") == "macho_brace":
				evs_to_give = {k: v * 2 for k, v in evs_to_give.items()}
			
			try:
				pm.tk.add_evs(self.user_id, pokemon_data["id"], evs_to_give)
				distribution.append((participant_index, pokemon_data, evs_to_give))
			except ValueError:
				pass
		
		return distribution
	
	async def _calculate_experience_distribution(self) -> List[Tuple[int, Dict[str, Any], int]]:
		base_experience = self.wild.pokeapi_data.base_experience if self.wild.pokeapi_data.base_experience else 50
		
		enemy_level = self.wild.level
		is_trainer_battle = False
		
		base_exp_gain = int((base_experience * enemy_level) / 7)
		
		if is_trainer_battle:
			base_exp_gain = int(base_exp_gain * 1.5)
		
		participant_count = len(self.battle_participants)
		if participant_count == 0:
			return []
		
		distribution = []
		for participant_index in self.battle_participants:
			pokemon_data = self.player_party_raw[participant_index]
			exp_to_give = base_exp_gain // participant_count
			
			if self.player_team[participant_index].volatile.get("held_item") == "lucky_egg":
				exp_to_give = int(exp_to_give * 1.5)
			
			exp_to_give = max(1, exp_to_give)
			
			exp_result = await pm.add_experience(
				self.user_id,
				pokemon_data["id"],
				exp_to_give,
				notify_message=self.message
			)
			
			distribution.append((participant_index, pokemon_data, exp_to_give))
		
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
	
	def _format_ev_gains(self, distribution: List[Tuple[int, Dict[str, Any], Dict[str, int]]]) -> List[str]:
		lines = []
		
		if not distribution:
			return lines
		
		lines.append("💪 **EVs Ganhos:**")
		
		for index, _, evs in distribution:
			pokemon_name = self.player_team[index].display_name
			ev_parts = [f"{stat.upper()}: +{value}" for stat, value in evs.items() if value > 0]
			if ev_parts:
				lines.append(f"  • {pokemon_name} [{', '.join(ev_parts)}]")
		
		return lines
	
	async def attempt_capture(self, ball_type: str = BallType.POKE_BALL) -> bool:
		async with self.lock:
			if self.ended:
				return False
			
			if self.player_active.fainted:
				self.lines = ["Seu Pokémon está desmaiado!"]
				if self.actions_view:
					self.actions_view.force_switch_mode = True
				await self.refresh()
				return False

			already_caught = pm.tk.has_caught_species(self.user_id, self.wild.species_id)
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
				ev_distribution = await self._distribute_evs()
				
				pm.tk.add_pokemon(
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
					growth_type=self.wild_raw.get("growth_type", "medium"),
					moves=self.wild_raw.get("moves", []),
					nickname=self.wild_raw.get("nickname"),
					name=self.wild_raw.get("name"),
					current_hp=self.wild_raw.get("current_hp"),
					on_party=pm.tk.can_add_to_party(self.user_id)
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
				
				ev_lines = self._format_ev_gains(ev_distribution)
				if ev_lines:
					self.lines.append("")
					self.lines.extend(ev_lines)
				
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
					await self._execute_turn_action(False, enemy_move_id, enemy_move_data, self.wild, self.player_active)
				)
				
				state = self._check_battle_state()
				if state != "ongoing":
					resolved = await self._resolve_battle_state(state)
					if resolved:
						await self.refresh()
						return False
				
				end_turn_effects = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
				if end_turn_effects:
					self.lines.append("")
					self.lines.extend(end_turn_effects)
				
				state = self._check_battle_state()
				if state != "ongoing":
					resolved = await self._resolve_battle_state(state)
					if resolved:
						await self.refresh()
						return False
				
				self.lines.append("")
				await self._process_end_of_turn([self.player_active, self.wild])
				await self._process_weather_effects([self.player_active, self.wild])
				await self._process_field_effects()
				
				state = self._check_battle_state()
				if state != "ongoing":
					resolved = await self._resolve_battle_state(state)
					if resolved:
						await self.refresh()
						return False
				
				self.turn += 1
				
				await self.refresh()
				return False
	
	async def _handle_victory(self) -> None:
		experience_distribution = await self._calculate_experience_distribution()
		ev_distribution = await self._distribute_evs()
		
		self.ended = True
		self.lines.extend(["", "🏆 **VITÓRIA!**", ""])
		self.lines.extend(self._format_experience_gains(experience_distribution))
		
		ev_lines = self._format_ev_gains(ev_distribution)
		if ev_lines:
			self.lines.append("")
			self.lines.extend(ev_lines)
		
		if self.actions_view:
			self.actions_view.disable_all()
		
		await self.refresh()
		
		total_experience = sum(xp for _, _, xp in experience_distribution)
		await self.interaction.channel.send(
			f"🏆 **Vitória!** ⭐ +{total_experience} XP distribuído!"
		)
		await self.cleanup()
	
	async def _handle_defeat(self) -> None:
		self.ended = True
		self.lines.extend([
			"",
			"😔 **DERROTA**",
			"Todos os seus Pokémon desmaiaram!"
		])
		if self.actions_view:
			self.actions_view.disable_all()
		await self.refresh()
		await self.interaction.channel.send("💀 **Derrota!**")
		await self.cleanup()
	
	async def _handle_forced_switch(self) -> None:
		self.lines.extend(["", "⚠️ Escolha outro Pokémon!"])
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
				await self.battle.message.reply(
					content="Batalha Expirada!\nA batalha foi encerrada por inatividade.", 
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
	    
	    from .helpers import PokeballsView
	    await interaction.response.edit_message(view=PokeballsView(self.battle))

