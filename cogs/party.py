import discord
from discord.ext import commands
from utils.pokemon_emojis import get_app_emoji
from pokemon_sdk.calculations import calculate_stats
from __main__ import pm

async def _fmt_party(party):
	results = []
	for i, p in enumerate(party, start=1):
		name = p.get("nickname") or p.get("name") or f"#{p['species_id']}"
		emoji = get_app_emoji(f"p_{p['species_id']}")
		shiny = "✨ " if p.get("is_shiny") else ""
		poke_api = await pm.service.get_pokemon(p["species_id"])
		base_stats = pm.service.get_base_stats(poke_api)
		stats = calculate_stats(base_stats, p["ivs"], p["evs"], p["level"], p["nature"])
		cur_hp = p.get("current_hp", stats["hp"])
		results.append(
			f"{i}. {emoji} {shiny}{name.title()}\n"
			f" > `id: {p['id']}` `Lv: {p['level']}` `HP: {cur_hp}/{stats['hp']}`"
		)
	return "\n\n".join(results) if results else "Seu time está vazio."


class Party(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.group(name="party", invoke_without_command=True)
	async def party_root(self, ctx: commands.Context):
		uid = str(ctx.author.id)
		party = pm.repo.tk.get_user_party(uid)
		text = await _fmt_party(party)
		await ctx.send(f"Time de {ctx.author.name}:\n{text}")

	@party_root.command(name="reorder", aliases=["order", "set"])
	async def party_reorder(self, ctx: commands.Context, *ids: int):
		uid = str(ctx.author.id)
		if not ids:
			return await ctx.send("Uso: `.party reorder <id1> <id2> …`")
		try:
			reordered = pm.repo.tk.reorder_party(uid, list(map(int, ids)))
		except Exception as e:
			return await ctx.send(f"Erro: {e}")
		text = await _fmt_party(reordered)
		await ctx.send("✅ Nova ordem definida:\n" + text)

	@party_root.command(name="swap")
	async def party_swap(self, ctx: commands.Context, a: int, b: int):
		uid = str(ctx.author.id)
		party = pm.repo.tk.get_user_party(uid)
		if not party:
			return await ctx.send("Seu time está vazio.")
		if not (1 <= a <= len(party) and 1 <= b <= len(party)):
			return await ctx.send(f"Posições válidas: 1 a {len(party)}.")
		ids = [int(p["id"]) for p in party]
		ids[a-1], ids[b-1] = ids[b-1], ids[a-1]
		try:
			swapped = pm.repo.tk.reorder_party(uid, ids)
		except Exception as e:
			return await ctx.send(f"Erro: {e}")
		text = await _fmt_party(swapped)
		await ctx.send("✅ Nova ordem definida:\n" + text)

	@party_root.command(name="add")
	async def party_add(self, ctx: commands.Context, pokemon_id: int):
		uid = str(ctx.author.id)
		try:
			p = pm.repo.tk.move_to_party(uid, pokemon_id)
		except Exception as e:
			return await ctx.send(f"Erro ao adicionar: {e}")
		await ctx.send(f"✅ {p.get('nickname') or p.get('name', f'#{p['species_id']}').title()} foi adicionado à sua party.")

	@party_root.command(name="remove")
	async def party_remove(self, ctx: commands.Context, position: int):
		uid = str(ctx.author.id)
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
		await ctx.send(f"✅ {p.get('nickname') or p.get('name', f'#{p['species_id']}').title()} foi removido da party e movido para a box.")


async def setup(bot: commands.Bot):
	await bot.add_cog(Party(bot))