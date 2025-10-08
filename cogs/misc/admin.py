import discord
from discord.ext import commands
from typing import Optional
from helpers.flags import flags
from helpers.checks import is_owner
from __main__ import pm, toolkit
from utils.formatting import format_pokemon_display
from pokemon_sdk.constants import NATURES, STAT_KEYS

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @flags.add_flag("user", type=discord.Member)
    @flags.add_flag("species", type=int)
    @flags.add_flag("--level", type=int, default=5)
    @flags.add_flag("--shiny", action="store_true")
    @flags.add_flag("--gender", type=str, choices=["male", "female", "genderless"], default=None)
    @flags.add_flag("--nature", type=str, default=None)
    @flags.add_flag("--ability", type=str, default=None)
    @flags.add_flag("--held_item", type=str, default=None)
    @flags.add_flag("--nickname", nargs="+", default=None)
    @flags.add_flag("--on_party", action="store_true")
    @flags.add_flag("--hp", type=int, default=31)
    @flags.add_flag("--atk", type=int, default=31)
    @flags.add_flag("--def", type=int, default=31)
    @flags.add_flag("--spatk", type=int, default=31)
    @flags.add_flag("--spdef", type=int, default=31)
    @flags.add_flag("--spd", type=int, default=31)
    @flags.add_flag("--random_ivs", action="store_true")
    @flags.add_flag("--perfect", action="store_true")
    @flags.add_flag("--no_rewards", action="store_true")
    @flags.command(
        name="give",
        aliases=["g"],
        help=(
            "Dá um Pokémon para um usuário.\n\n"
            "**OBRIGATÓRIO**\n"
            "  user                    Usuário que vai receber (@mention)\n"
            "  species                 ID da espécie do Pokémon (1-386)\n\n"
            "**OPCIONAL**\n"
            "  --level N               Nível do Pokémon (1-100, padrão: 5)\n"
            "  --shiny                 Pokémon será shiny\n"
            "  --gender <tipo>         Gênero: male | female | genderless\n"
            "  --nature <nome>         Nature específica (ex: adamant, modest)\n"
            "  --ability <nome>        Ability específica\n"
            "  --held_item <item>      Item que o Pokémon estará segurando\n"
            "  --nickname <texto>      Nickname do Pokémon\n"
            "  --on_party              Adiciona direto na party (padrão: box)\n"
            "  --no_rewards            Não dá recompensas de captura\n\n"
            "**IVs INDIVIDUAIS**\n"
            "  --hp N                  IV de HP (0-31, padrão: 31)\n"
            "  --atk N                 IV de Attack (0-31, padrão: 31)\n"
            "  --def N                 IV de Defense (0-31, padrão: 31)\n"
            "  --spatk N               IV de Special Attack (0-31, padrão: 31)\n"
            "  --spdef N               IV de Special Defense (0-31, padrão: 31)\n"
            "  --spd N                 IV de Speed (0-31, padrão: 31)\n"
            "  --random_ivs            IVs aleatórios (0-31 cada)\n"
            "  --perfect               Todos os IVs = 31 (ignora flags individuais)\n\n"
            "**EXEMPLOS**\n"
            "  .admin give @user 25 --level 50 --shiny\n"
            "  .admin give @user 6 --level 100 --perfect --nature adamant\n"
            "  .admin give @user 150 --shiny --on_party --held_item leftovers\n"
            "  .admin give @user 249 --level 70 --nickname \"Ho-Oh Dourado\" --random_ivs\n"
            "  .admin give @user 133 --gender female --nature modest --hp 0 --atk 0 --spd 31"
        )
    )
    @is_owner()
    async def admin_give(self, ctx: commands.Context, **flags):
        user = flags["user"]
        species_id = flags["species"]
        
        if not user:
            return await ctx.send("Mencione um usuário válido!")
        
        if not (1 <= species_id <= 386):
            return await ctx.send("Species ID deve estar entre 1 e 386!")
        
        user_id = str(user.id)
        
        try:
            toolkit.get_user(user_id)
        except ValueError:
            return await ctx.send(f"{user.mention} não tem uma conta!")
        
        level = max(1, min(100, flags["level"]))
        
        ivs = None
        if flags["perfect"]:
            ivs = {k: 31 for k in STAT_KEYS}
        elif not flags["random_ivs"]:
            ivs = {
                "hp": max(0, min(31, flags["hp"])),
                "attack": max(0, min(31, flags["atk"])),
                "defense": max(0, min(31, flags["def"])),
                "special-attack": max(0, min(31, flags["spatk"])),
                "special-defense": max(0, min(31, flags["spdef"])),
                "speed": max(0, min(31, flags["spd"]))
            }
        
        nature = None
        if flags["nature"]:
            nature_input = flags["nature"].lower()
            if nature_input in NATURES:
                nature = nature_input
            else:
                return await ctx.send(f"Nature inválida: `{flags['nature']}`\nNatures válidas: {', '.join(list(NATURES.keys())[:10])}...")
        
        nickname = None
        if flags["nickname"]:
            nickname = " ".join(flags["nickname"]).strip()
            if len(nickname) > 20:
                return await ctx.send("Nickname deve ter no máximo 20 caracteres!")
        
        gender = flags["gender"]
        ability = flags["ability"]
        held_item = flags["held_item"]
        on_party = flags["on_party"]
        give_rewards = not flags["no_rewards"]
        
        try:
            pokemon = await pm.create_pokemon(
                owner_id=user_id,
                species_id=species_id,
                level=level,
                on_party=on_party,
                give_rewards=give_rewards,
                shiny=flags["shiny"],
                forced_gender=gender,
                ivs=ivs,
                nature=nature,
                ability=ability,
                held_item=held_item,
                nickname=nickname
            )
            
            display = format_pokemon_display(pokemon, bold_name=True, show_level=True, show_gender=True)
            
            details = []
            if flags["shiny"]:
                details.append("✨ Shiny")
            if flags["perfect"]:
                details.append("💯 IVs Perfeitos")
            elif ivs:
                iv_total = sum(ivs.values())
                iv_percent = round((iv_total / 186) * 100, 2)
                details.append(f"📊 IVs: {iv_percent}%")
            if nature:
                details.append(f"🎭 {nature.title()}")
            if held_item:
                details.append(f"🎒 {held_item.replace('-', ' ').title()}")
            if nickname:
                details.append(f"📝 \"{nickname}\"")
            
            location = "party" if on_party else "box"
            
            message = f"✅ {display} foi dado para {user.mention}!\n"
            message += f"**Local:** {location}\n"
            
            if details:
                message += f"**Detalhes:** {' • '.join(details)}\n"
            
            if give_rewards:
                message += f"\n-# Recompensas de captura foram dadas."
            
            await ctx.send(message)
            
        except Exception as e:
            await ctx.send(f"Erro ao criar Pokémon: {str(e)}")

    @flags.add_flag("user", type=discord.Member)
    @flags.add_flag("item", type=str)
    @flags.add_flag("--quantity", "--q", type=int, default=1)
    @flags.command(
        name="giveitem",
        aliases=["gi"],
        help=(
            "Dá um item para um usuário.\n\n"
            "**EXEMPLOS**\n"
            "  .admin giveitem @user rare-candy --quantity 99\n"
            "  .admin giveitem @user master-ball -q 10\n"
            "  .admin giveitem @user leftovers"
        )
    )
    @is_owner()
    async def admin_giveitem(self, ctx: commands.Context, **flags):
        user = flags["user"]
        item_id = flags["item"]
        quantity = max(1, flags["quantity"])
        
        if not user:
            return await ctx.send("Mencione um usuário válido!")
        
        user_id = str(user.id)
        
        try:
            toolkit.get_user(user_id)
        except ValueError:
            return await ctx.send(f"{user.mention} não tem uma conta!")
        
        try:
            result = await pm.give_item(user_id, item_id, quantity)
            
            await ctx.send(
                f"{user.mention} recebeu **{result['name']}** x{quantity}!\n"
                f"**Total:** {result['quantity']}"
            )
        except Exception as e:
            await ctx.send(f"Erro: {str(e)}")

    @flags.add_flag("user", type=discord.Member)
    @flags.add_flag("amount", type=int)
    @flags.command(
        name="givemoney",
        aliases=["gm", "addmoney"],
        help=(
            "Dá dinheiro para um usuário.\n\n"
            "**EXEMPLOS**\n"
            "  .admin givemoney @user 100000\n"
            "  .admin gm @user 50000"
        )
    )
    @is_owner()
    async def admin_givemoney(self, ctx: commands.Context, **flags):
        user = flags["user"]
        amount = flags["amount"]
        
        if not user:
            return await ctx.send("Mencione um usuário válido!")
        
        if amount <= 0:
            return await ctx.send("Quantidade deve ser positiva!")
        
        user_id = str(user.id)
        
        try:
            toolkit.get_user(user_id)
        except ValueError:
            return await ctx.send(f"{user.mention} não tem uma conta!")
        
        new_balance = toolkit.adjust_money(user_id, amount)
        
        await ctx.send(
            f"✅ {user.mention} recebeu ₽{amount:,}!\n"
            f"**Novo saldo:** ₽{new_balance:,}"
        )

    @flags.add_flag("user", type=discord.Member)
    @flags.add_flag("amount", type=int)
    @flags.command(
        name="takemoney",
        aliases=["tm", "removemoney"],
        help=(
            "Remove dinheiro de um usuário.\n\n"
            "**EXEMPLOS**\n"
            "  .admin takemoney @user 50000\n"
            "  .admin tm @user 10000"
        )
    )
    @is_owner()
    async def admin_takemoney(self, ctx: commands.Context, **flags):
        user = flags["user"]
        amount = flags["amount"]
        
        if not user:
            return await ctx.send("Mencione um usuário válido!")
        
        if amount <= 0:
            return await ctx.send("Quantidade deve ser positiva!")
        
        user_id = str(user.id)
        
        try:
            toolkit.get_user(user_id)
        except ValueError:
            return await ctx.send(f"{user.mention} não tem uma conta!")
        
        new_balance = toolkit.adjust_money(user_id, -amount)
        
        await ctx.send(
            f"₽{amount:,} foram removidos de {user.mention}!\n"
            f"**Novo saldo:** ₽{new_balance:,}"
        )

    @flags.add_flag("user", type=discord.Member)
    @flags.add_flag("pokemon_id", type=int)
    @flags.add_flag("--level", type=int, default=None)
    @flags.add_flag("--shiny", action="store_true")
    @flags.add_flag("--unshiny", action="store_true")
    @flags.add_flag("--nature", type=str, default=None)
    @flags.add_flag("--ability", type=str, default=None)
    @flags.add_flag("--gender", type=str, default=None)
    @flags.add_flag("--held_item", type=str, default=None)
    @flags.add_flag("--nickname", nargs="+", default=None)
    @flags.add_flag("--favorite", action="store_true")
    @flags.add_flag("--unfavorite", action="store_true")
    @flags.add_flag("--hp", type=int, default=None)
    @flags.add_flag("--atk", type=int, default=None)
    @flags.add_flag("--def", type=int, default=None)
    @flags.add_flag("--spatk", type=int, default=None)
    @flags.add_flag("--spdef", type=int, default=None)
    @flags.add_flag("--spd", type=int, default=None)
    @flags.add_flag("--perfect", action="store_true")
    @flags.add_flag("--happiness", type=int, default=None)
    @flags.command(
        name="modify",
        aliases=["m", "mod", "edit"],
        help=(
            "Modifica um Pokémon de um usuário.\n\n"
            "**EXEMPLOS**\n"
            "  .admin modify @user 1 --level 100\n"
            "  .admin modify @user 5 --shiny --perfect\n"
            "  .admin modify @user 10 --nature adamant --ability intimidate\n"
            "  .admin modify @user 3 --nickname \"Meu Campeão\" --favorite\n"
            "  .admin modify @user 7 --held_item leftovers --happiness 255"
        )
    )
    @is_owner()
    async def admin_modify(self, ctx: commands.Context, **flags):
        user = flags["user"]
        pokemon_id = flags["pokemon_id"]
        
        if not user:
            return await ctx.send("Mencione um usuário válido!")
        
        user_id = str(user.id)
        
        try:
            pokemon = toolkit.get_pokemon(user_id, pokemon_id)
        except ValueError:
            return await ctx.send(f"Pokémon #{pokemon_id} não encontrado!")
        
        changes = []
        
        if flags["level"] is not None:
            level = max(1, min(100, flags["level"]))
            toolkit.set_level(user_id, pokemon_id, level)
            changes.append(f"Level → {level}")
        
        if flags["shiny"]:
            toolkit.set_shiny(user_id, pokemon_id, True)
            changes.append("Agora é Shiny ✨")
        elif flags["unshiny"]:
            toolkit.set_shiny(user_id, pokemon_id, False)
            changes.append("Não é mais Shiny")
        
        if flags["nature"]:
            nature_input = flags["nature"].lower()
            if nature_input in NATURES:
                toolkit.set_nature(user_id, pokemon_id, nature_input)
                changes.append(f"Nature → {nature_input.title()}")
            else:
                return await ctx.send(f"Nature inválida: `{flags['nature']}`")
        
        if flags["ability"]:
            toolkit.set_ability(user_id, pokemon_id, flags["ability"])
            changes.append(f"Ability → {flags['ability'].title()}")
        
        if flags["gender"]:
            toolkit.set_gender(user_id, pokemon_id, flags["gender"])
            changes.append(f"Gender → {flags['gender'].title()}")
        
        if flags["held_item"]:
            toolkit.set_held_item(user_id, pokemon_id, flags["held_item"])
            changes.append(f"Held Item → {flags['held_item'].replace('-', ' ').title()}")
        
        if flags["nickname"]:
            nickname = " ".join(flags["nickname"]).strip()
            if len(nickname) > 20:
                return await ctx.send("❌ Nickname deve ter no máximo 20 caracteres!")
            toolkit.set_nickname(user_id, pokemon_id, nickname)
            changes.append(f"Nickname → \"{nickname}\"")
        
        if flags["favorite"]:
            toolkit.set_favorite(user_id, pokemon_id, True)
            changes.append("Favoritado ❤️")
        elif flags["unfavorite"]:
            toolkit.set_favorite(user_id, pokemon_id, False)
            changes.append("Desfavoritado")
        
        if flags["perfect"]:
            ivs = {k: 31 for k in STAT_KEYS}
            toolkit.set_ivs(user_id, pokemon_id, ivs)
            changes.append("IVs → 100% Perfeito")
        else:
            current_ivs = pokemon["ivs"].copy()
            iv_changed = False
            
            if flags["hp"] is not None:
                current_ivs["hp"] = max(0, min(31, flags["hp"]))
                iv_changed = True
            if flags["atk"] is not None:
                current_ivs["attack"] = max(0, min(31, flags["atk"]))
                iv_changed = True
            if flags["def"] is not None:
                current_ivs["defense"] = max(0, min(31, flags["def"]))
                iv_changed = True
            if flags["spatk"] is not None:
                current_ivs["special-attack"] = max(0, min(31, flags["spatk"]))
                iv_changed = True
            if flags["spdef"] is not None:
                current_ivs["special-defense"] = max(0, min(31, flags["spdef"]))
                iv_changed = True
            if flags["spd"] is not None:
                current_ivs["speed"] = max(0, min(31, flags["spd"]))
                iv_changed = True
            
            if iv_changed:
                toolkit.set_ivs(user_id, pokemon_id, current_ivs)
                iv_total = sum(current_ivs.values())
                iv_percent = round((iv_total / 186) * 100, 2)
                changes.append(f"IVs → {iv_percent}%")
        
        if flags["happiness"] is not None:
            happiness = max(0, min(255, flags["happiness"]))
            toolkit.set_happiness(user_id, pokemon_id, happiness)
            changes.append(f"Happiness → {happiness}")
        
        if not changes:
            return await ctx.send("Nenhuma modificação foi especificada!")
        
        pokemon = toolkit.get_pokemon(user_id, pokemon_id)
        display = format_pokemon_display(pokemon, bold_name=True, show_level=True)
        
        await ctx.send(
            f"{display} de {user.mention} foi modificado!\n\n"
            f"**Mudanças:**\n" + "\n".join(f"• {change}" for change in changes)
        )

    @flags.add_flag("user", type=discord.Member)
    @flags.add_flag("pokemon_id", type=int)
    @flags.command(
        name="delete",
        aliases=["del", "remove"],
        help=(
            "Deleta um Pokémon de um usuário.\n\n"
            "**EXEMPLOS**\n"
            "  .admin delete @user 5\n"
            "  .admin del @user 10"
        )
    )
    @is_owner()
    async def admin_delete(self, ctx: commands.Context, **flags):
        user = flags["user"]
        pokemon_id = flags["pokemon_id"]
        
        if not user:
            return await ctx.send("Mencione um usuário válido!")
        
        user_id = str(user.id)
        
        try:
            pokemon = toolkit.get_pokemon(user_id, pokemon_id)
            display = format_pokemon_display(pokemon, bold_name=True, show_level=True)
            
            toolkit.release_pokemon(user_id, pokemon_id)
            
            await ctx.send(f"✅ {display} foi deletado de {user.mention}!")
        except ValueError:
            await ctx.send(f"Pokémon #{pokemon_id} não encontrado!")

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
