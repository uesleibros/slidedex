import asyncio
import discord
from discord.ext import commands
from __main__ import pm, battle_tracker
from utils.canvas import compose_battle_async
from utils.preloaded import preloaded_textures
from utils.formatting import format_pokemon_display, format_item_display
from ..pokemon import BattlePokemon
from ..capture import CaptureSystem
from ..helpers import SwitchView, MovesView, _slug
from ..pokeballs import PokeBallSystem, BallType
from ..rewards import BattleRewards
from ...constants import VERSION_GROUPS
from .engine import BattleEngine, BattleState

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
		self.wild_api = None
		self.actions_view: Optional[WildBattleView] = None
		self.ball_type = BallType.POKE_BALL
		self.location_type = "normal"
		self.time_of_day = "day"
		self.battle_participants: Set[int] = set()
		self.run_attempts: int = 0
	
	def _generate_wild_held_item(self) -> None:
		if not self.wild_api or not hasattr(self.wild_api, 'held_items'):
			return
		
		held_items = self.wild_api.held_items
		if not held_items:
			return
		
		possible_items = []
		
		for held_item_data in held_items:
			item_name = held_item_data.item.name
			
			for version_detail in held_item_data.version_details:
				version_name = version_detail.version.name
				
				if version_name in VERSION_GROUPS:
					rarity = version_detail.rarity
					possible_items.append((item_name, rarity))
					break
		
		if not possible_items:
			return
		
		for item_id, rarity in possible_items:
			chance = rarity / 100.0
			
			if pm.tk.roll_chance(self.user_id, chance):
				self.wild_raw["held_item"] = item_id
				return
		
		self.wild_raw["held_item"] = None
	
	@property
	def player_active(self) -> BattlePokemon:
		return self.player_team[self.active_player_idx]
	
	def get_battle_state(self) -> BattleState:
		wild_alive = not self.wild.fainted
		player_alive = not self.player_active.fainted
		has_backup = any(idx != self.active_player_idx and not p.fainted for idx, p in enumerate(self.player_team))
		
		if not wild_alive and not player_alive:
			return BattleState.BOTH_FAINTED_BACKUP if has_backup else BattleState.BOTH_FAINTED_NO_BACKUP
		if not wild_alive:
			return BattleState.PLAYER_WIN
		if not player_alive:
			return BattleState.PLAYER_FAINTED_BACKUP if has_backup else BattleState.PLAYER_LOSS
		
		return BattleState.ONGOING
	
	async def handle_battle_end(self, state: BattleState) -> None:
		if state == BattleState.PLAYER_WIN:
			await self._handle_victory()
		elif state in (BattleState.PLAYER_LOSS, BattleState.BOTH_FAINTED_NO_BACKUP):
			await self._handle_defeat()
		elif state in (BattleState.PLAYER_FAINTED_BACKUP, BattleState.BOTH_FAINTED_BACKUP):
			if state == BattleState.BOTH_FAINTED_BACKUP:
				self.lines.append("")
				self.lines.append("Ambos os Pokémon desmaiaram!")
			
			if self.player_active.fainted:
				pokemon_id = self.player_party_raw[self.active_player_idx]["id"]
				pm.tk.decrease_happiness_faint(self.user_id, pokemon_id)
			
			await self._handle_forced_switch()
	
	async def setup(self) -> bool:
		w_api = pm.service.get_pokemon(self.wild_raw["species_id"])
		w_spec = pm.service.get_species(self.wild_raw["species_id"])
		
		self.wild_api = w_api
		
		self._generate_wild_held_item()
		self.wild = BattlePokemon(self.wild_raw, w_api, w_spec)
		
		for p in self.player_party_raw:
			pokemon = pm.service.get_pokemon(p["species_id"])
			species = pm.service.get_species(p["species_id"])
			self.player_team.append(BattlePokemon(p, pokemon, species))
		
		if not self._validate_party(self.player_team):
			await self.interaction.followup.send(
				"Todos os seus Pokémon estão desmaiados!\n"
				"Cure-os em um Centro Pokémon antes de batalhar.",
				ephemeral=True
			)
			return False
		
		first_available = self._find_first_available_pokemon(self.player_team)
		if first_available is None:
			await self.interaction.followup.send(
				"Nenhum Pokémon disponível para batalha!",
				ephemeral=True
			)
			return False
		
		self.active_player_idx = first_available
		self.battle_context.team1 = [self.player_active]
		self.battle_context.team2 = [self.wild]
		
		await self._preload_all_moves()
		return True
	
	async def _preload_all_moves(self) -> None:
		move_ids: Set[str] = set()
		for mv in self.wild.moves:
			move_ids.add(_slug(mv["id"]))
		for p in self.player_team:
			for mv in p.moves:
				move_ids.add(_slug(mv["id"]))

		if move_ids:
			for mid in move_ids:
				if mid:
					self._fetch_move(mid)
	
	async def _compose_image(self) -> discord.File:
		pb = None
		ef = None

		pb = pm.service.get_pokemon_sprite(self.player_active.raw)[1]
		ef = pm.service.get_pokemon_sprite(self.wild.raw)[0]

		if self.player_active.volatile.get("transformed"):
			pb = pm.service.get_pokemon_sprite(self.wild.raw)[1]
		
		if self.wild.volatile.get("transformed"):
			ef = pm.service.get_pokemon_sprite(self.player_active.raw)[0]
		
		buf = await compose_battle_async(pb, ef, preloaded_textures["battle"])
		return discord.File(buf, filename="battle.png")
	
	def _build_embed(self) -> discord.Embed:
		description_components = [
			self._generate_hp_display(self.player_active),
			"**VS**",
			self._generate_hp_display(self.wild),
			""
		]
		
		description_components.extend(self._format_weather_display())
		description_components.extend(self._format_field_display())
		
		if self.lines:
			description_components.extend(self.lines[-15:])
		
		embed = discord.Embed(
			title=f"Batalha Selvagem - Turno {self.turn}",
			description="\n".join(description_components),
			color=discord.Color.green()
		)
		
		embed.set_footer(text="Effex Engine v1.71 — alpha")
		embed.set_image(url="attachment://battle.png")
		return embed
	
	def _format_weather_display(self) -> List[str]:
		weather_icons = {"sun": "☀️", "rain": "🌧️", "hail": "❄️", "sandstorm": "🌪️"}
		lines = []
		
		if self.weather["type"] and self.weather["turns"] > 0:
			icon = weather_icons.get(self.weather["type"], "🌤️")
			lines.append(f"{icon} {self.weather['type'].title()} ({self.weather['turns']} turnos)")
		
		return lines
	
	def _format_field_display(self) -> List[str]:
		field_status = []
		field_map = {
			"trick_room": ("🔄", "Trick Room"),
			"gravity": ("⬇️", "Gravity"),
			"mud_sport": ("⚡", "Mud Sport"),
			"water_sport": ("🔥", "Water Sport")
		}
		
		for key, (emoji, name) in field_map.items():
			if self.field.get(key, 0) > 0:
				field_status.append(f"{emoji} {name} ({self.field[key]})")
		
		if self.field.get("spikes_player", 0) > 0:
			field_status.append(f"⚠️ Spikes (Player: {self.field['spikes_player']})")
		if self.field.get("spikes_wild", 0) > 0:
			field_status.append(f"⚠️ Spikes (Wild: {self.field['spikes_wild']})")
		
		if field_status:
			field_status.append("")
		
		return field_status
	
	def _process_entry_abilities(self, pokemon: BattlePokemon, is_player: bool) -> List[str]:
		lines = []
		ability = pokemon.get_effective_ability()
		
		if ability == "intimidate":
			opponent = self.wild if is_player else self.player_active
			opponent.modify_stat_stage("atk", -1)
			lines.append(f"😤 Intimidate de {pokemon.display_name} baixou o ataque de {opponent.display_name}!")
		
		elif ability == "drought":
			self.weather["type"] = "sun"
			self.weather["turns"] = 5
			lines.append(f"☀️ Drought de {pokemon.display_name} intensificou o sol!")
		
		elif ability == "drizzle":
			self.weather["type"] = "rain"
			self.weather["turns"] = 5
			lines.append(f"🌧️ Drizzle de {pokemon.display_name} começou a chover!")
		
		elif ability == "sand_stream":
			self.weather["type"] = "sandstorm"
			self.weather["turns"] = 5
			lines.append(f"🌪️ Sand Stream de {pokemon.display_name} criou uma tempestade de areia!")
		
		elif ability == "snow_warning":
			self.weather["type"] = "hail"
			self.weather["turns"] = 5
			lines.append(f"❄️ Snow Warning de {pokemon.display_name} começou a granizar!")
		
		elif ability == "download":
			opponent = self.wild if is_player else self.player_active
			phys_def = opponent.eff_stat("def")
			spec_def = opponent.eff_stat("sp_def")
			
			if phys_def < spec_def:
				pokemon.modify_stat_stage("atk", 1)
				lines.append(f"⬇️ Download de {pokemon.display_name} aumentou Attack!")
			else:
				pokemon.modify_stat_stage("sp_atk", 1)
				lines.append(f"⬇️ Download de {pokemon.display_name} aumentou Sp. Attack!")
		
		elif ability == "trace":
			opponent = self.wild if is_player else self.player_active
			opponent_ability = opponent.get_effective_ability()
			
			untraceable = ["trace", "multitype", "stance_change", "power_construct", "battle_bond", "schooling", "comatose", "shields_down", "disguise", "zen_mode", "flower_gift"]
			
			if opponent_ability and opponent_ability not in untraceable:
				pokemon.volatile["original_ability"] = ability
				pokemon.ability = opponent_ability
				pokemon.volatile["traced_ability"] = opponent_ability
				lines.append(f"✨ Trace de {pokemon.display_name} copiou {opponent_ability} de {opponent.display_name}!")
		
		elif ability == "pressure":
			lines.append(f"💪 {pokemon.display_name} está exercendo Pressure!")
		
		elif ability == "mold_breaker":
			lines.append(f"🔨 {pokemon.display_name} quebra moldes!")
		
		elif ability == "teravolt":
			lines.append(f"⚡ {pokemon.display_name} está irradiando uma aura turbulenta!")
		
		elif ability == "turboblaze":
			lines.append(f"🔥 {pokemon.display_name} está irradiando uma aura ardente!")
		
		elif ability == "slow_start":
			pokemon.volatile["slow_start_turns"] = 5
			lines.append(f"🐢 {pokemon.display_name} não pode dar tudo de si!")
		
		elif ability == "unnerve":
			opponent = self.wild if is_player else self.player_active
			opponent.volatile["unnerved"] = True
			lines.append(f"😰 {opponent.display_name} está nervoso demais para comer Berries!")
		
		return lines
	
	async def start(self) -> None:
		self.battle_participants.add(self.active_player_idx)
		self.actions_view = WildBattleView(self)
		
		start_messages = [f"A batalha começou! Vamos lá, {self.player_active.display_name}!"]
		
		if self.wild_raw.get("held_item"):
			item_display = format_item_display(self.wild_raw["held_item"])
			start_messages.append(f"{self.wild.display_name} está segurando {item_display}!")
		
		self.lines = start_messages
		
		entry_ability_messages = self._process_entry_abilities(self.player_active, is_player=True)
		if entry_ability_messages:
			self.lines.extend(entry_ability_messages)
		
		entry_ability_messages_wild = self._process_entry_abilities(self.wild, is_player=False)
		if entry_ability_messages_wild:
			self.lines.extend(entry_ability_messages_wild)
		
		entry_damage = self._process_entry_hazards(self.player_active, is_player=True)
		if entry_damage:
			self.lines.extend(entry_damage)

		battle_tracker.add(self.user_id, self)
		self.message = await self.interaction.channel.send(
			embed=self._build_embed(),
			file=await self._compose_image(),
			view=self.actions_view
		)
		self.must_redraw_image = False

	async def _save_battle_state(self) -> None:
		for idx, pokemon in enumerate(self.player_team):
			pokemon_id = self.player_party_raw[idx]["id"]
			pm.tk.set_current_hp(self.user_id, pokemon_id, pokemon.current_hp)
			pm.tk.set_status(
				self.user_id, 
				pokemon_id, 
				pokemon.status.get("name"), 
				pokemon.status.get("counter", 0)
			)

			self.player_party_raw[idx]["status"] = pokemon.status
			
			current_pokemon = pm.tk.get_pokemon(self.user_id, pokemon_id)
			for battle_move in pokemon.moves:
				for db_move in current_pokemon["moves"]:
					if db_move["id"] == battle_move["id"]:
						db_move["pp"] = battle_move["pp"]
			
			pm.tk.set_moves(self.user_id, pokemon_id, current_pokemon["moves"])
		
		if self.wild:
			self.wild_raw["current_hp"] = self.wild.current_hp
			self.wild_raw["status"] = self.wild.status
			self.wild_raw["moves"] = [dict(m) for m in self.wild.moves]
	
	async def refresh(self) -> None:
		if not self.message:
			return

		await self._save_battle_state()
		embed = self._build_embed()
		
		if self.must_redraw_image:
			file = await self._compose_image()
			await self.message.edit(attachments=[file], embed=embed, view=self.actions_view)
			self.must_redraw_image = False
		else:
			await self.message.edit(embed=embed, view=self.actions_view)
	
	async def handle_player_move(self, move_id: str) -> None:
		async with self.lock:
			if self.ended:
				return
			
			self.lines = []
			self.player_active.clear_turn_volatiles()
			self.wild.clear_turn_volatiles()
			
			enemy_move_id = self._select_ai_move(self.wild)
			
			await self.execute_battle_turn(
				player_move_id=move_id,
				enemy_move_id=enemy_move_id,
				player=self.player_active,
				enemy=self.wild
			)
			
			state = self.get_battle_state()
			if state != BattleState.ONGOING:
				await self.handle_battle_end(state)
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
			
			effects_to_pass = None
			if self.player_active.volatile.get("baton_pass_active"):
				effects_to_pass = self.player_active.volatile.get("baton_pass_effects", {})
				self.player_active.volatile["baton_pass_active"] = False
			
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
			
			entry_ability_messages = self._process_entry_abilities(self.player_active, is_player=True)
			if entry_ability_messages:
				self.lines.extend(entry_ability_messages)
			
			entry_damage = self._process_entry_hazards(self.player_active, is_player=True)
			if entry_damage:
				self.lines.extend(entry_damage)
			
			if self.actions_view:
				self.actions_view.force_switch_mode = False
			
			state = self.get_battle_state()
			if state != BattleState.ONGOING:
				await self.handle_battle_end(state)
				await self.refresh()
				return
			
			if consume_turn:
				self.lines.append("")
				enemy_move_id = self._select_ai_move(self.wild)
				
				await self.execute_enemy_turn(enemy_move_id, self.wild, self.player_active)
				
				state = self.get_battle_state()
				if state != BattleState.ONGOING:
					await self.handle_battle_end(state)
					await self.refresh()
					return
				
				self.turn += 1
			
			await self.refresh()
	
	async def attempt_run(self) -> bool:
		async with self.lock:
			if self.ended:
				return False
			
			if self.player_active.fainted:
				self.lines = ["Seu Pokémon está desmaiado!"]
				if self.actions_view:
					self.actions_view.force_switch_mode = True
				await self.refresh()
				return False
			
			if self.player_active.volatile.get("trapped"):
				trapper = self.player_active.volatile.get("trapped_by")
				if trapper and not trapper.fainted:
					self.lines = [f"❌ Você não pode fugir! {self.wild.display_name} te prendeu!"]
					await self.refresh()
					return False
			
			if self.player_active.volatile.get("ingrain"):
				self.lines = ["❌ Você não pode fugir! Suas raízes te prendem!"]
				await self.refresh()
				return False
			
			wild_held_item = self.wild_raw.get("held_item")
			player_held_item = self.player_party_raw[self.active_player_idx].get("held_item")
			
			if player_held_item == "smoke-ball":
				self.lines = ["💨 Você fugiu com sucesso com Smoke Ball!"]
				self.ended = True
				
				if self.actions_view:
					self.actions_view.disable_all()
				
				await self.refresh()
				await self.interaction.channel.send(
					f"💨 <@{self.user_id}> fugiu da batalha com Smoke Ball!"
				)
				await self.cleanup()
				return True
			
			self.run_attempts += 1
			
			player_speed = self.player_active.eff_stat("speed")
			wild_speed = self.wild.eff_stat("speed")
			
			if wild_speed == 0:
				wild_speed = 1
			
			b_value = (wild_speed // 4) % 256
			if b_value == 0:
				b_value = 1
			
			f_value = ((player_speed * 128) // b_value) + (30 * self.run_attempts)

			rng = pm.tk.get_user_rng(self.user_id)
			roll = rng.randint(0, 256)
			pm.tk.save_user_rng(self.user_id, rng)
			
			if f_value >= 256 or f_value > roll:
				self.lines = ["💨 Você fugiu com sucesso!"]
				self.ended = True
				
				if self.actions_view:
					self.actions_view.disable_all()
				
				await self.refresh()
				await self.interaction.channel.send(f"💨 <@{self.user_id}> fugiu da batalha!")
				await self.cleanup()
				return True
			else:
				self.lines = ["Não conseguiu fugir!", ""]
				
				enemy_move_id = self._select_ai_move(self.wild)
				await self.execute_enemy_turn(enemy_move_id, self.wild, self.player_active)
				
				state = self.get_battle_state()
				if state != BattleState.ONGOING:
					await self.handle_battle_end(state)
					await self.refresh()
					return False
				
				self.turn += 1
				await self.refresh()
				return False
	
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
				toolkit=pm.tk,
				user_id=self.user_id,
				ball_type=self.ball_type,
				turn=self.turn,
				time_of_day=self.time_of_day,
				location_type=self.location_type,
				already_caught=already_caught
			)
			
			ball_emoji = PokeBallSystem.get_ball_emoji(ball_type)
			ball_name = PokeBallSystem.get_ball_name(ball_type)
			
			if success:
				await self._apply_battle_happiness_bonus()
				
				exp_distribution = await self._calculate_experience_distribution()
				await self._distribute_evs()
				
				captured_pokemon = pm.tk.add_pokemon(
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
					happiness=70,
					moves=self.wild_raw.get("moves", []),
					nickname=self.wild_raw.get("nickname"),
					name=self.wild_raw.get("name"),
					current_hp=self.wild_raw.get("current_hp"),
					held_item=self.wild_raw.get("held_item"),
					on_party=pm.tk.can_add_to_party(self.user_id)
				)
				
				self.ended = True
				
				bonus_text = f" (Bônus {modifier:.1f}x)" if modifier > 1.0 else ""
				max_level_skipped = getattr(self, '_max_level_skipped', 0)
				exp_lines = BattleRewards.format_experience_gains(exp_distribution, max_level_skipped)
				
				if self.actions_view:
					self.actions_view.disable_all()
				
				await self.refresh()
				
				total_exp = sum(xp for _, _, xp in exp_distribution)
				capture_message = (
					f"{format_pokemon_display(self.wild_raw, bold_name=True)} foi adicionado à sua Pokédex e recebeu <:CometShard:1424200074463805551> **+{total_exp} de EXP!**\n"
					f"{ball_emoji} Capturado com {ball_name}!{bonus_text}\n"
					f"{'\n'.join(exp_lines)}"
				)
				
				if self.wild_raw.get("held_item"):
					item_display = format_item_display(self.wild_raw["held_item"])
					capture_message += f"\n🎁 Estava segurando {item_display}!"
				
				await self.interaction.channel.send(capture_message)
				
				await self.cleanup()
				return True
			else:
				self.lines = []
				shake_display = f"{ball_emoji} " * shake_count if shake_count > 0 else ""
				self.lines.append(f"💢 {shake_display}Escapou! ({shake_count}x)")
				self.lines.append("")
				
				enemy_move_id = self._select_ai_move(self.wild)
				await self.execute_enemy_turn(enemy_move_id, self.wild, self.player_active)
				
				state = self.get_battle_state()
				if state != BattleState.ONGOING:
					await self.handle_battle_end(state)
					await self.refresh()
					return False
				
				self.turn += 1
				await self.refresh()
				return False
	
	async def _apply_battle_happiness_bonus(self) -> None:
		for participant_index in self.battle_participants:
			pokemon_data = self.player_party_raw[participant_index]
			pokemon_battle = self.player_team[participant_index]
			
			if not pokemon_battle.fainted:
				pm.tk.increase_happiness_battle(self.user_id, pokemon_data["id"])
	
	async def _distribute_evs(self) -> List[Tuple[int, str, Dict[str, int]]]:
		ev_yield = BattleRewards.calculate_ev_yield(self.wild)
		distribution = []
		
		for participant_index in self.battle_participants:
			pokemon_data = self.player_party_raw[participant_index]
			pokemon_battle = self.player_team[participant_index]
			
			held_item = pokemon_data.get("held_item")
			has_macho_brace = held_item == "macho-brace"
			evs_to_give = BattleRewards.apply_ev_modifiers(ev_yield, has_macho_brace=has_macho_brace)
			
			try:
				pm.tk.add_evs(self.user_id, pokemon_data["id"], evs_to_give)
				distribution.append((participant_index, pokemon_battle.display_name, evs_to_give))
			except ValueError:
				pass
		
		return distribution
	
	def _calculate_experience_distribution(self) -> List[Tuple[int, str, int]]:
		base_exp = BattleRewards.calculate_base_experience(self.wild, is_trainer_battle=False)
		participant_count = len(self.battle_participants)
		
		if participant_count == 0:
			return []
		
		distribution = []
		max_level_skipped = 0
		
		for participant_index in self.battle_participants:
			pokemon_data = self.player_party_raw[participant_index]
			pokemon_battle = self.player_team[participant_index]
			
			if pokemon_data["level"] >= 100:
				max_level_skipped += 1
				continue
			
			held_item = pokemon_data.get("held_item")
			has_lucky_egg = held_item == "lucky-egg"
			exp_to_give = BattleRewards.apply_exp_modifiers(
				base_exp,
				participant_count,
				has_lucky_egg=has_lucky_egg
			)
			
			pm.add_experience(
				self.user_id,
				pokemon_data["id"],
				exp_to_give,
				notify_message=self.message
			)
			
			distribution.append((participant_index, pokemon_battle, exp_to_give))
		
		self._max_level_skipped = max_level_skipped
		return distribution
	
	async def _handle_victory(self) -> None:
		await self._apply_battle_happiness_bonus()
		await self._distribute_evs()
		exp_distribution = self._calculate_experience_distribution()
		
		wild_held_item = self.wild_raw.get("held_item")
		
		self.ended = True
		
		max_level_skipped = getattr(self, '_max_level_skipped', 0)
		exp_lines = BattleRewards.format_experience_gains(exp_distribution, max_level_skipped)
		
		if self.actions_view:
			self.actions_view.disable_all()
		
		await self.refresh()
		
		total_exp = sum(xp for _, _, xp in exp_distribution)
		victory_message = f"<:OhBrother:1424196500581257339> **Você venceu!** e recebeu <:CometShard:1424200074463805551> **+{total_exp} de EXP!**\n{'\n'.join(exp_lines)}"
		
		if wild_held_item:
			item_display = format_item_display(wild_held_item)
			victory_message += f"\n🎁 {self.wild.display_name} dropou {item_display}!"
			pm.give_item(self.user_id, wild_held_item, 1)
		
		await self.interaction.channel.send(victory_message)
		await self.cleanup()
	
	async def _handle_defeat(self) -> None:
		self.ended = True
		if self.actions_view:
			self.actions_view.disable_all()
		await self.refresh()
		await self.interaction.channel.send(f"<@{self.user_id}> <:YouGotMogged:1424196005519298570> **Você perdeu!**\nNa próxima, tente usar estratégias válidas.")
		await self.cleanup()
	
	async def _handle_forced_switch(self) -> None:
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
				await self.battle.message.reply(content="Batalha Expirada!\nA batalha foi encerrada por inatividade.")
	
	def disable_all(self) -> None:
		for item in self.children:
			item.disabled = True
	
	@discord.ui.button(style=discord.ButtonStyle.primary, label="Lutar", emoji="⚔️", row=0)
	async def fight(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("Batalha encerrada.", ephemeral=True)
		if self.force_switch_mode:
			return await interaction.response.edit_message(view=SwitchView(self.battle, force_only=True))
		await interaction.response.edit_message(view=MovesView(self.battle))
	
	@discord.ui.button(style=discord.ButtonStyle.primary, label="Trocar", emoji="🔄", row=0)
	async def switch(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("Batalha encerrada.", ephemeral=True)
		await interaction.response.edit_message(view=SwitchView(self.battle))
	
	@discord.ui.button(style=discord.ButtonStyle.danger, label="Fugir", emoji="💨", row=0)
	async def run(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
		if str(interaction.user.id) != self.user_id:
			return await interaction.response.send_message("Não é sua batalha!", ephemeral=True)
		if self.battle.ended:
			return await interaction.response.send_message("Batalha encerrada.", ephemeral=True)
		if self.force_switch_mode:
			return await interaction.response.send_message("Você precisa trocar de Pokémon primeiro!", ephemeral=True)
		
		await interaction.response.defer()

		await self.battle.attempt_run()
