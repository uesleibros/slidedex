import discord
from typing import Optional
from discord.ext import commands
from helpers.flags import flags, ArgumentParsingError
from helpers.paginator import Paginator
from helpers.checks import requires_account
from utils.formatting import format_pokemon_display
from pokemon_sdk.constants import CATEGORY_NAMES, CATEGORY_ORDER
from .constants import ITEM_EMOJIS
from .item_effects import get_item_effect, requires_target_pokemon, is_consumable
from .item_handlers import ItemHandler
from __main__ import toolkit, pm, battle_tracker

class Bag(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.item_handler = ItemHandler(toolkit, pm)

    def _get_item_category(self, item_id: str) -> str:
        from pokemon_sdk.constants import BERRIES, POKEBALLS
        
        if item_id in BERRIES:
            return "berries"
        elif item_id in POKEBALLS:
            return "pokeballs"
        elif item_id.startswith("tm") or item_id.startswith("hm"):
            return "tms_hms"
        else:
            return "items"

    async def _generate_bag_embed(self, items: list, start: int, end: int, total: int, current_page: int) -> discord.Embed:
        embed = discord.Embed(title="Mochila", color=0x2F3136)
        
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
            emoji = ITEM_EMOJIS.get(item["item_id"], "")
            description_lines.append(f"`{item['item_id']}`　{emoji} {item_name}{item['quantity']:>4}x")
        
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

    @bag_root.command(name="add")
    async def bag_add(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
        uid = str(ctx.author.id)
        
        if quantity <= 0:
            await ctx.send("A quantidade deve ser maior que 0.")
            return
        
        if quantity > 999:
            await ctx.send("Você pode adicionar no máximo 999 itens por vez.")
            return
        
        try:
            current_qty = toolkit.get_item_quantity(uid, item_id)
            
            if current_qty + quantity > 999:
                await ctx.send(f"Limite máximo de 999 unidades. Você tem {current_qty}x.")
                return
            
            result = await pm.give_item(uid, item_id, quantity)
            category = await pm.get_item_category(item_id)
            
            emoji = ITEM_EMOJIS.get(item_id, "")
            await ctx.send(
                f"**Item Adicionado**\n"
                f"{emoji} **{result['name']}** x{quantity}\n"
                f"Quantidade Total: {result['quantity']}x\n"
                f"Categoria: {CATEGORY_NAMES.get(category, category)}"
            )
            
        except ValueError as e:
            await ctx.send(str(e))
        except Exception as e:
            await ctx.send(f"Erro ao adicionar item: {e}")

    @bag_root.command(name="remove")
    async def bag_remove(self, ctx: commands.Context, item_id: str, quantity: int = 1) -> None:
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
            emoji = ITEM_EMOJIS.get(item_id, "")
            
            await ctx.send(
                f"**Item Removido**\n"
                f"{emoji} **{item_name}** x{quantity}\n"
                f"Quantidade Restante: {new_qty}x"
            )
            
        except Exception as e:
            await ctx.send(f"Erro ao remover item: {e}")

    async def _use_out_of_battle(self, ctx: commands.Context, uid: str, item_id: str, party_pos: Optional[int], move_slot: Optional[int]) -> None:
        effect = get_item_effect(item_id)
        
        if not effect:
            await ctx.send(f"Item `{item_id}` não pode ser usado.")
            return
        
        if effect.battle_only:
            item_name = await pm.get_item_name(item_id)
            await ctx.send(f"**{item_name}** só pode ser usado durante batalhas.")
            return
        
        if requires_target_pokemon(item_id):
            if not party_pos:
                await ctx.send(f"Especifique a posição do Pokémon: `.bag use {item_id} <party_position>`")
                return
            
            party = toolkit.get_user_party(uid)
            if not party or party_pos > len(party) or party_pos < 1:
                await ctx.send(f"Posições válidas: 1 a {len(party) if party else 0}")
                return
            
            pokemon = party[party_pos - 1]
            pokemon_id = pokemon["id"]
            item_name = await pm.get_item_name(item_id)
            
            try:
                if effect.type in ["heal", "berry"]:
                    result = await self.item_handler.use_healing_item(uid, pokemon_id, item_id, pokemon)
                    hp_percent = (result['current_hp'] / result['max_hp']) * 100
                    await ctx.send(
                        f"**{item_name} Usado**\n"
                        f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou **{result['healed']} HP**!\n"
                        f"HP Atual: {result['current_hp']}/{result['max_hp']} ({hp_percent:.1f}%)"
                    )
                
                elif effect.type == "revive":
                    result = await self.item_handler.use_revive_item(uid, pokemon_id, item_id, pokemon)
                    await ctx.send(
                        f"**{item_name} Usado**\n"
                        f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi revivido!\n"
                        f"HP Restaurado: {result['restored_hp']}/{result['max_hp']}"
                    )
                
                elif effect.type in ["pp_restore", "pp_boost"]:
                    result = await self.item_handler.use_pp_item(uid, pokemon_id, item_id, pokemon, move_slot)
                    
                    if effect.type == "pp_restore":
                        moves_info = "\n".join([
                            f"{m['id'].replace('-', ' ').title()}: {m['pp']}/{m['pp_max']}"
                            for m in result['moves']
                        ])
                        await ctx.send(
                            f"**{item_name} Usado**\n"
                            f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!\n\n"
                            f"**Movimentos:**\n{moves_info}"
                        )
                    else:
                        move_name = result['move']['id'].replace('-', ' ').title()
                        await ctx.send(
                            f"**{item_name} Usado**\n"
                            f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)}\n"
                            f"Movimento: **{move_name}**\n"
                            f"PP Máximo: {result['move']['pp_max']}\n"
                            f"PP Ups: {result['move'].get('pp_ups', 0)}/3"
                        )
                
                elif effect.type == "vitamin":
                    result = await self.item_handler.use_vitamin(uid, pokemon_id, item_id, pokemon)
                    stat_name = result['stat'].replace('-', ' ').title()
                    await ctx.send(
                        f"**{item_name} Usado**\n"
                        f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} ganhou EVs!\n"
                        f"Stat: {stat_name}\n"
                        f"EVs Ganhos: +{result['ev_gain']}\n"
                        f"EVs Atuais: {result['new_ev']}/100\n"
                        f"EVs Totais: {result['total_evs']}/510"
                    )
                
                elif effect.type == "evolution":
                    result = await self.item_handler.use_evolution_stone(uid, pokemon_id, item_id, pokemon)
                    await ctx.send(
                        f"{ctx.author.mention} <:emojigg_Cap:1424197927496060969> "
                        f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} evoluiu para "
                        f"{format_pokemon_display(result['evolved'], bold_name=True, show_gender=False)}!"
                    )
                
                elif item_id == "rare-candy":
                    if pokemon.get("level", 1) >= 100:
                        await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} já está no nível máximo.")
                        return
                    await pm.use_rare_candy(uid, pokemon_id, ctx.message)
                
                else:
                    await ctx.send("Este item ainda não foi implementado.")
                    
            except ValueError as e:
                await ctx.send(str(e))
        
        elif effect.type == "repel":
            toolkit.remove_item(uid, item_id, 1)
            item_name = await pm.get_item_name(item_id)
            await ctx.send(f"**{item_name}** usado!\nSistema de Repel ainda não implementado.")

    async def _use_in_battle(self, ctx: commands.Context, battle, item_id: str, party_pos: Optional[int]) -> None:
        from pokemon_sdk.battle.pokeballs import PokeBallSystem
        from pokemon_sdk.constants import POKEBALLS
        
        uid = str(ctx.author.id)
        effect = get_item_effect(item_id)
        
        if item_id in POKEBALLS:
            if not hasattr(battle, 'attempt_capture'):
                await ctx.send("Poké Balls só podem ser usadas em batalhas selvagens.")
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
            return
        
        if not effect:
            await ctx.send(f"Item `{item_id}` não pode ser usado em batalha.")
            return
        
        if effect.type == "escape":
            toolkit.remove_item(uid, item_id, 1)
            battle.ended = True
            if battle.actions_view:
                battle.actions_view.disable_all()
            
            await battle.refresh()
            await battle.cleanup()
            item_name = await pm.get_item_name(item_id)
            await ctx.send(f"**{item_name}** usado! Você fugiu da batalha!")
            return
        
        if effect.type == "battle_boost":
            if not party_pos:
                await ctx.send(f"Especifique o Pokémon: `.bag use {item_id} <party_position>`")
                return
            
            party = toolkit.get_user_party(uid)
            if party_pos > len(party) or party_pos < 1:
                await ctx.send(f"Posições válidas: 1 a {len(party)}.")
                return
            
            target_idx = party_pos - 1
            
            if target_idx != battle.active_player_idx:
                await ctx.send("Você só pode usar itens de batalha no Pokémon ativo.")
                return
            
            toolkit.remove_item(uid, item_id, 1)
            
            if effect.stat == "guard_spec":
                battle.player_active.volatile["mist"] = effect.stages
                message = f"**Guard Spec** usado! {battle.player_active.display_name} está protegido!"
            elif effect.stat == "crit_stage":
                battle.player_active.volatile["crit_stage"] = battle.player_active.volatile.get("crit_stage", 0) + effect.stages
                message = f"**Dire Hit** usado! Taxa de crítico aumentou!"
            else:
                current_stage = battle.player_active.stages.get(effect.stat, 0)
                new_stage = min(6, current_stage + effect.stages)
                battle.player_active.stages[effect.stat] = new_stage
                actual_boost = new_stage - current_stage
                
                stat_names = {
                    "atk": "Ataque", "def": "Defesa", "speed": "Velocidade",
                    "accuracy": "Precisão", "sp_atk": "Ataque Especial", "sp_def": "Defesa Especial"
                }
                stat_name = stat_names.get(effect.stat, effect.stat)
                message = f"**{item_id.replace('-', ' ').title()}** usado! {stat_name} aumentou {actual_boost} estágio(s)!"
            
            await ctx.send(message)
            return
        
        if requires_target_pokemon(item_id):
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
            item_name = await pm.get_item_name(item_id)
            
            try:
                if effect.type == "revive":
                    if pokemon.get("current_hp", 1) > 0:
                        await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} não está desmaiado.")
                        return
                    
                    result = await self.item_handler.use_revive_item(uid, pokemon_id, item_id, pokemon)
                    battle.player_team[target_idx].current_hp = result['restored_hp']
                    
                    await ctx.send(
                        f"**{item_name}** usado! "
                        f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} foi revivido com {result['restored_hp']} HP!"
                    )
                    await battle.refresh()
                    return
                
                if effect.type in ["heal", "berry"]:
                    result = await self.item_handler.use_healing_item(uid, pokemon_id, item_id, pokemon)
                    battle.player_team[target_idx].current_hp = result['current_hp']
                    
                    hp_percent = (result['current_hp'] / result['max_hp']) * 100
                    await ctx.send(
                        f"**{item_name}** usado! "
                        f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou {result['healed']} HP! "
                        f"({result['current_hp']}/{result['max_hp']} - {hp_percent:.1f}%)"
                    )
                    await battle.refresh()
                    return
                
                if effect.type in ["pp_restore", "pp_boost"]:
                    result = await self.item_handler.use_pp_item(uid, pokemon_id, item_id, pokemon)
                    battle.player_team[target_idx].moves = result['moves']
                    
                    await ctx.send(
                        f"**{item_name}** usado! "
                        f"{format_pokemon_display(pokemon, bold_name=True, show_gender=False)} recuperou PP!"
                    )
                    await battle.refresh()
                    return
                    
            except ValueError as e:
                await ctx.send(str(e))
        
        await ctx.send(f"Item `{item_id}` não pode ser usado desta forma em batalha.")

    @bag_root.command(name="use")
    @requires_account()
    async def bag_use(self, ctx: commands.Context, item_id: str, party_pos: Optional[int] = None, move_slot: Optional[int] = None) -> None:
        uid = str(ctx.author.id)
        
        if not toolkit.has_item(uid, item_id):
            await ctx.send(f"Você não tem `{item_id}`.")
            return
        
        is_valid = await pm.validate_item(item_id)
        if not is_valid:
            await ctx.send(f"Item `{item_id}` não é válido.")
            return
        
        battle = battle_tracker.get_battle(uid)
        
        if battle:
            await self._use_in_battle(ctx, battle, item_id, party_pos)
        else:
            await self._use_out_of_battle(ctx, uid, item_id, party_pos, move_slot)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Bag(bot))

