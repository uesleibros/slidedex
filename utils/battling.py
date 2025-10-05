import threading
from typing import Set, Dict, Any, Optional

class BattleTracker:
	def __init__(self):
		self._battling: Set[str] = set()
		self._battle_instances: Dict[str, Any] = {}
		self._lock = threading.Lock()
	
	def add(self, user_id: str, battle_instance: Optional[Any] = None) -> bool:
		with self._lock:
			if user_id in self._battling:
				return False
			self._battling.add(user_id)
			if battle_instance is not None:
				self._battle_instances[user_id] = battle_instance
			return True
	
	def remove(self, user_id: str) -> bool:
		with self._lock:
			if user_id in self._battling:
				self._battling.discard(user_id)
				self._battle_instances.pop(user_id, None)
				return True
			return False
	
	def is_battling(self, user_id: str) -> bool:
		with self._lock:
			return user_id in self._battling
	
	def get_battle(self, user_id: str) -> Optional[Any]:
		with self._lock:
			return self._battle_instances.get(user_id)
	
	def set_battle(self, user_id: str, battle_instance: Any) -> bool:
		with self._lock:
			if user_id not in self._battling:
				return False
			self._battle_instances[user_id] = battle_instance
			return True
	
	def has_battle_instance(self, user_id: str) -> bool:
		with self._lock:
			return user_id in self._battle_instances
	
	def clear(self) -> None:
		with self._lock:
			self._battling.clear()
			self._battle_instances.clear()
	
	def get_all(self) -> Set[str]:
		with self._lock:
			return self._battling.copy()
	
	def count(self) -> int:
		with self._lock:
			return len(self._battling)
	
	def get_all_battles(self) -> Dict[str, Any]:
		with self._lock:
			return self._battle_instances.copy()