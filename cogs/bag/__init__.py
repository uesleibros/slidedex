import discord
from typing import Optional, Dict, Any
from discord.ext import commands
from helpers.paginator import Paginator
from helpers.flags import flags
from helpers.checks import requires_account
from utils.formatting import format_pokemon_display, format_item_display
from .constants import CATEGORY_NAMES
from .effects import get_item_effect, requires_target_pokemon
from .handlers import ItemHandler
from __main__ import toolkit, pm, battle_tracker

EMBED_COLOR = 0x2F3136
MAX_ITEM_QUANTITY = 999

ERROR_MESSAGES = {
	'empty_bag': "Sua mochila está vazia.",
	'invalid_quantity': "A quantidade deve ser maior que 0.",
	'max_quantity_exceeded': f"Você pode adicionar no máximo {MAX_ITEM_QUANTITY} itens por vez.",
	'quantity_limit': "Limite máximo de {max} unidades. Você tem {current}x.",
	'item_not_found': "Você não tem `{item_id}`.",
	'invalid_item': "Item `{item_id}` não é válido.",
	'cannot_use_item': "{item_name} não pode ser usado.",
	'battle_only': "**{item_name}** só pode ser usado durante batalhas.",
	'specify_position': "Especifique a posição do Pokémon: `.bag use {item_id} <party_position>`",
	'invalid_position': "Posições válidas: 1 a {max}",
	'pokeball_wild_only': "Poké Balls só podem ser usadas em batalhas selvagens.",
	'battle_item_active_only': "Você só pode usar itens de batalha no Pokémon ativo.",
	'cannot_use_in_battle': "Item `{item_id}` não pode ser usado desta forma em batalha.",
	'not_implemented': "Este item ainda não foi implementado.",
}

STAT_NAMES = {
	"atk": "Ataque",
	"def": "Defesa",
	"speed": "Velocidade",
	"accuracy": "Precisão",
	"sp_atk": "Ataque Especial",
	"sp_def": "Defesa Especial",
	"hp": "HP",
	"attack": "Ataque",
	"defense": "Defesa",
	"special-attack": "Ataque Especial",
	"special-defense": "Defesa Especial"
}

