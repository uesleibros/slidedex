import discord
from helpers.location import has_service, get_nearby_locations, get_available_events
from helpers.timezone import TimezoneHelper

class MapLayoutView(discord.ui.LayoutView):
	def __init__(self, user: dict, location: dict) -> None:
		super().__init__()
		self.location = location
		self.user = user

		self._build()

	def _build(self) -> None:
		container: discord.ui.Container = discord.ui.Container()
		add = self.add_item
		sep = discord.ui.Separator
		txt = discord.ui.TextDisplay

		container.add_item(txt(
			f"### {self.location['name']}"
		))

		container.add_item(sep())

		container.add_item(txt(
			"-# **Informações do Local**\n"
			f"**Tipo:** {self.location['type'].title()}\n"
			f"**Encontros Selvagens:** {'Sim' if self.location['wild_encounters'] else 'Não'}\n"
		))

		container.add_item(sep())

		services = []
		if has_service(self.user['location'], 'pokecenter'):
			services.append("Pokémon Center")
		if has_service(self.user['location'], 'mart'):
			services.append("Poké Mart")
		if has_service(self.user['location'], 'gym'):
			services.append("Ginásio")
		if has_service(self.user['location'], 'daycare'):
			services.append("Day Care")
		
		if services:
			container.add_item(txt(
				"-# **Serviços Disponíveis**\n" + 
				"\n".join(f"**•** {s}" for s in services)
			))
			container.add_item(sep())

		nearby = get_nearby_locations(self.user['location'])
		if nearby:
			nearby_text = "-# **Localizações Próximas**\n"
			for dest_id, dest_name, travel_time in nearby:
				time_str = f"{travel_time}s" if travel_time < 60 else f"{travel_time//60}min"
				nearby_text += f"**→** {dest_name} *({time_str})*\n"
			container.add_item(txt(nearby_text.strip()))
			container.add_item(sep())

		available_events = get_available_events(self.user['location'], self.user.get('completed_events', []))
		if available_events:
			container.add_item(txt(
				"-# **Eventos Disponíveis**\n"
				f"**Quantidade:** {len(available_events)} evento(s)\n"
				f"*Use o comando apropriado para interagir*"
			))
			container.add_item(sep())

		container.add_item(discord.ui.MediaGallery(
			discord.MediaGalleryItem("attachment://location.png")
		))
		container.add_item(sep())
		container.add_item(txt(
			f"-# Última movimentação: {TimezoneHelper.format_datetime(self.user['last_move_at'], self.user['timezone'])}"
		))

		add(container)