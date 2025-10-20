import asyncio
import logging
from typing import Optional, Callable, Awaitable
from datetime import datetime
from zoneinfo import ZoneInfo
from sdk.repositories.travel_repository import TravelRepository
from sdk.constants import TRAVEL_STEP_INTERVAL

logger = logging.getLogger(__name__)

class TravelService:
	def __init__(self, travel_repo: TravelRepository):
		self.travel_repo = travel_repo
		self.running = False
		self.task: Optional[asyncio.Task] = None
		self.check_interval = 1
		self.on_arrival_callback: Optional[Callable[[dict], Awaitable[None]]] = None
		
	def set_arrival_callback(self, callback: Callable[[dict], Awaitable[None]]) -> None:
		self.on_arrival_callback = callback
	
	async def start(self) -> None:
		if self.running:
			logger.warning("TravelService já está rodando")
			return
		
		self.running = True
		self.task = asyncio.create_task(self._travel_loop())
		logger.info("TravelService iniciado")
	
	async def stop(self) -> None:
		if not self.running:
			return
		
		self.running = False
		
		if self.task:
			self.task.cancel()
			try:
				await self.task
			except asyncio.CancelledError:
				pass
		
		logger.info("TravelService finalizado")
	
	async def _travel_loop(self) -> None:
		logger.info("Loop de viagens iniciado")
		
		while self.running:
			try:
				await self._process_travels()
				await asyncio.sleep(self.check_interval)
			
			except asyncio.CancelledError:
				logger.info("Loop de viagens cancelado")
				break
			
			except Exception as e:
				logger.error(f"Erro no loop de viagens: {e}", exc_info=True)
				await asyncio.sleep(self.check_interval)
	
	async def _process_travels(self) -> None:
		steps_synced = self.travel_repo.sync_all_travel_steps()
		
		if steps_synced:
			logger.debug(f"Passos sincronizados para {len(steps_synced)} viajantes")
		
		completed = self.travel_repo.auto_complete_travels()
		
		for travel in completed:
			logger.info(
				f"Viagem completada - user_id: {travel['user_id']}, "
				f"destination: {travel['destination']}, "
				f"steps: {travel.get('steps_earned', 0)}"
			)
			
			if self.on_arrival_callback:
				try:
					await self.on_arrival_callback(travel)
				except Exception as e:
					logger.error(f"Erro no callback de chegada: {e}", exc_info=True)
	
	def is_running(self) -> bool:
		return self.running