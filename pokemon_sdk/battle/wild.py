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
		self.field = {
			"spikes_player": 0, 
			"spikes_wild": 0, 
			"trick_room": 0, 
			"gravity": 0,
			"mud_sport": 0,
			"water_sport": 0
		}
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
		
		# Weather display
		weather_icons = {"sun": "☀️", "rain": "🌧️", "hail": "❄️", "sandstorm": "🌪️"}
		if self.weather["type"] and self.weather["turns"] > 0:
			icon = weather_icons.get(self.weather["type"], "🌤️")
			description_components.append(
				f"{icon} {self.weather['type'].title()} ({self.weather['turns']} turnos)"
			)
		
		# Field effects
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
		
		embed.set_footer(text="Effex Engine v1.5 — B.A.G.O.S")
		embed.set_image(url="attachment://battle.png")
		return embed
	
	async def start(self) -> None:
		self.battle_participants.add(self.active_player_idx)
		self.actions_view = WildBattleView(self)
		self.lines = [f"A batalha começou! Vamos lá, {self.player_active.display_name}!"]
		
		# Entry hazards damage
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
	
	def _check_move_restrictions(self, user: BattlePokemon, move_id: str, move_data: MoveData) -> Optional[str]:
		"""Verifica se o movimento pode ser usado."""
		
		# Recharge após Hyper Beam
		if user.volatile.get("must_recharge"):
			user.volatile["must_recharge"] = False
			return f"⚡ {user.display_name} precisa recarregar!"
		
		# Flinch
		if user.volatile.get("flinch"):
			return f"😰 {user.display_name} se encolheu!"
		
		# Disable
		if user.volatile.get("disable", 0) > 0:
			disabled_move = user.volatile.get("disable_move")
			if disabled_move and _slug(disabled_move) == _slug(move_id):
				return f"🚫 {move_data.name} está desabilitado!"
		
		# Encore - força uso de um movimento específico
		if user.volatile.get("encore", 0) > 0:
			encore_move = user.volatile.get("encore_move")
			if encore_move and _slug(encore_move) != _slug(move_id):
				return f"👏 {user.display_name} deve usar {encore_move}!"
		
		# Taunt - não pode usar movimentos de status
		if user.volatile.get("taunt", 0) > 0 and move_data.dmg_class == "status":
			return f"😤 {user.display_name} está provocado e não pode usar movimentos de status!"
		
		# Torment - não pode repetir o último movimento
		if user.volatile.get("torment"):
			last_move = user.volatile.get("torment_last_move")
			if last_move and _slug(last_move) == _slug(move_id):
				return f"😈 {user.display_name} não pode repetir o mesmo movimento!"
		
		# Imprison - não pode usar movimentos que o oponente tem
		if user.volatile.get("imprisoned_moves"):
			if _slug(move_id) in user.volatile["imprisoned_moves"]:
				return f"🔒 {move_data.name} está selado!"
		
		# Attract/Infatuation
		if user.volatile.get("attract") or user.volatile.get("attracted"):
			if random.random() < 0.5:  # 50% chance de não atacar
				return f"💕 {user.display_name} está apaixonado e não consegue atacar!"
		
		# Heal Block previne movimentos de cura
		effect_data = self._get_effect_data(move_id)
		if user.volatile.get("heal_block", 0) > 0:
			if effect_data.get("type") == "heal" or "heal" in str(move_data.name).lower():
				return f"🚫 {user.display_name} não pode usar movimentos de cura!"
		
		return None
	
	async def _execute_move(
		self,
		user: BattlePokemon,
		target: BattlePokemon,
		move_data: MoveData,
		move_id: Optional[str]
	) -> List[str]:
		is_struggle = move_id == "__struggle__"
		
		# Decrementar PP
		if move_id and not is_struggle:
			pp = user.get_pp(move_id)
			if pp is not None and pp <= 0:
				return [f"❌ {user.display_name} não tem PP para {move_data.name}!"]
			user.dec_pp(move_id)
			user.volatile["last_move_used"] = move_id
			user.volatile["last_move_type"] = move_data.type_name.lower()
			
			# Atualiza torment
			if user.volatile.get("torment"):
				user.volatile["torment_last_move"] = move_id
		
		effect_data = self._get_effect_data(move_id or "tackle")
		
		# Protect/Detect
		if target.volatile.get("protect") and move_data.dmg_class != "status":
			return [BattleMessages.protected(target.display_name)]
		
		# King's Shield
		if target.volatile.get("kings_shield") and move_data.dmg_class != "status":
			if effect_data.get("makes_contact"):
				user.modify_stat_stage("atk", -1)
				return [
					BattleMessages.protected(target.display_name),
					f"   └─ ⚔️ Ataque de {user.display_name} foi reduzido pelo contato!"
				]
			return [BattleMessages.protected(target.display_name)]
		
		# Spiky Shield
		if target.volatile.get("spiky_shield") and move_data.dmg_class != "status":
			if effect_data.get("makes_contact"):
				damage = max(1, user.stats["hp"] // 8)
				user.take_damage(damage, ignore_substitute=True)
				return [
					BattleMessages.protected(target.display_name),
					f"   └─ 🔱 {user.display_name} foi machucado pelos espinhos! ({damage} de dano)"
				]
			return [BattleMessages.protected(target.display_name)]
		
		# Baneful Bunker
		if target.volatile.get("baneful_bunker") and move_data.dmg_class != "status":
			if effect_data.get("makes_contact"):
				result = StatusHandler.apply_status_effect(user, "poison")
				return [
					BattleMessages.protected(target.display_name),
					result if result else f"   └─ ☠️ {user.display_name} foi envenenado!"
				]
			return [BattleMessages.protected(target.display_name)]
		
		# Semi-invulnerable (Fly, Dig, Dive, etc)
		if target.is_semi_invulnerable():
			# Alguns movimentos atingem durante semi-invulnerabilidade
			two_turn_move = target.volatile.get("two_turn_move", "")
			
			# Earthquake/Magnitude atinge Dig
			if two_turn_move == "dig" and _slug(move_id) in ["earthquake", "magnitude"]:
				pass  # Continua
			# Gust/Twister atinge Fly/Bounce
			elif two_turn_move in ["fly", "bounce"] and _slug(move_id) in ["gust", "twister"]:
				pass  # Continua
			# Surf/Whirlpool atinge Dive
			elif two_turn_move == "dive" and _slug(move_id) in ["surf", "whirlpool"]:
				pass  # Continua
			# Thunder atinge durante Fly
			elif two_turn_move == "fly" and _slug(move_id) == "thunder":
				pass  # Continua
			else:
				return [f"💨 {user.display_name} errou! {target.display_name} está inacessível!"]
		
		# Accuracy check
		if move_data.accuracy is not None and not effect_data.get("bypass_accuracy", False):
			accuracy = move_data.accuracy
			
			# Mind Reader/Lock-On garante acerto
			if user.volatile.get("mind_reader_target") == target:
				accuracy = None
				user.volatile["mind_reader_target"] = None
				user.volatile["mind_reader_turns"] = 0
			
			# No Guard ability sempre acerta
			user_ability = user.get_effective_ability()
			target_ability = target.get_effective_ability()
			if user_ability == "no_guard" or target_ability == "no_guard":
				accuracy = None
			
			# Calcula modificadores de accuracy/evasion
			if accuracy is not None:
				acc_stage = user.stages.get("accuracy", 0)
				eva_stage = target.stages.get("evasion", 0)
				
				# Foresight/Odor Sleuth/Miracle Eye ignoram evasão
				if target.volatile.get("foresight") or target.volatile.get("identified") or target.volatile.get("miracle_eye"):
					eva_stage = min(0, eva_stage)  # Ignora aumentos
				
				# Keen Eye/Unaware ignoram mudanças de evasão
				if user_ability == "keen_eye":
					eva_stage = 0
				if user_ability == "unaware":
					acc_stage = 0
					eva_stage = 0
				
				# Gravity aumenta accuracy
				if self.field.get("gravity", 0) > 0:
					acc_stage += 2
				
				stage_diff = acc_stage - eva_stage
				stage_multiplier = max(3, 3 + stage_diff) / max(3, 3 - stage_diff)
				
				final_accuracy = accuracy * stage_multiplier
				
				if random.randint(1, 100) > int(final_accuracy):
					return [BattleMessages.miss(user.display_name, move_data.name)]
		
		# Executa o movimento
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
				# Skill Link ability sempre dá 5 hits
				if user.get_effective_ability() == "skill_link":
					hits = max_hits
				else:
					# 35% chance de 2 hits, 35% de 3, 15% de 4, 15% de 5
					roll = random.random()
					if roll < 0.35:
						hits = 2
					elif roll < 0.70:
						hits = 3
					elif roll < 0.85:
						hits = 4
					else:
						hits = 5
		
		total_damage = 0
		first_multiplier, first_crit = 1.0, False
		actual_hits = 0
		
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
			
			# Thaw com movimento de fogo
			if target.status["name"] == "freeze" and move_data.type_name.lower() == "fire" and damage > 0:
				target.status = {"name": None, "counter": 0}
				lines.append(f"🔥 {target.display_name} descongelou!")
			
			# Wake-Up Slap acorda o alvo
			if effect_data.get("wake_up_slap") and target.status["name"] == "sleep":
				target.status = {"name": None, "counter": 0}
				lines.append(f"👋 {target.display_name} acordou!")
			
			# Smelling Salts cura paralisia
			if effect_data.get("smelling_salts") and target.status["name"] == "paralysis":
				target.status = {"name": None, "counter": 0}
				lines.append(f"👃 {target.display_name} se recuperou da paralisia!")
			
			actual_damage = target.take_damage(damage)
			total_damage += actual_damage
			actual_hits += 1
			
			# Interrompe se o alvo desmaiou
			if target.fainted:
				# Destiny Bond
				if target.volatile.get("destiny_bond"):
					user.current_hp = 0
					lines.append(f"👻 Destiny Bond ativado! {user.display_name} também caiu!")
				
				# Grudge drena todo o PP
				if target.volatile.get("grudge") and not is_struggle:
					move_data_user = user.get_move_data(user.volatile.get("last_move_used"))
					if move_data_user:
						move_data_user["pp"] = 0
						lines.append(f"👻 Grudge ativou! PP de {move_data.name} foi drenado!")
				
				break
		
		# Mensagem de dano
		if is_struggle:
			lines.insert(0, f"💢 {user.display_name} não tem PP!")
			lines.insert(1, f"Usou **Struggle**! ({total_damage} de dano)")
		else:
			lines.insert(0, BattleMessages.damage(user.display_name, move_data.name, total_damage))
		
		# Detalhes (hits, crit, effectiveness)
		detail_line = BattleMessages.details(actual_hits if actual_hits > 1 else None, first_crit, first_multiplier)
		if detail_line:
			lines.insert(1, detail_line)
		
		if target.fainted:
			lines.append(BattleMessages.fainted(target.display_name))
		
		# Recoil damage
		recoil_damage = self._calculate_recoil(total_damage, effect_data, is_struggle, user)
		if recoil_damage:
			lines.append(recoil_damage)
		
		# Drain/Absorb healing
		drain_healing = self._calculate_drain(total_damage, effect_data, user)
		if drain_healing:
			lines.append(drain_healing)
		
		# Recharge (Hyper Beam, etc)
		if effect_data.get("recharge"):
			user.volatile["must_recharge"] = True
		
		# Increment counters
		self._update_move_counters(user, move_data, effect_data, did_hit=True)
		
		# Efeitos secundários
		for effect in effect_data.get("effects", []):
			effect_results = self.effect_handler.apply_effect(user, target, effect, total_damage)
			if effect_results:
				lines.extend(effect_results)
		
		# Rage boost quando atinge
		if user.volatile.get("rage") or user.volatile.get("rage_active"):
			if total_damage > 0:
				user.modify_stat_stage("atk", 1)
				lines.append(f"   └─ 😡 Ataque de {user.display_name} aumentou pela Rage!")
		
		return lines
	
	def _update_move_counters(
		self, 
		user: BattlePokemon, 
		move_data: MoveData, 
		effect_data: Dict[str, Any],
		did_hit: bool
	) -> None:
		"""Atualiza contadores de movimentos consecutivos."""
		move_id = _slug(move_data.id)
		
		# Rollout
		if move_id == "rollout":
			if did_hit:
				user.volatile["rollout_count"] = user.volatile.get("rollout_count", 0) + 1
			else:
				user.volatile["rollout_count"] = 0
		
		# Ice Ball
		if move_id == "ice_ball":
			if did_hit:
				user.volatile["ice_ball_count"] = user.volatile.get("ice_ball_count", 0) + 1
			else:
				user.volatile["ice_ball_count"] = 0
		
		# Fury Cutter
		if move_id == "fury_cutter":
			if did_hit:
				user.volatile["fury_cutter_count"] = user.volatile.get("fury_cutter_count", 0) + 1
			else:
				user.volatile["fury_cutter_count"] = 0
		
		# Echoed Voice
		if move_id == "echoed_voice":
			if did_hit:
				user.volatile["echoed_voice_count"] = user.volatile.get("echoed_voice_count", 0) + 1
			else:
				user.volatile["echoed_voice_count"] = 0
		
		# Marca se o último movimento acertou
		user.volatile["last_move_hit"] = did_hit
	
	def _calculate_recoil(
		self,
		total_damage: int,
		effect_data: Dict[str, Any],
		is_struggle: bool,
		user: BattlePokemon
	) -> Optional[str]:
		# Rock Head ability previne recoil
		if user.get_effective_ability() == "rock_head" and not is_struggle:
			return None
		
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
			
			# Big Root aumenta drenagem em 30%
			if user.volatile.get("held_item") == "big_root":
				drain = int(drain * 1.3)
			
			# Liquid Ooze causa dano ao invés de curar
			# (precisaria checar ability do alvo)
			
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
		
		# Magic Coat reflete movimentos de status
		if target.volatile.get("magic_coat"):
			lines.append(f"   └─ ✨ {target.display_name} refletiu com Magic Coat!")
			# Troca user e target
			user, target = target, user
		
		# Snatch rouba movimentos que afetam o usuário
		if effect_data.get("target") == "self" and target.volatile.get("snatch"):
			lines.append(f"   └─ 🎯 {target.display_name} roubou o movimento com Snatch!")
			user, target = target, user
		
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
		
		# Pre-action status checks (sleep, freeze, paralysis)
		action_blocked, pre_messages = StatusHandler.check_pre_action(user)
		if action_blocked:
			return pre_messages
		
		# Confusion check
		confusion_blocked, confusion_messages = StatusHandler.check_confusion(user)
		if confusion_blocked:
			return pre_messages + confusion_messages
		
		# Move restriction checks
		restriction_msg = self._check_move_restrictions(user, move_id, move_data)
		if restriction_msg:
			return pre_messages + confusion_messages + [restriction_msg]
		
		# Executa o movimento
		move_result = await self._execute_move(user, target, move_data, move_id)
		
		return pre_messages + confusion_messages + move_result
	
	def _select_enemy_move(self) -> str:
		"""Seleciona movimento do inimigo considerando restrições."""
		available_moves = []
		
		for m in self.wild.moves:
			move_id = str(m["id"])
			pp = int(m.get("pp", 0))
			
			if pp <= 0:
				continue
			
			# Verifica se está desabilitado
			if self.wild.is_move_disabled(move_id):
				continue
			
			available_moves.append(m)
		
		if not available_moves:
			return "__struggle__"
		
		# Escolha aleatória (AI simples)
		return str(random.choice(available_moves)["id"])
	
	def _determine_turn_order(
		self,
		player_move: MoveData,
		enemy_move: MoveData
	) -> List[str]:
		"""Determina ordem de turno considerando prioridade e velocidade."""
		
		# Prioridade
		if player_move.priority != enemy_move.priority:
			return ["player", "enemy"] if player_move.priority > enemy_move.priority else ["enemy", "player"]
		
		# Velocidade
		player_speed = self.player_active.eff_stat("speed")
		enemy_speed = self.wild.eff_stat("speed")
		
		# Quick Claw (item que dá 20% de chance de atacar primeiro)
		player_item = self.player_active.volatile.get("held_item", "")
		enemy_item = self.wild.volatile.get("held_item", "")
		
		if player_item == "quick_claw" and random.random() < 0.2:
			return ["player", "enemy"]
		if enemy_item == "quick_claw" and random.random() < 0.2:
			return ["enemy", "player"]
		
		# Trick Room inverte ordem de velocidade
		if self.field.get("trick_room", 0) > 0:
			if player_speed != enemy_speed:
				return ["player", "enemy"] if player_speed < enemy_speed else ["enemy", "player"]
		else:
			if player_speed != enemy_speed:
				return ["player", "enemy"] if player_speed > enemy_speed else ["enemy", "player"]
		
		# Speed tie - aleatório
		return random.choice([["player", "enemy"], ["enemy", "player"]])
	
	def _process_entry_hazards(self, pokemon: BattlePokemon, is_player: bool) -> List[str]:
		"""Processa dano de entry hazards ao entrar em campo."""
		lines = []
		
		# Spikes
		spikes_key = "spikes_player" if is_player else "spikes_wild"
		spikes_layers = self.field.get(spikes_key, 0)
		
		if spikes_layers > 0:
			# Flying types e Levitate são imunes
			if "flying" in pokemon.types or pokemon.get_effective_ability() == "levitate":
				return lines
			
			# Magic Guard previne dano indireto
			if pokemon.get_effective_ability() == "magic_guard":
				return lines
			
			# Dano: 1 layer = 12.5%, 2 layers = 16.66%, 3 layers = 25%
			damage_ratios = {1: 0.125, 2: 0.1666, 3: 0.25}
			damage = max(1, int(pokemon.stats["hp"] * damage_ratios.get(spikes_layers, 0.125)))
			
			actual = pokemon.take_damage(damage, ignore_substitute=True)
			lines.append(f"⚠️ {pokemon.display_name} foi ferido por Spikes! ({actual} de dano)")
		
		return lines
	
	async def handle_player_move(self, move_id: str) -> None:
		async with self.lock:
			if self.ended:
				return
			
			self.lines = []
			
			# Limpa volatiles de turno
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
			
			# End of turn processing
			await self._process_end_of_turn()
			
			if self.wild.fainted:
				await self._handle_victory()
			elif self.player_active.fainted:
				await self._handle_player_faint()
			
			if not self.ended:
				self.turn += 1
			
			await self.refresh()
	
	async def _process_end_of_turn(self) -> None:
		"""Processa todos os efeitos de fim de turno."""
		self.lines.append("")
		
		# Status conditions (poison, burn, etc)
		status_effects = StatusHandler.end_of_turn_effects(self.player_active, self.wild)
		if status_effects:
			self.lines.extend(status_effects)
		
		# Volatile effects para cada Pokémon
		for pokemon, prefix in [(self.player_active, "🔵"), (self.wild, "🔴")]:
			if pokemon.fainted:
				continue
			
			# Leech Seed
			if pokemon.volatile.get("leech_seed"):
				seeder = pokemon.volatile.get("leech_seed_by")
				if seeder and not seeder.fainted:
					drain = max(1, pokemon.stats["hp"] // 8)
					actual_drain = pokemon.take_damage(drain, ignore_substitute=True)
					actual_heal = seeder.heal(actual_drain)
					self.lines.append(
						f"🌱 {prefix} {pokemon.display_name} perdeu {actual_drain} HP para Leech Seed!"
					)
					if actual_heal > 0:
						self.lines.append(f"   └─ {seeder.display_name} recuperou {actual_heal} HP!")
			
			# Bind/Wrap damage
			if pokemon.volatile.get("bind", 0) > 0:
				bind_damage = pokemon.volatile.get("bind_damage", pokemon.stats["hp"] // 16)
				actual = pokemon.take_damage(bind_damage, ignore_substitute=True)
				bind_type = pokemon.volatile.get("bind_type", "bind")
				self.lines.append(
					f"🎯 {prefix} {pokemon.display_name} sofreu {actual} de dano de {bind_type}!"
				)
			
			# Ingrain healing
			if pokemon.volatile.get("ingrain"):
				heal = max(1, pokemon.stats["hp"] // 16)
				actual = pokemon.heal(heal)
				if actual > 0:
					self.lines.append(
						f"🌿 {prefix} {pokemon.display_name} recuperou {actual} HP com Ingrain!"
					)
			
			# Aqua Ring healing
			if pokemon.volatile.get("aqua_ring"):
				heal = max(1, pokemon.stats["hp"] // 16)
				actual = pokemon.heal(heal)
				if actual > 0:
					self.lines.append(
						f"💧 {prefix} {pokemon.display_name} recuperou {actual} HP com Aqua Ring!"
					)
			
			# Wish healing (decreases counter, heals when reaches 0)
			if pokemon.volatile.get("wish", 0) > 0:
				pokemon.volatile["wish"] -= 1
				if pokemon.volatile["wish"] == 0:
					wish_hp = pokemon.volatile.get("wish_hp", pokemon.stats["hp"] // 2)
					actual = pokemon.heal(wish_hp)
					if actual > 0:
						self.lines.append(
							f"⭐ {prefix} O desejo de {pokemon.display_name} se realizou! (+{actual} HP)"
						)
			
			# Nightmare damage
			if pokemon.volatile.get("nightmare") and pokemon.status.get("name") == "sleep":
				damage = max(1, pokemon.stats["hp"] // 4)
				actual = pokemon.take_damage(damage, ignore_substitute=True)
				self.lines.append(
					f"😱 {prefix} {pokemon.display_name} está tendo pesadelos! ({actual} de dano)"
				)
			
			# Curse damage
			if pokemon.volatile.get("curse"):
				damage = max(1, pokemon.stats["hp"] // 4)
				actual = pokemon.take_damage(damage, ignore_substitute=True)
				self.lines.append(
					f"👻 {prefix} {pokemon.display_name} foi amaldiçoado! ({actual} de dano)"
				)
			
			# Perish Song counter
			if pokemon.volatile.get("perish_count", -1) >= 0:
				pokemon.volatile["perish_count"] -= 1
				count = pokemon.volatile["perish_count"]
				
				if count == 0:
					pokemon.current_hp = 0
					self.lines.append(
						f"🎵 {prefix} {pokemon.display_name} desmaiou pela Perish Song!"
					)
				elif count > 0:
					self.lines.append(
						f"🎵 {prefix} Perish count: {count}"
					)
		
		# Decrement volatile counters
		for pokemon in [self.player_active, self.wild]:
			if pokemon.fainted:
				continue
			
			# Bind
			if pokemon.volatile.get("bind", 0) > 0:
				pokemon.volatile["bind"] -= 1
				if pokemon.volatile["bind"] <= 0:
					pokemon.volatile["bind"] = 0
					pokemon.volatile["bind_by"] = None
					self.lines.append(f"   └─ {pokemon.display_name} se libertou!")
			
			# Yawn -> Sleep
			if pokemon.volatile.get("yawn", 0) > 0:
				pokemon.volatile["yawn"] += 1
				if pokemon.volatile["yawn"] >= 2:
					pokemon.volatile["yawn"] = 0
					result = StatusHandler.apply_status_effect(pokemon, "sleep")
					if result:
						self.lines.append(result)
			
			# Encore
			if pokemon.volatile.get("encore", 0) > 0:
				pokemon.volatile["encore"] -= 1
				if pokemon.volatile["encore"] <= 0:
					pokemon.volatile["encore"] = 0
					pokemon.volatile["encore_move"] = None
					self.lines.append(f"   └─ Encore de {pokemon.display_name} acabou!")
			
			# Disable
			if pokemon.volatile.get("disable", 0) > 0:
				pokemon.volatile["disable"] -= 1
				if pokemon.volatile["disable"] <= 0:
					pokemon.volatile["disable"] = 0
					pokemon.volatile["disable_move"] = None
			
			# Taunt
			if pokemon.volatile.get("taunt", 0) > 0:
				pokemon.volatile["taunt"] -= 1
				if pokemon.volatile["taunt"] <= 0:
					pokemon.volatile["taunt"] = 0
					self.lines.append(f"   └─ Taunt de {pokemon.display_name} acabou!")
			
			# Uproar
			if pokemon.volatile.get("uproar", 0) > 0:
				pokemon.volatile["uproar"] -= 1
				if pokemon.volatile["uproar"] <= 0:
					pokemon.volatile["uproar"] = 0
					pokemon.volatile["uproar_active"] = False
					self.lines.append(f"   └─ {pokemon.display_name} parou de fazer alvoroço!")
			
			# Magnet Rise, Telekinesis, etc
			for key in ["magnet_rise", "telekinesis", "heal_block", "embargo"]:
				if pokemon.volatile.get(key, 0) > 0:
					pokemon.volatile[key] -= 1
			
			# Light Screen, Reflect, Safeguard, Mist
			for key in ["light_screen", "reflect", "safeguard", "mist"]:
				if pokemon.volatile.get(key, 0) > 0:
					pokemon.volatile[key] -= 1
					if pokemon.volatile[key] <= 0:
						effect_names = {
							"light_screen": "Light Screen",
							"reflect": "Reflect",
							"safeguard": "Safeguard",
							"mist": "Mist"
						}
						self.lines.append(
							f"   └─ {effect_names[key]} de {pokemon.display_name} acabou!"
						)
		
		# Weather effects
		await self._process_weather_effects()
		
		# Field effects
		await self._process_field_effects()
	
	async def _process_weather_effects(self) -> None:
		"""Processa efeitos de clima."""
		if not self.weather["type"] or self.weather["turns"] <= 0:
			return
		
		self.weather["turns"] -= 1
		
		if self.weather["turns"] == 0:
			self.lines.append("🌤️ O clima voltou ao normal!")
			self.weather["type"] = None
			return
		
		weather_type = self.weather["type"]
		
		# Sandstorm damage
		if weather_type == "sandstorm":
			for pokemon, prefix in [(self.player_active, "🔵"), (self.wild, "🔴")]:
				if pokemon.fainted:
					continue
				
				# Imune: Rock, Ground, Steel types, Sand Veil/Rush, Overcoat, Magic Guard
				types = pokemon.get_effective_types()
				ability = pokemon.get_effective_ability()
				
				if any(t in types for t in ["rock", "ground", "steel"]):
					continue
				if ability in ["sand_veil", "sand_rush", "sand_force", "overcoat", "magic_guard"]:
					continue
				
				damage = max(1, int(pokemon.stats["hp"] * BattleConstants.SANDSTORM_DAMAGE_RATIO))
				actual = pokemon.take_damage(damage, ignore_substitute=True)
				self.lines.append(
					f"🌪️ {prefix} {pokemon.display_name} sofreu {actual} de dano da tempestade de areia!"
				)
		
		# Hail damage
		elif weather_type == "hail":
			for pokemon, prefix in [(self.player_active, "🔵"), (self.wild, "🔴")]:
				if pokemon.fainted:
					continue
				
				# Imune: Ice type, Snow Cloak, Ice Body, Overcoat, Magic Guard
				types = pokemon.get_effective_types()
				ability = pokemon.get_effective_ability()
				
				if "ice" in types:
					continue
				if ability in ["snow_cloak", "ice_body", "overcoat", "magic_guard"]:
					continue
				
				damage = max(1, int(pokemon.stats["hp"] * BattleConstants.HAIL_DAMAGE_RATIO))
				actual = pokemon.take_damage(damage, ignore_substitute=True)
				self.lines.append(
					f"❄️ {prefix} {pokemon.display_name} sofreu {actual} de dano do granizo!"
				)
				
				# Ice Body cura ao invés de causar dano
				if ability == "ice_body":
					heal = max(1, pokemon.stats["hp"] // 16)
					actual_heal = pokemon.heal(heal)
					if actual_heal > 0:
						self.lines.append(
							f"   └─ Ice Body curou {actual_heal} HP!"
						)
	
	async def _process_field_effects(self) -> None:
		"""Processa efeitos de campo."""
		
		# Trick Room
		if self.field.get("trick_room", 0) > 0:
			self.field["trick_room"] -= 1
			if self.field["trick_room"] <= 0:
				self.field["trick_room"] = 0
				self.lines.append("🔄 Trick Room acabou!")
		
		# Gravity
		if self.field.get("gravity", 0) > 0:
			self.field["gravity"] -= 1
			if self.field["gravity"] <= 0:
				self.field["gravity"] = 0
				self.lines.append("⬇️ Gravity voltou ao normal!")
		
		# Mud Sport
		if self.field.get("mud_sport", 0) > 0:
			self.field["mud_sport"] -= 1
		
		# Water Sport
		if self.field.get("water_sport", 0) > 0:
			self.field["water_sport"] -= 1
	
	async def switch_active(self, new_index: int, consume_turn: bool = True) -> None:
		async with self.lock:
			if self.ended or new_index == self.active_player_idx:
				return
			if not (0 <= new_index < len(self.player_team)) or self.player_team[new_index].fainted:
				return
			
			self.lines = []
			old_name = self.player_active.display_name
			
			# Baton Pass transfere efeitos
			if self.player_active.volatile.get("baton_pass_active"):
				effects_to_pass = self.player_active.volatile.get("baton_pass_effects", {})
				self.player_active.volatile["baton_pass_active"] = False
			else:
				effects_to_pass = None
			
			self.active_player_idx = new_index
			self.battle_participants.add(new_index)
			self.must_redraw_image = True
			
			# Aplica efeitos do Baton Pass
			if effects_to_pass:
				self.player_active._apply_baton_pass_effects(effects_to_pass)
				self.lines.append(f"🎯 {old_name} passou seus efeitos!")
			
			self.lines.extend([
				f"🔄 {old_name} voltou!" if not effects_to_pass else "",
				f"Vamos lá, {self.player_active.display_name}!"
			])
			
			# Entry hazards
			entry_damage = self._process_entry_hazards(self.player_active, is_player=True)
			if entry_damage:
				self.lines.extend(entry_damage)
			
			# Intimidate ability
			ability = self.player_active.get_effective_ability()
			if ability == "intimidate":
				self.wild.modify_stat_stage("atk", -1)
				self.lines.append(f"😤 Intimidate baixou o ataque de {self.wild.display_name}!")
			
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
				
				await self._process_end_of_turn()
				
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
		
		# Exp. Share distribui XP para todos
		# Lucky Egg aumenta XP em 50%
		
		participant_count = len(self.battle_participants)
		if participant_count == 0:
			return []
		
		experience_per_pokemon = max(1, base_experience // participant_count)
		
		distribution = []
		for participant_index in self.battle_participants:
			pokemon_data = self.player_party_raw[participant_index]
			exp_to_give = experience_per_pokemon
			
			# Lucky Egg bonus
			if self.player_team[participant_index].volatile.get("held_item") == "lucky_egg":
				exp_to_give = int(exp_to_give * 1.5)
			
			exp_result = pm.repo.tk.add_exp(self.user_id, pokemon_data["id"], exp_to_give)

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
			
			await self._process_end_of_turn()
			
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
		await interaction.response.defer()

		await self.battle.attempt_capture()


