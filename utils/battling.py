import threading
from typing import Set

class BattleTracker:
    def __init__(self):
        self._battling: Set[str] = set()
        self._lock = threading.Lock()
    
    def add(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._battling:
                return False
            self._battling.add(user_id)
            return True
    
    def remove(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._battling:
                self._battling.discard(user_id)
                return True
            return False
    
    def is_battling(self, user_id: str) -> bool:
        with self._lock:
            return user_id in self._battling
    
    def clear(self) -> None:
        with self._lock:
            self._battling.clear()
    
    def get_all(self) -> Set[str]:
        with self._lock:
            return self._battling.copy()
    
    def count(self) -> int:
        with self._lock:
            return len(self._battling)