class Bag(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.item_handler = ItemHandler(toolkit, pm)

	async def _generate_bag_embed(self, items: list, start: int, end: int, total: int, current_page: int) -> discord.Embed:
		embed = discord.Embed(title="Mochila", color=EMBED_COLOR)
		
		if not items:
			embed.description = ERROR_MESSAGES['empty_bag']
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
			
			description_lines.append(f"`{item['item_id']}`　{format_item_display(item['item_id'])}{item['quantity']:>4}x")
		
		embed.description = "\n".join(description_lines)
		embed.set_footer(text=f"Página {current_page + 1} • {total} tipos de itens")
		
		return embed

	@flags.group(name="bag", invoke_without_command=True)
	@requires_account()
	async def bag_root(self, ctx: commands.Context) -> None:
		uid = str(ctx.author.id)
		bag = toolkit.get_bag(uid)
		
		if not bag:
			await ctx.send(ERROR_MESSAGES['empty_bag'])
			return
				
		paginator = Paginator(
			items=bag,
			user_id=ctx.author.id,
			embed_generator=self._generate_bag_embed,
			page_size=25,
			current_page=1
		)
		
		embed = await paginator.get_embed()
		await ctx.send(embed=embed, view=paginator)

	@bag_root.command(name="add")
	async def bag_add(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
		uid = str(ctx.author.id)
		
		if quantity <= 0:
			await ctx.send(ERROR_MESSAGES['invalid_quantity'])
			return
		
		if quantity > MAX_ITEM_QUANTITY:
			await ctx.send(ERROR_MESSAGES['max_quantity_exceeded'])
			return
		
		try:
			current_qty = toolkit.get_item_quantity(uid, item_id)
			
			if current_qty + quantity > MAX_ITEM_QUANTITY:
				await ctx.send(
					ERROR_MESSAGES['quantity_limit'].format(
						max=MAX_ITEM_QUANTITY,
						current=current_qty
					)
				)
				return
			
			result = await pm.give_item(uid, item_id, quantity)
			category = await pm.get_item_category(item_id)
			
			await ctx.send(
				f"Adicionado {format_item_display(item_id, bold_name=True)} x{quantity}\n"
				f"Quantidade Total: {result['quantity']}x\n"
				f"Categoria: {CATEGORY_NAMES.get(category, category)}"
			)
			
		except ValueError as e:
			await ctx.send(f"{str(e)}")
		except Exception as e:
			await ctx.send(f"Erro ao adicionar item: {e}")

	@bag_root.command(name="remove")
	async def bag_remove(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
		uid = str(ctx.author.id)
		
		if quantity <= 0:
			await ctx.send(ERROR_MESSAGES['invalid_quantity'])
			return
		
		try:
			if not toolkit.has_item(uid, item_id, quantity):
				await ctx.send(f"Você não tem {quantity}x `{item_id}`.")
				return
			
			new_qty = toolkit.remove_item(uid, item_id, quantity)
			
			await ctx.send(
				f"Removeu {format_item_display(item_id, bold_name=True)} x{quantity}\n"
				f"Quantidade Restante: {new_qty}x"
			)
			
		except Exception as e:
			await ctx.send(f"Erro ao remover item: {e}")

	def _validate_party_position(self, party: list, party_pos: int) -> Optional[str]:
		if not party:
			return ERROR_MESSAGES['invalid_position'].format(max=0)
		
		if party_pos < 1 or party_pos > len(party):
			return ERROR_MESSAGES['invalid_position'].format(max=len(party))
		
		return None

	async def _use_out_of_battle(
		self,
		ctx: commands.Context,
		uid: str,
		item_id: str,
		party_pos: Optional[int],
		move_slot: Optional[int]
	) -> None:
		effect = get_item_effect(item_id)
		
		if not effect:
			await ctx.send(ERROR_MESSAGES['cannot_use_item'].format(item_name=format_item_display(item_id, bold_name=True)))
			return
		
		if effect.battle_only:
			await ctx.send(ERROR_MESSAGES['battle_only'].format(item_name=format_item_display(item_id, bold_name=True)))
			return
		
		if effect.type == "sacred_ash":
			await self._use_sacred_ash(ctx, uid)
			return
		
		if effect.type == "repel":
			await self._use_repel(ctx, uid, item_id)
			return
		
		if requires_target_pokemon(item_id):
			await self._use_item_on_pokemon(ctx, uid, item_id, party_pos, move_slot)

	async def _use_item_on_pokemon(
		self,
		ctx: commands.Context,
		uid: str,
		item_id: str,
		party_pos: Optional[int],
		move_slot: Optional[int]
	) -> None:
		if not party_pos:
			await ctx.send(ERROR_MESSAGES['specify_position'].format(item_id=item_id))
			return
		
		party = toolkit.get_user_party(uid)
		error = self._validate_party_position(party, party_pos)
		if error:
			await ctx.send(error)
			return
		
		pokemon = party[party_pos - 1]
		pokemon_id = pokemon["id"]
		effect = get_item_effect(item_id)
		item_name = await pm.get_item_name(item_id)
		
		try:
			handlers = {
				"heal": self._handle_heal,
				"berry": self._handle_heal,
				"revive": self._handle_revive,
				"status": self._handle_status_heal,
				"pp_restore": self._handle_pp_restore,
				"pp_boost": self._handle_pp_boost,
				"vitamin": self._handle_vitamin,
				"ev_reducer": self._handle_ev_reducer,
				"evolution": self._handle_evolution,
				"rare-candy": self._handle_rare_candy,
				"confusion_heal_restore": self._handle_confusion_heal_restore,
				"flute": self._handle_flute,
			}
			
			handler = handlers.get(effect.type)
			if handler:
				await handler(ctx, uid, pokemon_id, item_id, item_name, pokemon, move_slot)
			else:
				await ctx.send(ERROR_MESSAGES['not_implemented'])
				
		except ValueError as e:
			await ctx.send(f"{str(e)}")

	async def _handle_heal(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_healing_item(uid, pokemon_id, item_id, pokemon)
		hp_percent = (result['current_hp'] / result['max_hp']) * 100
		
		await ctx.send(
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou **{result['healed']} HP**!\n"
			f"❤️ HP Atual: {result['current_hp']}/{result['max_hp']} ({hp_percent:.1f}%)"
		)

	async def _handle_revive(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_revive_item(uid, pokemon_id, item_id, pokemon)
		
		await ctx.send(
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi revivido!\n"
			f"❤️ HP Restaurado: {result['restored_hp']}/{result['max_hp']}"
		)

	async def _handle_status_heal(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		from pokemon_sdk.battle.constants import STATUS_TAGS
		result = await self.item_handler.use_status_heal_item(uid, pokemon_id, item_id, pokemon)
		
		status_emoji = STATUS_TAGS.get(result['cured_status'], "✨")
		
		await ctx.send(
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi curado de {status_emoji} **{result['cured_status']}**!"
		)

	async def _handle_pp_restore(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_pp_item(uid, pokemon_id, item_id, pokemon, move_slot)
		
		moves_info = "\n".join([
			f"• {m['id'].replace('-', ' ').title()}: {m['pp']}/{m['pp_max']}"
			for m in result['moves']
		])
		
		await ctx.send(
			f"✅ **{item_name} Usado**\n"
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!\n\n"
			f"**Movimentos:**\n{moves_info}"
		)

	async def _handle_pp_boost(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_pp_item(uid, pokemon_id, item_id, pokemon, move_slot)
		move_name = result['move']['id'].replace('-', ' ').title()
		
		await ctx.send(
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)}\n"
			f"🎯 Movimento: **{move_name}**\n"
			f"📊 PP Máximo: {result['move']['pp_max']}\n"
			f"⬆️ PP Ups: {result['move'].get('pp_ups', 0)}/3"
		)

	async def _handle_vitamin(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_vitamin(uid, pokemon_id, item_id, pokemon)
		stat_name = STAT_NAMES.get(result['stat'], result['stat'].title())
		
		await ctx.send(
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} ganhou EVs!\n"
			f"📊 **Stat:** {stat_name}\n"
			f"➕ **EVs Ganhos:** +{result['ev_gain']}\n"
			f"📈 **EVs Atuais:** {result['new_ev']}/100\n"
			f"📊 **EVs Totais:** {result['total_evs']}/510"
		)

	async def _handle_ev_reducer(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_ev_reducing_berry(uid, pokemon_id, item_id, pokemon)
		stat_name = STAT_NAMES.get(result['stat'], result['stat'].title())
		
		await ctx.send(
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} reduziu EVs!\n"
			f"📊 **Stat:** {stat_name}\n"
			f"➖ **EVs Reduzidos:** -{result['ev_reduced']}\n"
			f"📉 **EVs Atuais:** {result['new_ev']}/100\n"
			f"📊 **EVs Totais:** {result['total_evs']}/510"
		)

	async def _handle_evolution(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_evolution_stone(uid, pokemon_id, item_id, pokemon)
		
		await pm.evolution_ui.send_evolution_message(
			channel=ctx.channel,
			owner_id=uid,
			pokemon_id=pokemon_id,
			current_pokemon=pokemon,
			evolution_species_id=result['evolved']['species_id']
		)

	async def _handle_rare_candy(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		if pokemon.get("level", 1) >= 100:
			await ctx.send(
				f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} já está no nível máximo."
			)
			return
		
		await pm.use_rare_candy(uid, pokemon_id, ctx.message)

	async def _handle_confusion_heal_restore(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_confusion_berry(uid, pokemon_id, item_id, pokemon)
		hp_percent = (result['current_hp'] / result['max_hp']) * 100
		
		message = (
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou **{result['healed']} HP**!\n"
			f"❤️ HP Atual: {result['current_hp']}/{result['max_hp']} ({hp_percent:.1f}%)"
		)
		
		if result['confusion_applied']:
			message += "\nPokémon ficou confuso por não gostar do sabor!"
		
		await ctx.send(message)

	async def _handle_flute(
		self,
		ctx: commands.Context,
		uid: str,
		pokemon_id: int,
		item_id: str,
		item_name: str,
		pokemon: Dict,
		move_slot: Optional[int]
	) -> None:
		result = await self.item_handler.use_flute(uid, pokemon_id, item_id, pokemon)
		
		await ctx.send(
			f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi curado de **{result['cured_status']}**!"
		)

	async def _use_sacred_ash(self, ctx: commands.Context, uid: str) -> None:
		try:
			result = await self.item_handler.use_sacred_ash(uid)
			
			revived_list = "\n".join([
				f"• {p['name'].title()} - {p['restored_hp']} HP"
				for p in result['revived_pokemon']
			])
			
			await ctx.send(
				f"✨ **Sacred Ash Usado**\n"
				f"Todos os Pokémon desmaiados foram revividos!\n\n"
				f"**Pokémon Revividos ({result['revived_count']}):**\n{revived_list}"
			)
		except ValueError as e:
			await ctx.send(f"{str(e)}")

	async def _use_repel(self, ctx: commands.Context, uid: str, item_id: str) -> None:
		toolkit.remove_item(uid, item_id, 1)
		item_name = await pm.get_item_name(item_id)
		await ctx.send(f"Sistema de Repel ainda não implementado.")

	async def _use_in_battle(
		self,
		ctx: commands.Context,
		battle,
		item_id: str,
		party_pos: Optional[int]
	) -> None:
		from pokemon_sdk.battle.pokeballs import PokeBallSystem, BallType
		
		uid = str(ctx.author.id)
		POKEBALLS = {v for v in BallType.__dict__.values() if isinstance(v, str)}
		
		if item_id in POKEBALLS:
			await self._use_pokeball(ctx, battle, uid, item_id)
			return
		
		effect = get_item_effect(item_id)
		if not effect:
			await ctx.send(ERROR_MESSAGES['cannot_use_in_battle'].format(item_id=item_id))
			return
		
		battle_handlers = {
			"escape": self._battle_escape,
			"battle_boost": self._battle_boost,
		}
		
		handler = battle_handlers.get(effect.type)
		if handler:
			await handler(ctx, battle, uid, item_id, party_pos, effect)
		elif requires_target_pokemon(item_id):
			await self._use_recovery_in_battle(ctx, battle, uid, item_id, party_pos, effect)
		else:
			await ctx.send(ERROR_MESSAGES['cannot_use_in_battle'].format(item_id=item_id))

	async def _use_pokeball(
		self,
		ctx: commands.Context,
		battle,
		uid: str,
		item_id: str
	) -> None:
		from pokemon_sdk.battle.pokeballs import PokeBallSystem
		
		if not hasattr(battle, 'attempt_capture'):
			await ctx.send(ERROR_MESSAGES['pokeball_wild_only'])
			return
		
		ball_name = PokeBallSystem.get_ball_name(item_id)
		ball_emoji = PokeBallSystem.get_ball_emoji(item_id)
		
		if not toolkit.has_item(uid, item_id, 1):
			await ctx.send(f"Você não tem {ball_emoji} **{ball_name}**!")
			return
		
		toolkit.remove_item(uid, item_id, 1)
		battle.ball_type = item_id
		
		await ctx.send(f"{ball_emoji} Você lançou uma **{ball_name}**!")
		await battle.attempt_capture(item_id)

	async def _battle_escape(
		self,
		ctx: commands.Context,
		battle,
		uid: str,
		item_id: str,
		party_pos: Optional[int],
		effect
	) -> None:
		toolkit.remove_item(uid, item_id, 1)
		item_name = await pm.get_item_name(item_id)
		
		battle.ended = True
		if battle.actions_view:
			battle.actions_view.disable_all()
		
		await battle.refresh()
		await battle.cleanup()
		
		await ctx.send(f"Você fugiu da batalha!")

	async def _battle_boost(
		self,
		ctx: commands.Context,
		battle,
		uid: str,
		item_id: str,
		party_pos: Optional[int],
		effect
	) -> None:
		if not party_pos:
			await ctx.send(ERROR_MESSAGES['specify_position'].format(item_id=item_id))
			return
		
		party = toolkit.get_user_party(uid)
		error = self._validate_party_position(party, party_pos)
		if error:
			await ctx.send(error)
			return
		
		target_idx = party_pos - 1
		
		if target_idx != battle.active_player_idx:
			await ctx.send(ERROR_MESSAGES['battle_item_active_only'])
			return
		
		toolkit.remove_item(uid, item_id, 1)
		
		if effect.stat == "guard_spec":
			battle.player_active.volatile["mist"] = effect.stages
			message = f"🛡️ **Guard Spec** usado! {battle.player_active.display_name} está protegido!"
		elif effect.stat == "crit_stage":
			battle.player_active.volatile["crit_stage"] = battle.player_active.volatile.get("crit_stage", 0) + effect.stages
			message = f"🎯 **Dire Hit** usado! Taxa de crítico de {battle.player_active.display_name} aumentou!"
		else:
			current_stage = battle.player_active.stages.get(effect.stat, 0)
			new_stage = min(6, current_stage + effect.stages)
			battle.player_active.stages[effect.stat] = new_stage
			actual_boost = new_stage - current_stage
			
			stat_name = STAT_NAMES.get(effect.stat, effect.stat.title())
			item_name = item_id.replace('-', ' ').title()
			
			message = (
				f"{stat_name} de {battle.player_active.display_name} aumentou {actual_boost} estágio(s)!"
			)
		
		await ctx.send(message)

	async def _use_recovery_in_battle(
		self,
		ctx: commands.Context,
		battle,
		uid: str,
		item_id: str,
		party_pos: Optional[int],
		effect
	) -> None:
		if not party_pos:
			await ctx.send(ERROR_MESSAGES['specify_position'].format(item_id=item_id))
			return
		
		party = toolkit.get_user_party(uid)
		error = self._validate_party_position(party, party_pos)
		if error:
			await ctx.send(error)
			return
		
		target_idx = party_pos - 1
		pokemon = party[target_idx]
		pokemon_id = pokemon["id"]
		item_name = await pm.get_item_name(item_id)
		
		try:
			if effect.type == "revive":
				if pokemon.get("current_hp", 1) > 0:
					await ctx.send(
						f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} não está desmaiado."
					)
					return
				
				result = await self.item_handler.use_revive_item(uid, pokemon_id, item_id, pokemon)
				battle.player_team[target_idx].current_hp = result['restored_hp']
				
				await ctx.send(
					f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi revivido com {result['restored_hp']} HP!"
				)
				await battle.refresh()
			
			elif effect.type in ["heal", "berry"]:
				result = await self.item_handler.use_healing_item(uid, pokemon_id, item_id, pokemon)
				battle.player_team[target_idx].current_hp = result['current_hp']
				
				hp_percent = (result['current_hp'] / result['max_hp']) * 100
				await ctx.send(
					f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou {result['healed']} HP!\n"
					f"❤️ {result['current_hp']}/{result['max_hp']} ({hp_percent:.1f}%)"
				)
				await battle.refresh()
			
			elif effect.type in ["pp_restore", "pp_boost"]:
				result = await self.item_handler.use_pp_item(uid, pokemon_id, item_id, pokemon)
				battle.player_team[target_idx].moves = result['moves']
				
				await ctx.send(
					f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!"
				)
				await battle.refresh()
			
			elif effect.type in ["status", "flute"]:
				if effect.type == "status":
					result = await self.item_handler.use_status_heal_item(uid, pokemon_id, item_id, pokemon)
				else:
					result = await self.item_handler.use_flute(uid, pokemon_id, item_id, pokemon)
				
				battle.player_team[target_idx].status = None
				
				await ctx.send(
					f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi curado de **{result['cured_status']}**!"
				)
				await battle.refresh()
				
		except ValueError as e:
			await ctx.send(f"{str(e)}")

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
			await ctx.send(ERROR_MESSAGES['item_not_found'].format(item_id=item_id))
			return
		
		is_valid = await pm.validate_item(item_id)
		if not is_valid:
			await ctx.send(ERROR_MESSAGES['invalid_item'].format(item_id=item_id))
			return
		
		battle = battle_tracker.get_battle(uid)
		
		if battle:
			await self._use_in_battle(ctx, battle, item_id, party_pos)
		else:
			await self._use_out_of_battle(ctx, uid, item_id, party_pos, move_slot)


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Bag(bot))