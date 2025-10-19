import discord
from helpers.timezone import TimezoneHelper
from helpers.gender import Gender

class ProfileLayoutView(discord.ui.LayoutView):
	def __init__(self, user: dict, pokemon_count: int) -> None:
		super().__init__()
		self.user = user
		self.pokemon_count = pokemon_count
		self._build()

	def _build(self) -> None:
		u = self.user
		tz = u['timezone']
		
		badges = u['badges']
		badges_text = f"{len(badges)}/8 Insígnias{f' ({', '.join(badges)})' if badges else ''}"
		
		repel = u['repel_steps']
		repel_text = f"Sim ({repel} passos)" if repel > 0 else "Não"
		
		caught = len(u['pokedex_caught'])
		seen = len(u['pokedex_seen'])
		caught_pct = caught / 386 * 100 if caught else 0
		
		c = discord.ui.Container()
		add = c.add_item
		sep = discord.ui.Separator
		txt = discord.ui.TextDisplay
		
		add(txt("### Seu Perfil"))
		add(sep())
		add(txt(
			"-# **Informações Pessoais**\n"
			f"**Gênero:** {Gender.get_label(u['gender'])}\n"
			f"**Fuso Horário:** {TimezoneHelper.get_label(tz)}\n"
			f"**Seed:** `{u['rng_seed']}`"
		))
		add(sep())
		
		loc_section = discord.ui.Section(accessory=discord.ui.Thumbnail("attachment://location.png"))
		loc_section.add_item(txt(
			"-# **Localização**\n"
			f"**Local Atual:** {u['location']}\n"
			f"**Local Anterior:** {u['previous_location'] or 'Nenhum'}\n"
			f"**Locais Visitados:** {len(u['visited_locations'])}\n"
			f"**Última Movimentação:** {TimezoneHelper.format_datetime(u['last_move_at'], tz)}"
		))
		
		add(loc_section)
		add(sep())
		add(txt(
			"-# **Progressão**\n"
			f"**Insígnias:** {badges_text}\n"
			f"**Passos:** {u['steps']:,}\n"
			f"**Repel Ativo:** {repel_text}"
		))
		add(sep())
		add(txt(
			"-# **Pokédex**\n"
			f"**Capturados:** {caught}/386 ({caught_pct:.1f}%)\n"
			f"**Vistos:** {seen}/386"
		))
		add(sep())
		add(txt(
			"-# **Recursos**\n"
			f"**PokéYens:** ₽ {u['money']:,.2f}\n"
			f"**Pokémon:** {self.pokemon_count}"
		))
		add(sep())
		add(discord.ui.MediaGallery(discord.MediaGalleryItem("attachment://profile.png")))
		add(sep())
		add(txt(f"-# Conta criada em {TimezoneHelper.format_datetime(u['created_at'], tz)}"))
		
		self.add_item(c)