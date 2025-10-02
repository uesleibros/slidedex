from discord.ext import commands
from utils.pokemon_emojis import get_app_emoji
from utils.formatting import format_pokemon_display
from pokemon_sdk.calculations import calculate_stats
from helpers.checks import requires_account
from typing import Optional
from __main__ import pm

async def _fmt_party(party):
	results = []
	for i, p in enumerate(party, start=1):
		stats = calculate_stats(p.get("base_stats"), p["ivs"], p["evs"], p["level"], p["nature"])
		cur_hp = p.get("current_hp", stats["hp"])
		results.append(
			f"{i}. {format_pokemon_display(p, show_fav=True)}\n"
			f"-# `id: {p['id']}` `Lv: {p['level']}` `HP: {cur_hp}/{stats['hp']}`"
		)
	return "\n\n".join(results) if results else "Seu time está vazio."


class Party(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.group(name="party", invoke_without_command=True)
	@requires_account()
	async def party_root(self, ctx: commands.Context):
		uid = str(ctx.author.id)
		party = pm.repo.tk.get_user_party(uid)
		text = await _fmt_party(party)
		await ctx.send(f"Time de {ctx.author.name}:\n{text}")

	@party_root.command(name="reorder", aliases=["order", "set"])
	@requires_account()
	async def party_reorder(self, ctx: commands.Context, *ids: int):
		uid = str(ctx.author.id)
		if not ids:
			return await ctx.send(
				"Uso: `.party reorder <id1> <id2> <id3> ...`\n"
				"Exemplo: `.party reorder 5 2 8 1 4 3`\n"
				"-# Use `.party` para ver os IDs dos seus Pokémon."
			)
		try:
			reordered = pm.repo.tk.reorder_party(uid, list(map(int, ids)))
		except Exception as e:
			return await ctx.send(f"Erro: {e}")
		text = await _fmt_party(reordered)
		await ctx.send("Nova ordem definida:\n" + text)

	@party_root.command(name="swap")
	@requires_account()
	async def party_swap(self, ctx: commands.Context, a: Optional[int] = None, b: Optional[int] = None):
		uid = str(ctx.author.id)
		if a is None or b is None:
			return await ctx.send(
				"Uso: `.party swap <posição1> <posição2>`\n"
				"Exemplo: `.party swap 1 3`\n"
				"-# Troca o Pokémon da posição 1 com o da posição 3."
			)

		party = pm.repo.tk.get_user_party(uid)
		if not party:
			return await ctx.send("Seu time está vazio.")
		if not (1 <= a <= len(party) and 1 <= b <= len(party)):
			return await ctx.send(f"Posições válidas: 1 a {len(party)}.")
		if a == b:
			return await ctx.send("Você não pode trocar um Pokémon com ele mesmo.")

		poke_a = party[a - 1]
		poke_b = party[b - 1]

		ids = [int(p["id"]) for p in party]
		ids[a-1], ids[b-1] = ids[b-1], ids[a-1]
		try:
			pm.repo.tk.reorder_party(uid, ids)
		except Exception as e:
			return await ctx.send(f"Erro: {e}")
		
		await ctx.send(f"{format_pokemon_display(poke_a, bold_name=True)} e {format_pokemon_display(poke_b, bold_name=True)} trocaram de lugar.")

	@party_root.command(name="add")
	@requires_account()
	async def party_add(self, ctx: commands.Context, pokemon_id: Optional[int] = None):
		uid = str(ctx.author.id)
		if not pokemon_id:
			return await ctx.send(
				"Uso: `.party add <pokemon_id>`\n"
				"Exemplo: `.party add 42`\n"
				"-# Use `.pokemon` para ver os IDs dos seus Pokémon."
			)
		try:
			p = pm.repo.tk.move_to_party(uid, pokemon_id)
		except Exception as e:
			return await ctx.send(f"Erro ao adicionar: {e}")
		await ctx.send(f"{format_pokemon_display(p, bold_name=True)} foi adicionado à sua party.")

	@party_root.command(name="remove")
	@requires_account()
	async def party_remove(self, ctx: commands.Context, position: Optional[int] = None):
		uid = str(ctx.author.id)
		if not position:
			return await ctx.send(
				"Uso: `.party remove <posição>`\n"
				"Exemplo: `.party remove 3`\n"
				"-# Remove o Pokémon da posição 3 do seu time.\n"
				"-# Use `.party` para ver as posições."
			)
		party = pm.repo.tk.get_user_party(uid)
		if not party:
			return await ctx.send("Seu time está vazio.")
		if not (1 <= position <= len(party)):
			return await ctx.send(f"Posição inválida. Escolha um número de 1 a {len(party)}.")
		
		pokemon_to_remove = party[position - 1]
		pokemon_id = pokemon_to_remove['id']

		try:
			p = pm.repo.tk.move_to_box(uid, pokemon_id)
		except Exception as e:
			return await ctx.send(f"Erro ao remover: {e}")
		await ctx.send(f"{format_pokemon_display(p, bold_name=True)} foi removido da party e movido para a box.")


async def setup(bot: commands.Bot):
	await bot.add_cog(Party(bot))