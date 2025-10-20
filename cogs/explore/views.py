import discord
from helpers.location import get_location_name, has_service, get_nearby_locations, get_available_events, get_encounter_methods
from helpers.timezone import TimezoneHelper
from helpers.travel import format_time_remaining, get_progress_bar, calculate_travel_progress

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

		container.add_item(txt(f"### {self.location['name']}"))
		container.add_item(sep())

		encounter_methods = get_encounter_methods(self.user['location'])
		encounters_text = ", ".join(encounter_methods) if encounter_methods else "Não"

		container.add_item(txt(
			"-# **Informações do Local**\n"
			f"**Tipo:** {self.location['type'].title()}\n"
			f"**Encontros Selvagens:** {encounters_text}"
		))

		container.add_item(sep())

		services = []
		if has_service(self.user['location'], 'pokemon_center'):
			services.append("Pokémon Center")
		if has_service(self.user['location'], 'mart'):
			services.append("Poké Mart")
		if has_service(self.user['location'], 'gym'):
			services.append("Ginásio")
		if has_service(self.user['location'], 'day_care'):
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

class TravelSelectView(discord.ui.View):
	def __init__(self, user: dict, nearby_locations: list[tuple[str, str, int]]) -> None:
		super().__init__(timeout=60)
		self.user = user
		self.nearby_locations = nearby_locations
		self.selected_destination = None
		
		self._build_select()
	
	def _build_select(self) -> None:
		options = []
		
		for dest_id, dest_name, travel_time in self.nearby_locations:
			time_str = f"{travel_time}s" if travel_time < 60 else f"{travel_time//60}min"
			
			options.append(discord.SelectOption(
				label=dest_name,
				value=dest_id,
				description=f"Tempo de viagem: {time_str}"
			))
		
		select = discord.ui.Select(
			placeholder="Escolha seu destino...",
			options=options,
			custom_id="travel_destination_select"
		)
		
		select.callback = self._on_select
		self.add_item(select)
	
	async def _on_select(self, interaction: discord.Interaction) -> None:
		self.selected_destination = interaction.data["values"][0]
		await interaction.response.defer()
		self.stop()

class TravelStatusView(discord.ui.LayoutView):
	def __init__(self, user: dict, travel_status: dict) -> None:
		super().__init__()
		self.user = user
		self.travel_status = travel_status
		self._build()
	
	def _build(self) -> None:
		c = discord.ui.Container()
		txt = discord.ui.TextDisplay
		sep = discord.ui.Separator
		
		destination_name = get_location_name(self.travel_status['destination'])
		from_name = get_location_name(self.travel_status['from_location'])
		
		progress = calculate_travel_progress(
			self.travel_status['started_at'],
			self.travel_status['ends_at']
		)
		
		progress_bar = get_progress_bar(progress['elapsed'], progress['total'], 15)
		time_remaining = format_time_remaining(progress['remaining'])
		
		if progress['completed']:
			c.add_item(txt("### Viagem Concluída"))
			c.add_item(sep())
			c.add_item(txt(
				f"Você chegou em **{destination_name}**!\n"
				f"Use o comando de mapa para explorar o local."
			))
		else:
			c.add_item(txt("### Viagem em Andamento"))
			c.add_item(sep())
			c.add_item(txt(
				f"**Origem:** {from_name}\n"
				f"**Destino:** {destination_name}\n"
			))
			c.add_item(sep())
			c.add_item(txt(
				f"**Progresso**\n"
				f"{progress['percentage']:.1f}% concluído\n"
				f"`{progress_bar}`\n"
				f"Tempo restante: **{time_remaining}**"
			))
		
		self.add_item(c)

class ArrivalNotificationView(discord.ui.LayoutView):
	def __init__(self, user_id: str, travel: dict) -> None:
		super().__init__()
		self.user_id = user_id
		self.travel = travel
		self._build()
	
	def _build(self) -> None:
		c = discord.ui.Container()
		txt = discord.ui.TextDisplay
		sep = discord.ui.Separator
		
		dest_name = get_location_name(self.travel['destination'])
		from_name = get_location_name(self.travel['from_location'])
		steps_earned = self.travel.get('steps_earned', 0)
		
		c.add_item(txt(f"### Viagem Concluída!"))
		c.add_item(sep())
		
		c.add_item(txt(f"<@{self.user_id}> chegou em **{dest_name}**!"))
		c.add_item(sep())
		
		route_info = f"**Rota**\n{from_name} → {dest_name}"
		
		if steps_earned > 0:
			route_info += f"\n\n**Passos ganhos:** {steps_earned}"
		
		c.add_item(txt(route_info))
		c.add_item(sep())
		
		c.add_item(txt("-# Use o comando `.map` para explorar o local"))
		
		self.add_item(c)