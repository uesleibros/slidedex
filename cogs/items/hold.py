import discord
from typing import Optional, Dict, Any, List, Tuple
from discord.ext import commands
from helpers.flags import flags
from helpers.checks import requires_account
from utils.formatting import format_pokemon_display, format_item_display
from cogs.bag.constants import ITEM_EMOJIS
from pokemon_sdk.config import tk, pm

EMBED_COLOR = 0x2F3136
DEFAULT_ITEM_EMOJI = "📦"
NO_ITEM_EMOJI = "❌"

ERROR_MESSAGES = {
    'no_item': "Você não tem `{item_id}` na mochila.",
    'not_holdable': "**{item_name}** não pode ser equipado por Pokémon.",
    'already_holding': "{pokemon} já está equipado com **{item_name}**.\nUse `.hold swap` para trocar.",
    'not_holding': "{pokemon} não possui item equipado.",
    'invalid_item': "Item `{item_id}` inválido.",
    'invalid_position': "Posição inválida. Escolha entre 1 e {max}.",
    'empty_party': "Você não tem Pokémon no party.",
    'no_equipped_items': "Nenhum Pokémon está com item equipado.",
}

SUCCESS_MESSAGES = {
    'item_equipped': "{pokemon} agora está usando {emoji} **{item}**",
    'item_unequipped': "{emoji} **{item}** foi removido de {pokemon}",
    'item_swapped': "{pokemon}\n{old_emoji} ~~{old_item}~~ → {new_emoji} **{new_item}**",
}

class HeldItemManager:
    def __init__(self):
        pass
    
    def validate_party_position(self, party_pos: int, party_size: int) -> Optional[str]:
        if not party_size:
            return ERROR_MESSAGES['invalid_position'].format(max=0)
        
        if not (1 <= party_pos <= party_size):
            return ERROR_MESSAGES['invalid_position'].format(max=party_size)
        
        return None
    
    def get_party_pokemon(self, uid: str, party_pos: int) -> Tuple[Optional[Dict], Optional[str]]:
        party = tk.get_user_party(uid)
        
        if not party:
            return None, ERROR_MESSAGES['empty_party']
        
        error = self.validate_party_position(party_pos, len(party))
        if error:
            return None, error
        
        return party[party_pos - 1], None
    
    def validate_item(self, uid: str, item_id: str) -> Tuple[bool, Optional[str]]:
        if not tk.has_item(uid, item_id):
            return False, ERROR_MESSAGES['no_item'].format(item_id=item_id)
        
        if not pm.validate_item(item_id):
            return False, ERROR_MESSAGES['invalid_item'].format(item_id=item_id)
        
        if not pm.is_holdable(item_id):
            return False, ERROR_MESSAGES['not_holdable'].format(item_name=format_item_display(item_id))
        
        return True, None
    
    def get_item_emoji(self, item_id: Optional[str]) -> str:
        if not item_id:
            return NO_ITEM_EMOJI
        return ITEM_EMOJIS.get(item_id, DEFAULT_ITEM_EMOJI)
    
    def get_item_display(self, item_id: Optional[str]) -> Tuple[str, str]:
        if not item_id:
            return NO_ITEM_EMOJI, "Sem item"
        
        emoji = self.get_item_emoji(item_id)
        name = pm.get_item_name(item_id)
        return emoji, name
    
    def equip_item(self, uid: str, pokemon_id: int, item_id: str) -> Dict:
        tk.remove_item(uid, item_id, 1)
        tk.set_pokemon_held_item(uid, pokemon_id, item_id)
        
        emoji = self.get_item_emoji(item_id)
        name = pm.get_item_name(item_id)
        
        return {"emoji": emoji, "name": name}
    
    def unequip_item(self, uid: str, pokemon_id: int, item_id: str) -> Dict:
        tk.set_pokemon_held_item(uid, pokemon_id, None)
        pm.give_item(uid, item_id, 1)
        
        emoji = self.get_item_emoji(item_id)
        name = pm.get_item_name(item_id)
        
        return {"emoji": emoji, "name": name}
    
    def swap_item(
        self,
        uid: str,
        pokemon_id: int,
        old_item_id: Optional[str],
        new_item_id: str
    ) -> Dict:
        tk.remove_item(uid, new_item_id, 1)
        
        if old_item_id:
            pm.give_item(uid, old_item_id, 1)
            old_emoji, old_name = self.get_item_display(old_item_id)
        else:
            old_emoji, old_name = NO_ITEM_EMOJI, "Nenhum"
        
        tk.set_pokemon_held_item(uid, pokemon_id, new_item_id)
        new_emoji, new_name = self.get_item_display(new_item_id)
        
        return {
            "old_emoji": old_emoji,
            "old_name": old_name,
            "new_emoji": new_emoji,
            "new_name": new_name
        }


