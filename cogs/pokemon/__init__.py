import discord
from typing import Optional
from discord.ext import commands
from helpers.flags import flags
from helpers.paginator import Paginator
from helpers.checks import requires_account, not_in_battle
from utils.formatting import format_pokemon_display
from __main__ import toolkit
from .views import InfoView, ConfirmationView
from .embeds import generate_pokemon_embed, generate_info_embed
from .filters import apply_filters, apply_sort_limit
from .analysis import analyze_pokemons

class Pokemon(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot

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
			"  --user                  Lista as infomrações do usuário\n"
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
			"  .pokemon --user @misty\n"
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
	@requires_account()
	async def pokemon_command(self, ctx: commands.Context, **flags):
		user = flags.get("user") or ctx.author
		user_id = str(user.id)

		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		page_size = flags.get("page_size") if flags.get("page_size") and flags.get("page_size", 20) > 0 else 20

		display_user = user if user.id != ctx.author.id else None
		view = Paginator(
			items=pokemons,
			user_id=ctx.author.id,
			embed_generator=lambda items, start, end, total, page: generate_pokemon_embed(items, start, end, total, page, display_user),
			page_size=page_size,
			current_page=flags.get("page", 0)
		)
		embed = await view.get_embed()
		await ctx.send(embed=embed, view=view)

	@commands.command(name="favorite", aliases=["fav"])
	@requires_account()
	async def favorite_pokemon(self, ctx, pokemon_id: int):
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return
		
		try:
			pokemon = toolkit.get_pokemon(user_id, pokemon_id)
			if pokemon.get("is_favorite"):
				return await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True)} já está nos favoritos!")
			
			toolkit.toggle_favorite(user_id, pokemon_id)
			await ctx.send(f"❤️ {format_pokemon_display(pokemon, bold_name=True)} foi adicionado aos favoritos!")
		except ValueError:
			return

	@commands.command(name="unfavourite", aliases=["unfav", "unfavorite"])
	@requires_account()
	async def unfavourite_pokemon(self, ctx, pokemon_id: int):
		user_id = str(ctx.author.id)
		user = toolkit.get_user(user_id)
		if not user:
			return
		
		try:
			pokemon = toolkit.get_pokemon(user_id, pokemon_id)
			if not pokemon.get("is_favorite"):
				return await ctx.send(f"{format_pokemon_display(pokemon, bold_name=True)} já não está nos favoritos!")
			
			toolkit.toggle_favorite(user_id, pokemon_id)
			await ctx.send(f"💔 {format_pokemon_display(pokemon, bold_name=True)} foi removido dos favoritos!")
		except ValueError:
			return

	@commands.command(name="nickname", aliases=["nick"])
	@requires_account()
	async def set_nickname(self, ctx, pokemon_id: int, *, nickname: Optional[str] = None):
		user_id = str(ctx.author.id)
		if nickname:
			nickname = nickname.strip()
		user = toolkit.get_user(user_id)
		if not user:
			return
		
		if nickname and len(nickname) > 20:
			return await ctx.send("O nickname deve ter no máximo 20 caracteres!")
		
		try:
			toolkit.set_nickname(user_id, pokemon_id, nickname)
			pokemon = toolkit.get_pokemon(user_id, pokemon_id)
			
			if nickname:
				await ctx.send(f"Nickname definido como **{nickname}** para o {format_pokemon_display(pokemon, bold_name=True, show_nick=False)}!")
			else:
				await ctx.send(f"Nickname do {format_pokemon_display(pokemon, bold_name=True)} removido!")
		except ValueError:
			return

	@flags.add_flag("--name", "--n", nargs="+", action="append")
	@flags.add_flag("--nickname", "--nck", nargs="*", action="append")
	@flags.add_flag("--type", "--t", type=str, nargs="+", action="append")
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
	@flags.add_flag("--move", nargs="+", action="append")
	@flags.add_flag("--no_nickname", action="store_true")
	@flags.add_flag("--has_nickname", action="store_true")
	@flags.add_flag("--no_held_item", action="store_true")
	@flags.add_flag("--has_held_item", action="store_true")
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
	@flags.add_flag("--limit", type=int)
	@flags.command(
		name="favoriteall",
		aliases=["favall"],
		help=(
			"Marca todos os Pokémon que correspondem aos filtros como favoritos.\n\n"
			"Aceita as mesmas flags de filtro do comando .pokemon\n\n"
			"**EXEMPLOS**\n"
			"  .favoriteall --shiny\n"
			"  .favoriteall --species 25 --min_iv 90\n"
			"  .favoriteall --legendary --box"
		)
	)
	@requires_account()
	async def favoriteall_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)
		
		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		pokemons_to_fav = [p for p in pokemons if not p.get("is_favorite")]
		
		if not pokemons_to_fav:
			return await ctx.send("Todos os Pokémon encontrados já estão favoritados!")

		stats = analyze_pokemons(pokemons_to_fav)
		
		message_parts = [f"Você tem certeza que quer **favoritar {len(pokemons_to_fav)}** pokémon?"]
		
		details = []
		if stats["event"] > 0:
			details.append(f"• **{stats['event']}** Pokémon de Eventos")
		if stats["rare"] > 0:
			details.append(f"• **{stats['rare']}** Pokémon Raros (Lendários e Míticos)")
		if stats["shiny"] > 0:
			details.append(f"• **{stats['shiny']}** Pokémon Shiny")
		if stats["iv_100"] > 0:
			details.append(f"• **{stats['iv_100']}** Pokémon com **IV = 100%**")
		if stats["iv_90_100"] > 0:
			details.append(f"• **{stats['iv_90_100']}** Pokémon com **IV ≥ 90%, < 100%**")
		if stats["iv_80_90"] > 0:
			details.append(f"• **{stats['iv_80_90']}** Pokémon com **IV ≥ 80%, < 90%**")
		
		if details:
			message_parts.append("\n**Incluindo:**")
			message_parts.extend(details)
		
		message_parts.append("\n-# *Você tem 60 segundos para confirmar.*")
		
		view = ConfirmationView(ctx.author.id, timeout=60)
		message = await ctx.send("\n".join(message_parts), view=view)
		
		await view.wait()
		
		if view.value is None or view.value is False:
			for item in view.children:
				item.disabled = True
			await message.edit(content="Operação cancelada ou com tempo limite esgotado.", view=None)
			return

		pokemon_ids = [p["id"] for p in pokemons_to_fav]
		updated = toolkit.bulk_update_pokemon(user_id, pokemon_ids, {"is_favorite": True})
		count = len(updated)

		if count == 0:
			result_text = "Não foi possível favoritar nenhum Pokémon!"
		else:
			result_text = f"❤️ **{count}** Pokémon foram favoritados!"
		
		for item in view.children:
			item.disabled = True
		
		await message.edit(content=result_text, view=None)

	@flags.add_flag("--name", "--n", nargs="+", action="append")
	@flags.add_flag("--nickname", "--nck", nargs="*", action="append")
	@flags.add_flag("--type", "--t", type=str, nargs="+", action="append")
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
	@flags.add_flag("--move", nargs="+", action="append")
	@flags.add_flag("--no_nickname", action="store_true")
	@flags.add_flag("--has_nickname", action="store_true")
	@flags.add_flag("--no_held_item", action="store_true")
	@flags.add_flag("--has_held_item", action="store_true")
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
	@flags.add_flag("--limit", type=int)
	@flags.command(
		name="unfavouriteall",
		aliases=["unfavall", "unfavoriteall"],
		help=(
			"Remove todos os Pokémon que correspondem aos filtros dos favoritos.\n\n"
			"Aceita as mesmas flags de filtro do comando .pokemon\n\n"
			"**EXEMPLOS**\n"
			"  .unfavouriteall --favorite\n"
			"  .unfavouriteall --species 25 --max_iv 50\n"
			"  .unfavouriteall --box --min_level 1 --max_level 10"
		)
	)
	@requires_account()
	async def unfavouriteall_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)
		
		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		pokemons_to_unfav = [p for p in pokemons if p.get("is_favorite")]
		
		if not pokemons_to_unfav:
			return await ctx.send("Nenhum dos Pokémon encontrados está favoritado!")

		stats = analyze_pokemons(pokemons_to_unfav)
		
		message_parts = [f"Você tem certeza que quer **desfavoritar {len(pokemons_to_unfav)}** pokémon?"]
		
		details = []
		if stats["event"] > 0:
			details.append(f"• **{stats['event']}** Pokémon de Eventos")
		if stats["rare"] > 0:
			details.append(f"• **{stats['rare']}** Pokémon Raros (Lendários e Míticos)")
		if stats["shiny"] > 0:
			details.append(f"• **{stats['shiny']}** Pokémon Shiny")
		if stats["iv_100"] > 0:
			details.append(f"• **{stats['iv_100']}** Pokémon com **IV = 100%**")
		if stats["iv_90_100"] > 0:
			details.append(f"• **{stats['iv_90_100']}** Pokémon com **IV ≥ 90%, < 100%**")
		if stats["iv_80_90"] > 0:
			details.append(f"• **{stats['iv_80_90']}** Pokémon com **IV ≥ 80%, < 90%**")
		
		if details:
			message_parts.append("\n**Incluindo:**")
			message_parts.extend(details)
		
		message_parts.append("\n-# *Você tem 60 segundos para confirmar.*")
		
		view = ConfirmationView(ctx.author.id, timeout=60)
		message = await ctx.send("\n".join(message_parts), view=view)
		
		await view.wait()
		
		if view.value is None or view.value is False:
			for item in view.children:
				item.disabled = True
			await message.edit(content="Operação cancelada ou com tempo limite esgotado.", view=None)
			return

		pokemon_ids = [p["id"] for p in pokemons_to_unfav]
		updated = toolkit.bulk_update_pokemon(user_id, pokemon_ids, {"is_favorite": False})
		count = len(updated)

		if count == 0:
			result_text = "Não foi possível desfavoritar nenhum Pokémon!"
		else:
			result_text = f"💔 **{count}** Pokémon foram removidos dos favoritos!"
		
		for item in view.children:
			item.disabled = True
		
		await message.edit(content=result_text, view=None)

	@flags.add_flag("newname", nargs="+")
	@flags.add_flag("--name", "--n", nargs="+", action="append")
	@flags.add_flag("--nickname", "--nck", nargs="*", action="append")
	@flags.add_flag("--type", "--t", type=str, nargs="+", action="append")
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
	@flags.add_flag("--move", nargs="+", action="append")
	@flags.add_flag("--no_nickname", action="store_true")
	@flags.add_flag("--has_nickname", action="store_true")
	@flags.add_flag("--no_held_item", action="store_true")
	@flags.add_flag("--has_held_item", action="store_true")
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
	@flags.add_flag("--limit", type=int)
	@flags.command(
		name="nicknameall",
		aliases=["nickall"],
		help=(
			"Define o mesmo nickname para todos os Pokémon que correspondem aos filtros.\n\n"
			"Aceita as mesmas flags de filtro do comando .pokemon\n\n"
			"**EXEMPLOS**\n"
			"  .nicknameall Campeão --species 25\n"
			"  .nicknameall Shiny --shiny\n"
			"  .nicknameall clear --box (remove nickname de todos na box)"
		)
	)
	@requires_account()
	async def nicknameall_command(self, ctx: commands.Context, **flags):
		user_id = str(ctx.author.id)
		nickname = " ".join(flags.get("newname", []))
		
		if nickname.lower() == "clear":
			nickname = ""
		
		if nickname and len(nickname) > 20:
			return await ctx.send("O nickname deve ter no máximo 20 caracteres!")
		
		if flags.get("party") and not flags.get("box"):
			pokemons = toolkit.get_user_party(user_id)
		elif flags.get("box") and not flags.get("party"):
			pokemons = toolkit.get_user_box(user_id)
		else:
			pokemons = toolkit.list_pokemon_by_owner(user_id)
		
		pokemons = apply_filters(pokemons, flags)
		pokemons = apply_sort_limit(pokemons, flags)

		if not pokemons:
			return await ctx.send("Nenhum Pokémon encontrado com esses filtros.")

		stats = analyze_pokemons(pokemons)
		
		action_text = f"renomear **{len(pokemons)}** pokémon para `{nickname}`" if nickname else f"remover nicknames de **{len(pokemons)}** pokémon"
		
		message_parts = [f"Você tem certeza que quer {action_text}?"]
		
		details = []
		if stats["event"] > 0:
			details.append(f"• **{stats['event']}** Pokémon de Eventos")
		if stats["rare"] > 0:
			details.append(f"• **{stats['rare']}** Pokémon Raros (Lendários e Míticos)")
		if stats["shiny"] > 0:
			details.append(f"• **{stats['shiny']}** Pokémon Shiny")
		if stats["favorite"] > 0:
			details.append(f"• **{stats['favorite']}** Pokémon Favoritados")
		if stats["iv_100"] > 0:
			details.append(f"• **{stats['iv_100']}** Pokémon com **IV = 100%**")
		if stats["iv_90_100"] > 0:
			details.append(f"• **{stats['iv_90_100']}** Pokémon com **IV ≥ 90%, < 100%**")
		if stats["iv_80_90"] > 0:
			details.append(f"• **{stats['iv_80_90']}** Pokémon com **IV ≥ 80%, < 90%**")
		
		if details:
			message_parts.append("\n**Incluindo:**")
			message_parts.extend(details)
		
		message_parts.append("\n-# *Você tem 60 segundos para confirmar.*")
		
		view = ConfirmationView(ctx.author.id, timeout=60)
		message = await ctx.send("\n".join(message_parts), view=view)
		
		await view.wait()
		
		if view.value is None or view.value is False:
			for item in view.children:
				item.disabled = True
			await message.edit(content="Operação cancelada ou com tempo limite esgotado.", view=None)
			return
		
		pokemon_ids = [p["id"] for p in pokemons]
		updated = toolkit.bulk_update_pokemon(user_id, pokemon_ids, {"nickname": nickname if nickname else None})
		count = len(updated)

		if count == 0:
			result_text = "Não foi possível alterar o nickname de nenhum Pokémon!"
		else:
			action = f"alterado para **{nickname}**" if nickname else "removido"
			result_text = f"Nickname {action} para **{count}** Pokémon!"
		
		for item in view.children:
			item.disabled = True
		
		await message.edit(content=result_text, view=None)

	@commands.cooldown(3, 5, commands.BucketType.user)
	@commands.command(name="info", aliases=["i", "inf"])
	async def info_command(self, ctx: commands.Context, user: Optional[discord.Member] = None, pokemon_id: Optional[int] = None) -> None:
		user: discord.Member = user or ctx.author
		user_id = str(user.id)
		all_pokemons = toolkit.get_user_pokemon(user_id)
		
		if not all_pokemons:
			await ctx.send("Voce nao possui nenhum Pokemon!")
			return
			
		all_pokemon_ids = [p['id'] for p in all_pokemons]
		
		current_pokemon_id = pokemon_id
		if current_pokemon_id is None:
			party = toolkit.get_user_party(user_id)
			current_pokemon_id = party[0]['id'] if party else all_pokemon_ids[0]
		
		if current_pokemon_id not in all_pokemon_ids:
			await ctx.send("Voce nao possui um Pokemon com este ID.")
			return

		current_index = all_pokemon_ids.index(current_pokemon_id)
		
		result = await generate_info_embed(user_id, current_pokemon_id)

		if result:
			embed, files = result
			if str(ctx.author.id) != user_id:
				embed.title += f"\nde {user.display_name}"
				
			view = InfoView(self, ctx.author, user, all_pokemon_ids, current_index)
			await ctx.send(embed=embed, files=files, view=view)
		else:
			await ctx.send("Nao pude encontrar esse Pokemon!")


async def setup(bot: commands.Bot):
	await bot.add_cog(Pokemon(bot))
