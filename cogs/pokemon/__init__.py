import discord
import io
import asyncio
from typing import List, Optional, Dict, Final
from discord.ext import commands
from helpers.flags import flags
from cogs.pokemon.filters import apply_filters, apply_sort_limit
from cogs.pokemon.analysis import analyze_pokemons
from cogs.pokemon.views import PokemonListLayout, PokemonInfoLayout
from sdk.toolkit import Toolkit
from utilities.formatting import format_pokemon_display
from utilities.preloaded import preloaded_info_backgrounds
from utilities.canvas import compose_pokemon_async
import helpers.checks as checks

class Pokemon(commands.Cog, name="Pokémon"):
    STATIC_ICONS: Final[Dict[str, str]] = {
        "special_move": "resources/textures/icons/special_move.png",
        "future_moves": "resources/textures/icons/future_moves.png",
        "iv": "resources/textures/icons/iv.png",
        "ev": "resources/textures/icons/ev.png",
        "stats": "resources/textures/icons/stats.png"
    }
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tk = Toolkit()
        self._icon_cache: Dict[str, bytes] = {}
        self._preload_icons()

    def _preload_icons(self) -> None:
        for icon_name, path in self.STATIC_ICONS.items():
            try:
                with open(path, 'rb') as f:
                    self._icon_cache[icon_name] = f.read()
            except FileNotFoundError:
                pass

    def _get_static_files(self) -> List[discord.File]:
        return [
            discord.File(io.BytesIO(data), f"{name}.png")
            for name, data in self._icon_cache.items()
        ]

    @flags.add_flag("--page", nargs="?", type=int, default=0)
    @flags.add_flag("--user", type=discord.Member, default=None)
    @flags.add_flag("--name", "--n", nargs="+", action="append")
    @flags.add_flag("--nickname", "--nck", nargs="*", action="append")
    @flags.add_flag("--type", "--t", type=str,  nargs="+", action="append")
    @flags.add_flag("--region", "--r", type=str, nargs="+", action="append")
    @flags.add_flag("--gender", type=str)
    @flags.add_flag("--shiny", action="store_true")
    @flags.add_flag("--legendary", action="store_true")
    @flags.add_flag("--mythical", action="store_true")
    @flags.add_flag("--party", action="store_true")
    @flags.add_flag("--box", action="store_true")
    @flags.add_flag("--favorite", action="store_true")
    @flags.add_flag("--held_item", nargs="+", action="append")
    @flags.add_flag("--nature", nargs="+", action="append")
    @flags.add_flag("--ability", nargs="+", action="append")
    @flags.add_flag("--species", nargs="+", action="append", type=int)
    @flags.add_flag("--reverse", action="store_true")
    @flags.add_flag("--random", action="store_true")
    @flags.add_flag("--sort", type=str)
    @flags.add_flag("--min_iv", type=int)
    @flags.add_flag("--max_iv", type=int)
    @flags.add_flag("--min_level", type=int)
    @flags.add_flag("--max_level", type=int)
    @flags.add_flag("--level", nargs="+", action="append")
    @flags.add_flag("--min_happiness", type=int)
    @flags.add_flag("--max_happiness", type=int)
    @flags.add_flag("--happiness", nargs="+", action="append")
    @flags.add_flag("--hpiv", nargs="+", action="append")
    @flags.add_flag("--atkiv", nargs="+", action="append")
    @flags.add_flag("--defiv", nargs="+", action="append")
    @flags.add_flag("--spatkiv", nargs="+", action="append")
    @flags.add_flag("--spdefiv", nargs="+", action="append")
    @flags.add_flag("--spdiv", nargs="+", action="append")
    @flags.add_flag("--iv", nargs="+", action="append")
    @flags.add_flag("--min_ev", type=int)
    @flags.add_flag("--max_ev", type=int)
    @flags.add_flag("--hpev", nargs="+", action="append")
    @flags.add_flag("--atkev", nargs="+", action="append")
    @flags.add_flag("--defev", nargs="+", action="append")
    @flags.add_flag("--spatkev", nargs="+", action="append")
    @flags.add_flag("--spdefev", nargs="+", action="append")
    @flags.add_flag("--spedev", nargs="+", action="append")
    @flags.add_flag("--move", nargs="+", action="append")
    @flags.add_flag("--no_nickname", action="store_true")
    @flags.add_flag("--has_nickname", action="store_true")
    @flags.add_flag("--no_held_item", action="store_true")
    @flags.add_flag("--has_held_item", action="store_true")
    @flags.add_flag("--fainted", action="store_true")
    @flags.add_flag("--healthy", action="store_true")
    @flags.add_flag("--growth_type", nargs="+", action="append")
    @flags.add_flag("--min_exp", type=int)
    @flags.add_flag("--max_exp", type=int)
    @flags.add_flag("--exp", nargs="+", action="append")
    @flags.add_flag("--exp_percent", nargs="+", action="append")
    @flags.add_flag("--background", nargs="+", action="append")
    @flags.add_flag("--min_move_count", type=int)
    @flags.add_flag("--max_move_count", type=int)
    @flags.add_flag("--move_count", nargs="+", action="append")
    @flags.add_flag("--triple_31", action="store_true")
    @flags.add_flag("--quad_31", action="store_true")
    @flags.add_flag("--penta_31", action="store_true")
    @flags.add_flag("--hexa_31", action="store_true")
    @flags.add_flag("--triple_0", action="store_true")
    @flags.add_flag("--quad_0", action="store_true")
    @flags.add_flag("--duplicates", action="store_true")
    @flags.add_flag("--unique", action="store_true")
    @flags.add_flag("--page_size", type=int, default=20)
    @flags.add_flag("--limit", type=int)
    @commands.cooldown(3, 5, commands.BucketType.user)
    @flags.command(
        name="pokemon",
        aliases=["p", "pk", "pkm", "pkmn"],
        help=(
            "Lista os Pokémon do usuário com suporte a filtros, ordenação e paginação.\n\n"
            "**BÁSICO**\n"
            "  --party                 Lista apenas Pokémon que estão na party\n"
            "  --box                   Lista apenas Pokémon que estão na box\n"
            "  --shiny                 Filtra apenas Pokémon shiny\n"
            "  --favorite              Filtra apenas Pokémon marcados como favoritos\n"
            "  --gender <valor>        Filtra por gênero: male | female | genderless\n"
            "  --species <ID...>       Filtra por species IDs específicos (um ou mais)\n"
            "  --name <texto...>       Filtra pelo nome da espécie contendo o texto\n"
            "  --nickname <texto...>   Filtra pelo nickname contendo o texto\n"
            "  --nature <nome...>      Filtra por nature(s) específicas\n"
            "  --ability <nome...>     Filtra por ability(ies) específicas\n"
            "  --held_item <nome...>   Filtra por item segurado\n"
            "  --type <nome...>        Filtra por tipos do Pokémon (aceita múltiplos)\n"
            "  --region <nome...>      Filtra por região de origem da espécie\n"
            "  --move <nome...>        Filtra por movimento específico\n\n"
            "**ESPECIAL**\n"
            "  --legendary             Filtra apenas espécies lendárias\n"
            "  --mythical              Filtra apenas espécies míticas\n"
            "  --no_nickname           Pokémon sem nickname\n"
            "  --has_nickname          Pokémon com nickname\n"
            "  --no_held_item          Pokémon sem item segurado\n"
            "  --has_held_item         Pokémon com item segurado\n"
            "  --fainted               Pokémon desmaiados (HP = 0)\n"
            "  --healthy               Pokémon com HP cheio\n"
            "  --duplicates            Apenas espécies duplicadas\n"
            "  --unique                Apenas espécies únicas\n\n"
            "**FILTRAGEM NUMÉRICA**\n"
            "  --min_iv N              Seleciona apenas Pokémon com IV total >= N (valor em %)\n"
            "  --max_iv N              Seleciona apenas Pokémon com IV total <= N (valor em %)\n"
            "  --min_level N           Seleciona apenas Pokémon com level >= N\n"
            "  --max_level N           Seleciona apenas Pokémon com level <= N\n"
            "  --level <N...>          Filtra por levels exatos (aceita vários)\n"
            "  --min_happiness N       Seleciona apenas Pokémon com amizade >= N (0-255)\n"
            "  --max_happiness N       Seleciona apenas Pokémon com amizade <= N (0-255)\n"
            "  --happiness <N...>      Filtra por valores exatos de amizade\n"
            "  --min_ev N              Seleciona apenas Pokémon com EV total >= N\n"
            "  --max_ev N              Seleciona apenas Pokémon com EV total <= N\n\n"
            "**FILTRAGEM POR IV INDIVIDUAL**\n"
            "  --hpiv <N...>           IV exato de HP\n"
            "  --atkiv <N...>          IV exato de Attack\n"
            "  --defiv <N...>          IV exato de Defense\n"
            "  --spatkiv <N...>        IV exato de Special Attack\n"
            "  --spdefiv <N...>        IV exato de Special Defense\n"
            "  --spdiv <N...>          IV exato de Speed\n"
            "  --iv <N...>             IV total em % exato (ex.: 100 = perfeitos)\n\n"
            "**FILTRAGEM POR EV INDIVIDUAL**\n"
            "  --hpev <N...>           EV exato de HP\n"
            "  --atkev <N...>          EV exato de Attack\n"
            "  --defev <N...>          EV exato de Defense\n"
            "  --spatkev <N...>        EV exato de Special Attack\n"
            "  --spdefev <N...>        EV exato de Special Defense\n"
            "  --spedev <N...>         EV exato de Speed\n\n"
            "**FILTRAGEM AVANÇADA DE IVs**\n"
            "  --triple_31             Pelo menos 3 IVs perfeitos (31)\n"
            "  --quad_31               Pelo menos 4 IVs perfeitos (31)\n"
            "  --penta_31              Pelo menos 5 IVs perfeitos (31)\n"
            "  --hexa_31               6 IVs perfeitos (31)\n"
            "  --triple_0              Pelo menos 3 IVs em 0\n"
            "  --quad_0                Pelo menos 4 IVs em 0\n\n"
            "**EXPERIÊNCIA E CRESCIMENTO**\n"
            "  --growth_type <tipo>    Tipo de crescimento: slow | medium | fast | medium-slow | slow-then-very-fast | fast-then-very-slow\n"
            "  --min_exp N             Experiência mínima\n"
            "  --max_exp N             Experiência máxima\n"
            "  --exp <N...>            Experiência exata\n"
            "  --exp_percent <N...>    Percentual de progresso no nível (0-100)\n\n"
            "**MOVIMENTOS E VISUAL**\n"
            "  --min_move_count N      Número mínimo de movimentos\n"
            "  --max_move_count N      Número máximo de movimentos\n"
            "  --move_count <N...>     Número exato de movimentos\n"
            "  --background <tipo>     Background específico\n\n"
            "**ORDENAÇÃO**\n"
            "  --sort <campo>          Define critério de ordenação: iv | level | id | name | species | ev | hp | exp | growth | happiness\n"
            "  --reverse               Inverte a ordem de ordenação\n"
            "  --random                Embaralha a ordem (ignora sort)\n\n"
            "**PAGINAÇÃO E LIMITES**\n"
            "  --page N                Define a página inicial (1-based, padrão: 1)\n"
            "  --page_size N           Define o número de Pokémon por página (padrão: 20)\n"
            "  --limit N               Define um limite máximo de Pokémon retornados\n\n"
            "**EXEMPLOS**\n"
            "  .pokemon --party\n"
            "  .pokemon --box --shiny\n"
            "  .pokemon --species 25 133 --min_iv 85 --sort level --reverse\n"
            "  .pokemon --type fire flying --region kalos\n"
            "  .pokemon --hexa_31 --shiny\n"
            "  .pokemon --min_happiness 200 --sort happiness\n"
            "  .pokemon --happiness 255 --favorite\n"
            "  .pokemon --growth_type slow medium-slow\n"
            "  .pokemon --exp_percent 90 95 100\n"
            "  .pokemon --duplicates --sort species\n"
            "  .pokemon --triple_31 --min_level 50"
        )
    )
    @checks.require_account()
    async def pokemon_command(self, ctx: commands.Context, **flags):
        user_id = str(ctx.author.id)

        if flags.get("party") and not flags.get("box"):
            pokemons = self.tk.pokemon.get_party(user_id)
        elif flags.get("box") and not flags.get("party"):
            pokemons = self.tk.pokemon.get_box(user_id)
        else:
            pokemons = self.tk.pokemon.get_all_by_owner(user_id)

        pokemons = apply_filters(pokemons, flags)
        pokemons = apply_sort_limit(pokemons, flags)

        if not pokemons:
            await ctx.message.reply("Nenhum Pokémon encontrado.")
            return

        page_size: int = flags.get("page_size") if flags.get("page_size") and flags.get("page_size", 20) > 0 else 20

        view: discord.ui.LayoutView = PokemonListLayout(pokemons, flags.get("page", 0), page_size)
        await ctx.message.reply(view=view)

    @commands.command(name="favorite", aliases=["fav"])
    @checks.require_account()
    async def favorite_pokemon(self, ctx, pokemon_id: int):
        user_id = str(ctx.author.id)
        
        try:
            pokemon = self.tk.pokemon.get(user_id, pokemon_id)
            if pokemon.get("is_favorite"):
                return await ctx.message.reply(f"{format_pokemon_display(pokemon, bold_name=True)} já está nos favoritos!")
            
            self.tk.pokemon.toggle_favorite(user_id, pokemon_id)
            await ctx.message.reply(f"❤️ {format_pokemon_display(pokemon, bold_name=True)} foi adicionado aos favoritos!")
        except ValueError:
            return

    @commands.command(name="unfavourite", aliases=["unfav", "unfavorite"])
    @checks.require_account()
    async def unfavourite_pokemon(self, ctx, pokemon_id: int):
        user_id = str(ctx.author.id)

        try:
            pokemon = self.tk.pokemon.get(user_id, pokemon_id)
            if not pokemon.get("is_favorite"):
                return await ctx.message.reply(f"{format_pokemon_display(pokemon, bold_name=True)} já não está nos favoritos!")
            
            self.tk.pokemon.toggle_favorite(user_id, pokemon_id)
            await ctx.message.reply(f"💔 {format_pokemon_display(pokemon, bold_name=True)} foi removido dos favoritos!")
        except ValueError:
            return

    @commands.command(name="nickname", aliases=["nick"])
    @checks.require_account()
    async def set_nickname(self, ctx, pokemon_id: int, *, nickname: Optional[str] = None):
        user_id = str(ctx.author.id)
        if nickname:
            nickname = nickname.strip()
        
        if nickname and len(nickname) > 20:
            return await ctx.message.reply("O nickname deve ter no máximo 20 caracteres!")
        
        try:
            self.tk.pokemon.set_nickname(user_id, pokemon_id, nickname)
            pokemon = self.tk.pokemon.get(user_id, pokemon_id)
            
            if nickname:
                await ctx.message.reply(f"Nickname definido como **{nickname}** para o {format_pokemon_display(pokemon, bold_name=True, show_nick=False)}!")
            else:
                await ctx.message.reply(f"Nickname do {format_pokemon_display(pokemon, bold_name=True)} removido!")
        except ValueError:
            return

    @commands.cooldown(3, 5, commands.BucketType.user)
    @commands.command(name="info", aliases=["i", "inf"])
    @checks.require_account()
    async def info_command(self, ctx: commands.Context, pokemon_id: Optional[int] = None) -> None:
        user_id = str(ctx.author.id)

        if pokemon_id is None:
            party = self.tk.pokemon.get_party(user_id)
            if not party:
                all_pokemons = self.tk.pokemon.get_all_by_owner(user_id)
                if not all_pokemons:
                    await ctx.message.reply("Voce nao possui nenhum Pokemon.")
                    return
                current_pokemon = all_pokemons[0]
                pokemon_index = 0
                total_count = len(all_pokemons)
            else:
                all_pokemons = self.tk.pokemon.get_all_by_owner(user_id)
                current_pokemon = party[0]
                pokemon_index = next((i for i, p in enumerate(all_pokemons) if p['id'] == current_pokemon['id']), 0)
                total_count = len(all_pokemons)
        else:
            try:
                current_pokemon = self.tk.pokemon.get(user_id, pokemon_id)
                all_pokemons = self.tk.pokemon.get_all_by_owner(user_id)
                pokemon_index = next((i for i, p in enumerate(all_pokemons) if p['id'] == pokemon_id), 0)
                total_count = len(all_pokemons)
            except ValueError:
                await ctx.message.reply("Voce nao possui um Pokemon com esse ID.")
                return

        sprite_url = self.tk.api.get_pokemon_sprite(current_pokemon)[0]
        background = preloaded_info_backgrounds[current_pokemon["background"]]
        
        composed_image, static_files = await asyncio.gather(
            compose_pokemon_async(sprite_url, background),
            asyncio.to_thread(self._get_static_files)
        )
        
        files = static_files + [discord.File(composed_image, "pokemon.png")]
        view = PokemonInfoLayout(current_pokemon, pokemon_index, total_count, self.tk)
        
        await ctx.message.reply(view=view, files=files)


async def setup(bot: commands.Bot):
    await bot.add_cog(Pokemon(bot))
