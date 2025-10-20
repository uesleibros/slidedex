import discord
import logging
from discord.ext import commands
from sdk.toolkit import Toolkit
from helpers.location import get_location_name
from cogs.explore.views import ArrivalNotificationView

logger = logging.getLogger(__name__)

class TravelManager(commands.Cog):
	def __init__(self, bot: commands.Bot) -> None:
		self.bot = bot
		self.tk: Toolkit = Toolkit()
		self.tk.travel_service.set_arrival_callback(self._on_arrival)
	
	async def cog_load(self) -> None:
		await self.tk.travel_service.start()
		logger.info("TravelManager carregado e serviço iniciado")
	
	async def cog_unload(self) -> None:
		await self.tk.travel_service.stop()
		logger.info("TravelManager descarregado e serviço parado")
	
	async def _on_arrival(self, travel: dict) -> None:
		user_id = travel['user_id']
		channel_id = travel.get('notification_channel_id')
		
		try:
			channel = self.bot.get_channel(channel_id)
			if not channel:
				channel = await self.bot.fetch_channel(channel_id)

			view = ArrivalNotificationView(user_id, travel)
			await channel.send(view=view)

			logger.info(f"Notificação enviada no canal #{channel.name} para user_id={user_id}")
		except discord.Forbidden:
			logger.debug(f"Sem permissão para enviar mensagem no canal {channel_id}")
		
		except discord.HTTPException as e:
			logger.warning(f"Erro HTTP ao notificar no canal {channel_id}: {e}")

		except Exception as e:
			logger.error(f"Erro ao notificar user_id={user_id}: {e}", exc_info=True)

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(TravelManager(bot))