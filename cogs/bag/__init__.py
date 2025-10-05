import discord
from typing import Optional
from discord.ext import commands
from helpers.flags import flags, ArgumentParsingError
from helpers.paginator import Paginator
from helpers.checks import requires_account
from utils.formatting import format_pokemon_display
from pokemon_sdk.constants import (
	CATEGORY_NAMES, CATEGORY_ORDER, HEALING_ITEMS, REVIVE_ITEMS, VITAMINS, PP_RECOVERY, PP_BOOST, 
	EVOLUTION_STONES, BERRIES, POKEBALLS, BATTLE_USABLE_ITEMS
)
from __main__ import toolkit, pm, battle_tracker

STATUS_HEALERS = ["antidote", "parlyz-heal", "awakening", "burn-heal", "ice-heal", "full-heal"]
BATTLE_ITEMS = ["x-attack", "x-defense", "x-speed", "x-accuracy", "x-special", "x-sp-atk", "x-sp-def", "dire-hit", "guard-spec"]
REPELS = ["repel", "super-repel", "max-repel"]
ESCAPE_ITEMS = ["escape-rope", "poke-doll", "fluffy-tail"]

class Bag(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

	def _get_item_category(self, item_id: str) -> str:
		if item_id in BERRIES:
			return "berries"
		elif item_id in POKEBALLS:
			return "pokeballs"
		elif item_id.startswith("tm") or item_id.startswith("hm"):
			return "tms_hms"
		else:
			return "items"
	
	def _convert_ball_id_to_type(self, item_id: str) -> str:
		return item_id.replace("-", "_")
	
	def _convert_ball_type_to_id(self, ball_type: str) -> str:
		return ball_type.replace("_", "-")

	async def _generate_bag_embed(
		self,
		items: list,
		start: int,
		end: int,
		total: int,
		current_page: int
	) -> discord.Embed:
		embed = discord.Embed(
			title="Mochila",
			color=0x2F3136
		)
		
		if not items:
			embed.description = "Sua mochila está vazia."
			return embed
		
		description_lines = []
		current_category = None
		
		for item in items:
			if item["category"] != current_category:
				current_category = item["category"]
				category_name = CATEGORY_NAMES.get(current_category, current_category)
				if description_lines:
					description_lines.append("")
				description_lines.append(f"**{category_name}**")
			
			item_name = item["item_id"].replace("-", " ").title()
			description_lines.append(f"`{item['item_id']}`　{item_name}{item['quantity']:>4}x")
		
		embed.description = "\n".join(description_lines)
		embed.set_footer(text=f"Página {current_page + 1} • {total} tipos de itens")
		
		return embed

	@flags.group(name="bag", invoke_without_command=True)
	@requires_account()
	async def bag_root(self, ctx: commands.Context) -> None:
		uid = str(ctx.author.id)
		bag = toolkit.get_bag(uid)
		
		if not bag:
			await ctx.send("Sua mochila está vazia.")
			return
		
		all_items = []
		for item in bag:
			category = self._get_item_category(item["item_id"])
			all_items.append({
				"item_id": item["item_id"],
				"quantity": item["quantity"],
				"category": category
			})
		
		all_items.sort(key=lambda x: (CATEGORY_ORDER.index(x["category"]), x["item_id"]))
		
		paginator = Paginator(
			items=all_items,
			user_id=ctx.author.id,
			embed_generator=self._generate_bag_embed,
			page_size=25,
			current_page=1
		)
		
		embed = await paginator.get_embed()
		await ctx.send(embed=embed, view=paginator)

	@bag_root.error
	async def bag_root_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
		if isinstance(error, ArgumentParsingError):
			await ctx.send(f"Erro nos argumentos: {str(error)}\n-# Use `.help {ctx.command.qualified_name}` para ver o uso correto.")
			return
		
		if isinstance(error, commands.CommandNotFound):
			return
		
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send(f"Argumento obrigatório faltando: `{error.param.name}`\n-# Use `.help {ctx.command.qualified_name}` para ver o uso correto.")
			return
		
		raise error

	@bag_root.command(name="add")
	async def bag_add(
		self,
		ctx: commands.Context,
		item_id: str,
		quantity: int = 1
	) -> None:
		uid = str(ctx.author.id)
		
		if quantity <= 0:
			await ctx.send("A quantidade deve ser maior que 0.")
			return
		
		if quantity > 99:
			await ctx.send("Você pode adicionar no máximo 99 itens por vez.")
			return
		
		try:
			is_valid = await pm.validate_item(item_id)
			
			if not is_valid:
				await ctx.send(f"Item `{item_id}` não encontrado no Banco de Dados.")
				return
			
			current_qty = toolkit.get_item_quantity(uid, item_id) if hasattr(toolkit, 'get_item_quantity') else 0
			
			if current_qty + quantity > 999:
				await ctx.send(f"Limite máximo de 999 unidades do mesmo item. Você tem {current_qty}x.")
				return
			
			new_qty = toolkit.add_item(uid, item_id, quantity)
			
			item_name = await pm.get_item_name(item_id)
			category = await pm.get_item_category(item_id)
			
			await ctx.send(f"**Item Adicionado**\n**{item_name}** x{quantity}\nQuantidade Total: {new_qty}x\nCategoria: {CATEGORY_NAMES.get(category, category)}")
			
		except Exception as e:
			await ctx.send(f"Erro ao adicionar item: {e}")

	@bag_root.command(name="remove")
	@commands.is_owner()
	async def bag_remove(
		self,
		ctx: commands.Context,
		item_id: str,
		quantity: int = 1
	) -> None:
		uid = str(ctx.author.id)
		
		if quantity <= 0:
			await ctx.send("A quantidade deve ser maior que 0.")
			return
		
		try:
			if not toolkit.has_item(uid, item_id, quantity):
				await ctx.send(f"Você não tem {quantity}x `{item_id}`.")
				return
			
			new_qty = toolkit.remove_item(uid, item_id, quantity)
			
			item_name = await pm.get_item_name(item_id)
			
			await ctx.send(f"**Item Removido**\n**{item_name}** x{quantity}\nQuantidade Restante: {new_qty}x")
			
		except Exception as e:
			await ctx.send(f"Erro ao remover item: {e}")

	async def _use_berry(self, ctx: commands.Context, uid: str, pokemon_id: int, berry_id: str, pokemon: dict) -> None:
		berry_effects = {
			"oran-berry": {"type": "heal", "amount": 10},
			"sitrus-berry": {"type": "heal", "percent": 0.25},
			"pecha-berry": {"type": "status", "cures": "poison"},
			"cheri-berry": {"type": "status", "cures": "paralysis"},
			"chesto-berry": {"type": "status", "cures": "sleep"},
			"rawst-berry": {"type": "status", "cures": "burn"},
			"aspear-berry": {"type": "status", "cures": "freeze"},
			"persim-berry": {"type": "status", "cures": "confusion"},
			"lum-berry": {"type": "status", "cures": "all"},
			"leppa-berry": {"type": "pp", "amount": 10}
		}
		
		effect = berry_effects.get(berry_id)
		
		if not effect:
			await ctx.send("Esta berry ainda não está implementada.")
			return
		
		berry_name = await pm.get_item_name(berry_id)
		
		if effect["type"] == "heal":
			from pokemon_sdk.calculations import calculate_max_hp
			
			max_hp = calculate_max_hp(
				pokemon["base_stats"]["hp"],
				pokemon["ivs"]["hp"],
				pokemon["evs"]["hp"],
				pokemon["level"]
			)
			current_hp = pokemon.get("current_hp", max_hp)
			
			if current_hp >= max_hp:
				await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} já está com HP cheio.")
				return
			
			if "amount" in effect:
				heal_amount = effect["amount"]
			else:
				heal_amount = int(max_hp * effect["percent"])
			
			new_hp = min(current_hp + heal_amount, max_hp)
			healed = new_hp - current_hp
			
			toolkit.set_current_hp(uid, pokemon_id, new_hp)
			toolkit.remove_item(uid, berry_id, 1)
			toolkit.increase_happiness_berry(uid, pokemon_id)
			
			hp_percent = (new_hp / max_hp) * 100

			await ctx.send(f"**{berry_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou **{healed} HP**!\nHP Atual: {new_hp}/{max_hp} ({hp_percent:.1f}%)")
		
		elif effect["type"] == "status":
			toolkit.remove_item(uid, berry_id, 1)
			toolkit.increase_happiness_berry(uid, pokemon_id)
			await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} comeu **{berry_name}**, mas status conditions ainda não foram implementadas.")
		
		elif effect["type"] == "pp":
			moves = pokemon.get("moves", [])
			if not moves:
				await ctx.send("Este Pokémon não tem movimentos.")
				return
			
			restored_any = False
			for move in moves:
				if move["pp"] < move["pp_max"]:
					move["pp"] = min(move["pp"] + effect["amount"], move["pp_max"])
					restored_any = True
			
			if not restored_any:
				await ctx.send("Todos os movimentos já estão com PP máximo.")
				return
			
			toolkit.set_moves(uid, pokemon_id, moves)
			toolkit.remove_item(uid, berry_id, 1)
			toolkit.increase_happiness_berry(uid, pokemon_id)
			
			moves_info = []
			for move in moves:
				move_name = move["id"].replace("-", " ").title()
				moves_info.append(f"{move_name}: {move['pp']}/{move['pp_max']}")
			
			await ctx.send(f"**{berry_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!\n\n**Movimentos:**\n" + "\n".join(moves_info))

	async def _use_healing_item(self, ctx: commands.Context, uid: str, pokemon_id: int, item_id: str, pokemon: dict) -> None:
		result = await pm.use_healing_item(uid, pokemon_id, item_id)
		
		pokemon = toolkit.get_pokemon(uid, pokemon_id)
		item_name = await pm.get_item_name(item_id)
		
		hp_percent = (result['current_hp'] / result['max_hp']) * 100
		
		await ctx.send(f"**{item_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou **{result['healed']} HP**!\nHP Atual: {result['current_hp']}/{result['max_hp']} ({hp_percent:.1f}%)")

	async def _use_revive_item(self, ctx: commands.Context, uid: str, pokemon_id: int, item_id: str, pokemon: dict) -> None:
		result = await pm.use_revive_item(uid, pokemon_id, item_id)
		
		pokemon = toolkit.get_pokemon(uid, pokemon_id)
		item_name = await pm.get_item_name(item_id)
		
		await ctx.send(f"**{item_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi revivido!\nHP Restaurado: {result['restored_hp']}/{result['max_hp']}")

	async def _use_rare_candy(self, ctx: commands.Context, uid: str, pokemon_id: int, pokemon: dict) -> None:
		if pokemon.get("level", 1) >= 100:
			await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} já está no nível máximo (100).")
			return
		
		await pm.use_rare_candy(uid, pokemon_id, ctx.message)
		
	async def _use_vitamin(self, ctx: commands.Context, uid: str, pokemon_id: int, item_id: str, pokemon: dict) -> None:
		vitamin_map = {
			"hp-up": "hp",
			"protein": "attack",
			"iron": "defense",
			"carbos": "speed",
			"calcium": "special-attack",
			"zinc": "special-defense"
		}
		
		stat = vitamin_map.get(item_id)
		if not stat:
			await ctx.send("Este item não é uma vitamina válida.")
			return
		
		current_evs = pokemon.get("evs", {})
		current_stat_ev = current_evs.get(stat, 0)
		
		if current_stat_ev >= 100:
			await ctx.send(f"Este Pokémon já atingiu o limite de EVs (100) para {stat} via vitaminas.")
			return
		
		total_evs = sum(current_evs.values())
		if total_evs >= 510:
			await ctx.send("Este Pokémon já atingiu o limite total de EVs (510).")
			return
		
		ev_gain = min(10, 100 - current_stat_ev, 510 - total_evs)
		
		new_evs = current_evs.copy()
		new_evs[stat] = current_stat_ev + ev_gain
		
		toolkit.set_evs(uid, pokemon_id, new_evs)
		toolkit.remove_item(uid, item_id, 1)
		toolkit.increase_happiness_vitamin(uid, pokemon_id)
		
		item_name = await pm.get_item_name(item_id)
		stat_name = stat.replace("-", " ").title()
		
		await ctx.send(f"**{item_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} ganhou EVs!\nStat: {stat_name}\nEVs Ganhos: +{ev_gain}\nEVs Atuais: {new_evs[stat]}/100\nEVs Totais: {sum(new_evs.values())}/510")

	async def _use_pp_recovery(self, ctx: commands.Context, uid: str, pokemon_id: int, item_id: str, pokemon: dict) -> None:
		moves = pokemon.get("moves", [])
		if not moves:
			await ctx.send("Este Pokémon não tem movimentos.")
			return
		
		recovery_map = {
			"ether": 10,
			"max-ether": 999999,
			"elixir": 10,
			"max-elixir": 999999
		}
		
		recovery = recovery_map.get(item_id, 0)
		if recovery == 0:
			await ctx.send("Este item não recupera PP.")
			return
		
		is_elixir = "elixir" in item_id
		
		updated = False
		for move in moves:
			if is_elixir or move["pp"] < move["pp_max"]:
				move["pp"] = min(move["pp"] + recovery, move["pp_max"])
				updated = True
		
		if not updated:
			await ctx.send("Todos os movimentos já estão com PP máximo.")
			return
		
		toolkit.set_moves(uid, pokemon_id, moves)
		toolkit.remove_item(uid, item_id, 1)
		
		item_name = await pm.get_item_name(item_id)
		
		moves_info = []
		for move in moves:
			move_name = move["id"].replace("-", " ").title()
			moves_info.append(f"{move_name}: {move['pp']}/{move['pp_max']}")
		
		await ctx.send(f"**{item_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!\n\n**Movimentos:**\n" + "\n".join(moves_info))

	async def _use_pp_boost(self, ctx: commands.Context, uid: str, pokemon_id: int, item_id: str, pokemon: dict, move_slot: Optional[int] = None) -> None:
		moves = pokemon.get("moves", [])
		if not moves:
			await ctx.send("Este Pokémon não tem movimentos.")
			return
		
		if len(moves) == 1:
			move_idx = 0
		elif move_slot is not None and 1 <= move_slot <= len(moves):
			move_idx = move_slot - 1
		else:
			await ctx.send(f"Este Pokémon tem {len(moves)} movimentos. Especifique o slot: `.bag use {item_id} <party_pos> <move_slot>`\nSlots: 1-{len(moves)}")
			return
		
		move = moves[move_idx]
		max_pp_ups = 3
		current_pp_ups = move.get("pp_ups", 0)
		
		if current_pp_ups >= max_pp_ups:
			await ctx.send(f"O movimento **{move['id'].replace('-', ' ').title()}** já atingiu o limite de PP Ups.")
			return
		
		boost_amount = move["pp_max"] // 5
		move["pp_max"] += boost_amount
		move["pp"] = min(move["pp"] + boost_amount, move["pp_max"])
		move["pp_ups"] = current_pp_ups + 1
		
		toolkit.set_moves(uid, pokemon_id, moves)
		toolkit.remove_item(uid, item_id, 1)
		
		item_name = await pm.get_item_name(item_id)
		move_name = move["id"].replace("-", " ").title()
		
		await ctx.send(f"**{item_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)}\nMovimento: **{move_name}**\nPP Máximo: {move['pp_max']}\nPP Ups: {move['pp_ups']}/{max_pp_ups}")

	async def _use_status_healer(self, ctx: commands.Context, uid: str, pokemon_id: int, item_id: str, pokemon: dict) -> None:
		toolkit.remove_item(uid, item_id, 1)
		item_name = await pm.get_item_name(item_id)
		await ctx.send(f"**{item_name} Usado**\n{format_pokemon_display(pokemon, bold_name=True, show_gender=False)}\nStatus conditions ainda não foram implementadas.")

	async def _use_evolution_stone(self, ctx: commands.Context, uid: str, pokemon_id: int, item_id: str, pokemon: dict) -> None:
		evolution_data = await pm.check_evolution(uid, pokemon_id, trigger="use-item")
		
		if not evolution_data or evolution_data.get("item") != item_id:
			await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True)} não pode evoluir com este item.")
			return
		
		toolkit.remove_item(uid, item_id, 1)
		evolved = await pm.evolve_pokemon(uid, pokemon_id, evolution_data["species_id"])
		
		await ctx.send(f"{ctx.author.mention} <:emojigg_Cap:1424197927496060969> {format_pokemon_display(pokemon, bold_name=True, show_gender=False)} evoluiu para {format_pokemon_display(evolved, bold_name=True, show_gender=False)}!")

	async def _use_in_battle(
		self,
		ctx: commands.Context,
		battle,
		item_id: str,
		party_pos: Optional[int] = None
	) -> None:
		uid = str(ctx.author.id)
		
		async with battle.lock:
			if battle.ended:
				await ctx.send("A batalha já terminou!")
				return
			
			if battle.actions_view and battle.actions_view.force_switch_mode:
				await ctx.send("Você precisa trocar de Pokémon primeiro!")
				return
			
			if item_id in POKEBALLS:
				if not hasattr(battle, 'attempt_capture'):
					await ctx.send("Poké Balls só podem ser usadas em batalhas selvagens.")
					return
				
				from pokemon_sdk.battle.pokeballs import PokeBallSystem
				
				ball_type = self._convert_ball_id_to_type(item_id)
				ball_name = PokeBallSystem.get_ball_name(ball_type)
				ball_emoji = PokeBallSystem.get_ball_emoji(ball_type)
				
				if not toolkit.has_item(uid, item_id, 1):
					await ctx.send(f"Você não tem {ball_emoji} **{ball_name}**!")
					return
				
				toolkit.remove_item(uid, item_id, 1)
				battle.ball_type = ball_type
				
				await ctx.send(f"{ball_emoji} Você lançou uma **{ball_name}**!")
				await battle.attempt_capture(ball_type)
				return
			
			if item_id in ESCAPE_ITEMS:
				toolkit.remove_item(uid, item_id, 1)
				battle.ended = True
				if battle.actions_view:
					battle.actions_view.disable_all()
				
				await battle.refresh()
				await battle.cleanup()
				item_name = await pm.get_item_name(item_id)
				await ctx.send(f"**{item_name}** usado! Você fugiu da batalha!")
				return
			
			if item_id in BATTLE_ITEMS:
				if not party_pos:
					await ctx.send(f"Especifique o Pokémon: `.bag use {item_id} <party_position>`")
					return
				
				stat_boost_map = {
					"x-attack": ("atk", 2),
					"x-defense": ("def", 2),
					"x-speed": ("speed", 2),
					"x-accuracy": ("accuracy", 2),
					"x-special": ("sp_atk", 2),
					"x-sp-atk": ("sp_atk", 2),
					"x-sp-def": ("sp_def", 2),
					"dire-hit": ("crit_stage", 2),
					"guard-spec": ("guard_spec", 5)
				}
				
				stat, stages = stat_boost_map.get(item_id, (None, 0))
				if not stat:
					await ctx.send(f"Item `{item_id}` não reconhecido.")
					return
				
				party = toolkit.get_user_party(uid)
				if party_pos > len(party) or party_pos < 1:
					await ctx.send(f"Posições válidas: 1 a {len(party)}.")
					return
				
				target_idx = party_pos - 1
				
				if target_idx != battle.active_player_idx:
					await ctx.send("Você só pode usar itens de batalha no Pokémon ativo.")
					return
				
				if battle.player_active.fainted:
					await ctx.send("Seu Pokémon está desmaiado!")
					return
				
				battle.lines = []
				toolkit.remove_item(uid, item_id, 1)
				
				if stat == "guard_spec":
					battle.player_active.volatile["mist"] = stages
					message = f"**Guard Spec** usado! {battle.player_active.display_name} está protegido contra mudanças de status!"
				elif stat == "crit_stage":
					battle.player_active.volatile["crit_stage"] = battle.player_active.volatile.get("crit_stage", 0) + stages
					message = f"**Dire Hit** usado! Taxa de crítico de {battle.player_active.display_name} aumentou!"
				else:
					current_stage = battle.player_active.stages.get(stat, 0)
					new_stage = min(6, current_stage + stages)
					battle.player_active.stages[stat] = new_stage
					actual_boost = new_stage - current_stage
					
					stat_names = {
						"atk": "Ataque",
						"def": "Defesa",
						"speed": "Velocidade",
						"accuracy": "Precisão",
						"sp_atk": "Ataque Especial",
						"sp_def": "Defesa Especial"
					}
					stat_name = stat_names.get(stat, stat)
					message = f"**{item_id.replace('-', ' ').title()}** usado! {stat_name} de {battle.player_active.display_name} aumentou em {actual_boost} estágio(s)!"
				
				battle.lines.append(message)
				battle.lines.append("")
				
				enemy_move_id = battle._select_ai_move(battle.wild)
				await battle.execute_enemy_turn(enemy_move_id, battle.wild, battle.player_active)
				
				state = battle.get_battle_state()
				if state != battle.BattleState.ONGOING:
					await battle.handle_battle_end(state)
					await battle.refresh()
					return
				
				battle.turn += 1
				await battle.refresh()
				return
			
			if item_id in HEALING_ITEMS or item_id in REVIVE_ITEMS or item_id in BERRIES or item_id in PP_RECOVERY:
				if not party_pos:
					await ctx.send(f"Especifique o Pokémon: `.bag use {item_id} <party_position>`")
					return
				
				party = toolkit.get_user_party(uid)
				if party_pos > len(party) or party_pos < 1:
					await ctx.send(f"Posições válidas: 1 a {len(party)}.")
					return
				
				target_idx = party_pos - 1
				pokemon = party[target_idx]
				pokemon_id = pokemon["id"]
				
				if item_id in REVIVE_ITEMS:
					if not pokemon.get("current_hp", 1) <= 0:
						await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} não está desmaiado.")
						return
					
					battle.lines = []
					result = await pm.use_revive_item(uid, pokemon_id, item_id)
					
					battle_pokemon = battle.player_team[target_idx]
					battle_pokemon.current_hp = result['restored_hp']
					
					item_name = await pm.get_item_name(item_id)
					battle.lines.append(f"**{item_name}** usado! {format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi revivido com {result['restored_hp']} HP!")
					battle.lines.append("")
					
					enemy_move_id = battle._select_ai_move(battle.wild)
					await battle.execute_enemy_turn(enemy_move_id, battle.wild, battle.player_active)
					
					state = battle.get_battle_state()
					if state != battle.BattleState.ONGOING:
						await battle.handle_battle_end(state)
						await battle.refresh()
						return
					
					battle.turn += 1
					await battle.refresh()
					return
				
				if pokemon.get("current_hp", 0) <= 0:
					await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} está desmaiado! Use um Revive.")
					return
				
				battle.lines = []
				
				if item_id in HEALING_ITEMS:
					result = await pm.use_healing_item(uid, pokemon_id, item_id)
					
					battle_pokemon = battle.player_team[target_idx]
					battle_pokemon.current_hp = result['current_hp']
					
					item_name = await pm.get_item_name(item_id)
					hp_percent = (result['current_hp'] / result['max_hp']) * 100
					battle.lines.append(f"**{item_name}** usado! {format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou {result['healed']} HP! ({result['current_hp']}/{result['max_hp']} - {hp_percent:.1f}%)")
				
				elif item_id in BERRIES:
					berry_effects = {
						"oran-berry": {"type": "heal", "amount": 10},
						"sitrus-berry": {"type": "heal", "percent": 0.25},
						"leppa-berry": {"type": "pp", "amount": 10}
					}
					
					effect = berry_effects.get(item_id)
					if not effect:
						await ctx.send("Esta berry ainda não está implementada em batalha.")
						return
					
					if effect["type"] == "heal":
						from pokemon_sdk.calculations import calculate_max_hp
						
						max_hp = calculate_max_hp(
							pokemon["base_stats"]["hp"],
							pokemon["ivs"]["hp"],
							pokemon["evs"]["hp"],
							pokemon["level"]
						)
						current_hp = pokemon.get("current_hp", max_hp)
						
						if current_hp >= max_hp:
							await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} já está com HP cheio.")
							return
						
						if "amount" in effect:
							heal_amount = effect["amount"]
						else:
							heal_amount = int(max_hp * effect["percent"])
						
						new_hp = min(current_hp + heal_amount, max_hp)
						healed = new_hp - current_hp
						
						toolkit.set_current_hp(uid, pokemon_id, new_hp)
						toolkit.remove_item(uid, item_id, 1)
						toolkit.increase_happiness_berry(uid, pokemon_id)
						
						battle_pokemon = battle.player_team[target_idx]
						battle_pokemon.current_hp = new_hp
						
						berry_name = await pm.get_item_name(item_id)
						hp_percent = (new_hp / max_hp) * 100
						battle.lines.append(f"**{berry_name}** usado! {format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou {healed} HP! ({new_hp}/{max_hp} - {hp_percent:.1f}%)")
					
					elif effect["type"] == "pp":
						moves = pokemon.get("moves", [])
						if not moves:
							await ctx.send("Este Pokémon não tem movimentos.")
							return
						
						restored_any = False
						for move in moves:
							if move["pp"] < move["pp_max"]:
								move["pp"] = min(move["pp"] + effect["amount"], move["pp_max"])
								restored_any = True
						
						if not restored_any:
							await ctx.send("Todos os movimentos já estão com PP máximo.")
							return
						
						toolkit.set_moves(uid, pokemon_id, moves)
						toolkit.remove_item(uid, item_id, 1)
						toolkit.increase_happiness_berry(uid, pokemon_id)
						
						battle_pokemon = battle.player_team[target_idx]
						battle_pokemon.moves = moves
						
						berry_name = await pm.get_item_name(item_id)
						battle.lines.append(f"**{berry_name}** usado! {format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!")
				
				elif item_id in PP_RECOVERY:
					moves = pokemon.get("moves", [])
					if not moves:
						await ctx.send("Este Pokémon não tem movimentos.")
						return
					
					recovery_map = {
						"ether": 10,
						"max-ether": 999999,
						"elixir": 10,
						"max-elixir": 999999
					}
					
					recovery = recovery_map.get(item_id, 0)
					is_elixir = "elixir" in item_id
					
					updated = False
					for move in moves:
						if is_elixir or move["pp"] < move["pp_max"]:
							move["pp"] = min(move["pp"] + recovery, move["pp_max"])
							updated = True
					
					if not updated:
						await ctx.send("Todos os movimentos já estão com PP máximo.")
						return
					
					toolkit.set_moves(uid, pokemon_id, moves)
					toolkit.remove_item(uid, item_id, 1)
					
					battle_pokemon = battle.player_team[target_idx]
					battle_pokemon.moves = moves
					
					item_name = await pm.get_item_name(item_id)
					battle.lines.append(f"**{item_name}** usado! {format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!")
				
				battle.lines.append("")
				
				enemy_move_id = battle._select_ai_move(battle.wild)
				await battle.execute_enemy_turn(enemy_move_id, battle.wild, battle.player_active)
				
				state = battle.get_battle_state()
				if state != battle.BattleState.ONGOING:
					await battle.handle_battle_end(state)
					await battle.refresh()
					return
				
				battle.turn += 1
				await battle.refresh()
				return
			
			await ctx.send(f"Item `{item_id}` não pode ser usado em batalha.")

	@bag_root.command(name="use")
	@requires_account()
	async def bag_use(
		self,
		ctx: commands.Context,
		item_id: str,
		party_pos: Optional[int] = None,
		move_slot: Optional[int] = None
	) -> None:
		uid = str(ctx.author.id)
		
		if not toolkit.has_item(uid, item_id):
			await ctx.send(f"Você não tem `{item_id}`.")
			return
		
		is_valid = await pm.validate_item(item_id)
		if not is_valid:
			await ctx.send(f"Item `{item_id}` não é válido.")
			return
		
		is_in_battle = battle_tracker.is_battling(uid)
		
		if is_in_battle:
			battle = battle_tracker.get_battle(uid)
			if battle:
				await self._use_in_battle(ctx, battle, item_id, party_pos)
				return
		
		is_battle_only = await pm.is_battle_only_item(item_id)
		
		if is_battle_only and not is_in_battle:
			item_name = await pm.get_item_name(item_id)
			await ctx.send(f"**{item_name}** só pode ser usado durante batalhas.")
			return
		
		if item_id in POKEBALLS and not is_in_battle:
			await ctx.send("Poké Balls só podem ser usadas durante batalhas selvagens.")
			return
		
		if item_id in BATTLE_ITEMS and not is_in_battle:
			item_name = await pm.get_item_name(item_id)
			await ctx.send(f"**{item_name}** só pode ser usado durante batalhas.")
			return
		
		if item_id in REPELS:
			toolkit.remove_item(uid, item_id, 1)
			item_name = await pm.get_item_name(item_id)
			await ctx.send(f"**{item_name}** usado!\nSistema de Repel ainda não implementado.")
			return
		
		if item_id in ESCAPE_ITEMS:
			toolkit.remove_item(uid, item_id, 1)
			item_name = await pm.get_item_name(item_id)
			await ctx.send(f"**{item_name}** usado!\nSistema de Escape ainda não implementado fora de batalha.")
			return
		
		requires_pokemon = (
			item_id in HEALING_ITEMS or 
			item_id in REVIVE_ITEMS or 
			item_id == "rare-candy" or
			item_id in VITAMINS or
			item_id in PP_RECOVERY or
			item_id in PP_BOOST or
			item_id in EVOLUTION_STONES or
			item_id in BERRIES or
			item_id in STATUS_HEALERS
		)
		
		pokemon = None
		pokemon_id = None
		
		if requires_pokemon:
			if not party_pos:
				await ctx.send(f"Você precisa especificar a posição do Pokémon.\nUso: `.bag use {item_id} <party_position>`")
				return
			
			try:
				party = toolkit.get_user_party(uid)
				
				if not party:
					await ctx.send("Você não tem Pokémon na party!")
					return

				if party_pos > len(party) or party_pos < 1:
					return await ctx.send(f"Posições válidas: 1 a {len(party)}.")

				pokemon = party[party_pos - 1]
				pokemon_id = pokemon["id"]
			except (ValueError, IndexError, TypeError):
				await ctx.send(f"Pokémon na posição #{party_pos} não encontrado.")
				return
		
		if not requires_pokemon:
			await ctx.send(f"O item `{item_id}` não pode ser usado ou ainda não foi implementado.")
			return
		
		try:
			if item_id == "rare-candy":
				await self._use_rare_candy(ctx, uid, pokemon_id, pokemon)
			
			elif item_id in HEALING_ITEMS:
				await self._use_healing_item(ctx, uid, pokemon_id, item_id, pokemon)
			
			elif item_id in REVIVE_ITEMS:
				await self._use_revive_item(ctx, uid, pokemon_id, item_id, pokemon)
			
			elif item_id in VITAMINS:
				await self._use_vitamin(ctx, uid, pokemon_id, item_id, pokemon)
			
			elif item_id in PP_RECOVERY:
				await self._use_pp_recovery(ctx, uid, pokemon_id, item_id, pokemon)
			
			elif item_id in PP_BOOST:
				await self._use_pp_boost(ctx, uid, pokemon_id, item_id, pokemon, move_slot)
			
			elif item_id in STATUS_HEALERS:
				await self._use_status_healer(ctx, uid, pokemon_id, item_id, pokemon)
			
			elif item_id in EVOLUTION_STONES:
				await self._use_evolution_stone(ctx, uid, pokemon_id, item_id, pokemon)
			
			elif item_id in BERRIES:
				await self._use_berry(ctx, uid, pokemon_id, item_id, pokemon)
			
			else:
				await ctx.send(f"O item `{item_id}` não pode ser usado ou ainda não foi implementado.")
				
		except ValueError as e:
			await ctx.send(f"{e}")
		except Exception as e:
			await ctx.send(f"Erro ao usar item: {e}")
			import traceback
			traceback.print_exc()

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Bag(bot))