class HeldItems(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.manager = HeldItemManager()

    def format_pokemon(self, pokemon: Dict) -> str:
        return format_pokemon_display(pokemon, bold_name=True, show_gender=False, show_item=False)

    def _build_party_items(self, party: List[Dict]) -> str:        
        equipped_count = sum(1 for p in party if p.get("held_item"))
        text = ''
        
        for i, pokemon in enumerate(party, 1):
            pokemon_display = self.format_pokemon(pokemon)
            text += (
                f"\n{i}. {pokemon_display}\n"
                f"{format_item_display(pokemon.get('held_item'), bold_name=False)}\n"
            )
        
        text += f"\n-# {equipped_count}/{len(party)} Pokémon com itens equipados"
        return text.strip()

    def _build_item_info_embed(self, pokemon: Dict, item_id: str) -> discord.Embed:
        item_name = pm.get_item_name(item_id)
        item_effect = pm.get_item_effect(item_id)
        emoji = self.manager.get_item_emoji(item_id)
        
        embed = discord.Embed(
            title=f"{emoji} {item_name}",
            color=EMBED_COLOR
        )
        
        embed.add_field(
            name="Equipado em",
            value=self.format_pokemon(pokemon),
            inline=False
        )
        
        if item_effect:
            embed.add_field(
                name="Efeito",
                value=item_effect,
                inline=False
            )
        
        embed.add_field(
            name="Identificador",
            value=f"`{item_id}`",
            inline=True
        )
        
        category = pm.get_item_category(item_id)
        embed.add_field(
            name="Categoria",
            value=category.title(),
            inline=True
        )
        
        return embed

    def _build_cleared_items(self, removed_items: List[Dict]) -> str:
        text = ''

        for i, pokemon in enumerate(removed_items, 1):
            pokemon_display = self.format_pokemon(pokemon)
            text += (
                f"\n{i}. {pokemon_display}\n"
                f"{format_item_display(pokemon.get('held_item'), bold_name=False)}\n"
            )
        
        text += f"\n-# {len(removed_items)} itens retornados à mochila"
        return text.strip()

    @flags.group(name="hold", aliases=["held", "item"], invoke_without_command=True)
    @requires_account()
    async def hold_root(self, ctx: commands.Context) -> None:
        uid = str(ctx.author.id)
        party = tk.get_user_party(uid)
        
        if not party:
            await ctx.send(ERROR_MESSAGES['empty_party'])
            return
        
        party_items = self._build_party_items(party)
        await ctx.send(party_items)

    @hold_root.command(name="give", aliases=["equip", "add", "set"])
    @requires_account()
    async def hold_give(self, ctx: commands.Context, item_id: str, party_pos: int) -> None:
        uid = str(ctx.author.id)
        
        pokemon, error = self.manager.get_party_pokemon(uid, party_pos)
        if error:
            await ctx.send(error)
            return
        
        is_valid, error = self.manager.validate_item(uid, item_id)
        if not is_valid:
            await ctx.send(error)
            return
        
        if pokemon.get("held_item"):
            await ctx.send(
                ERROR_MESSAGES['already_holding'].format(
                    pokemon=self.format_pokemon(pokemon),
                    item_name=format_item_display(pokemon["held_item"], bold_name=True)
                )
            )
            return
        
        result = self.manager.equip_item(uid, pokemon["id"], item_id)
        
        await ctx.send(
            SUCCESS_MESSAGES['item_equipped'].format(
                pokemon=self.format_pokemon(pokemon),
                emoji=result["emoji"],
                item=result["name"]
            )
        )

    @hold_root.command(name="take", aliases=["remove", "unequip"])
    @requires_account()
    async def hold_take(self, ctx: commands.Context, party_pos: int) -> None:
        uid = str(ctx.author.id)
        
        pokemon, error = self.manager.get_party_pokemon(uid, party_pos)
        if error:
            await ctx.send(error)
            return
        
        item_id = pokemon.get("held_item")
        if not item_id:
            await ctx.send(
                ERROR_MESSAGES['not_holding'].format(pokemon=self.format_pokemon(pokemon))
            )
            return
        
        result = self.manager.unequip_item(uid, pokemon["id"], item_id)
        
        await ctx.send(
            SUCCESS_MESSAGES['item_unequipped'].format(
                pokemon=self.format_pokemon(pokemon),
                emoji=result["emoji"],
                item=result["name"]
            )
        )

    @hold_root.command(name="swap", aliases=["change", "switch", "replace"])
    @requires_account()
    async def hold_swap(self, ctx: commands.Context, new_item_id: str, party_pos: int) -> None:
        uid = str(ctx.author.id)
        
        pokemon, error = self.manager.get_party_pokemon(uid, party_pos)
        if error:
            await ctx.send(error)
            return
        
        is_valid, error = self.manager.validate_item(uid, new_item_id)
        if not is_valid:
            await ctx.send(error)
            return
        
        old_item_id = pokemon.get("held_item")
        
        result = self.manager.swap_item(uid, pokemon["id"], old_item_id, new_item_id)
        
        await ctx.send(
            SUCCESS_MESSAGES['item_swapped'].format(
                pokemon=self.format_pokemon(pokemon),
                old_emoji=result["old_emoji"],
                old_item=result["old_name"],
                new_emoji=result["new_emoji"],
                new_item=result["new_name"]
            )
        )

    @hold_root.command(name="info", aliases=["show", "details"])
    @requires_account()
    async def hold_info(self, ctx: commands.Context, party_pos: int) -> None:
        uid = str(ctx.author.id)
        
        pokemon, error = self.manager.get_party_pokemon(uid, party_pos)
        if error:
            await ctx.send(error)
            return
        
        item_id = pokemon.get("held_item")
        if not item_id:
            await ctx.send(
                ERROR_MESSAGES['not_holding'].format(pokemon=self.format_pokemon(pokemon))
            )
            return
        
        embed = self._build_item_info_embed(pokemon, item_id)
        await ctx.send(embed=embed)

    @hold_root.command(name="clear", aliases=["removeall", "unequipall"])
    @requires_account()
    async def hold_clear(self, ctx: commands.Context) -> None:
        uid = str(ctx.author.id)
        party = tk.get_user_party(uid)
        
        if not party:
            await ctx.send(ERROR_MESSAGES['empty_party'])
            return
        
        removed_items = []
        
        for pokemon in party:
            item_id = pokemon.get("held_item")
            if item_id:
                result = self.manager.unequip_item(uid, pokemon["id"], item_id)
                removed_items.append(pokemon)
        
        if not removed_items:
            await ctx.send(ERROR_MESSAGES['no_equipped_items'])
            return
        
        cleared_items = self._build_cleared_items(removed_items)
        await ctx.send(cleared_items)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HeldItems(bot))

