import orjson
import threading
from pathlib import Path
from typing import Any

class Database:
	__slots__ = ("path", "_lock", "_data")
	
	def __init__(self, path: str = "database.json"):
		self.path = Path(path)
		self._lock = threading.RLock()
		self._data: dict = {}
		self._load()
	
	def _load(self) -> None:
		with self._lock:
			if not self.path.exists():
				self._initialize()
			else:
				self._load_from_file()
	
	def _initialize(self) -> None:
		self._data = {
			"users": {},
			"pokemon": [],
			"bags": []
		}
		self._save()
	
	def _load_from_file(self) -> None:
		with open(self.path, "rb") as f:
			self._data = orjson.loads(f.read())
		
		self._data.setdefault("users", {})
		self._data.setdefault("pokemon", [])
		self._data.setdefault("bags", [])
	
	def save(self) -> None:
		with self._lock:
			tmp_path = self.path.with_suffix(".tmp")
			tmp_path.write_bytes(orjson.dumps(self._data, option=orjson.OPT_INDENT_2))
			tmp_path.replace(self.path)
	
	def _save(self) -> None:
		self.save()
	
	def get(self, key: str) -> Any:
		with self._lock:
			return self._data.get(key)
	
	def set(self, key: str, value: Any) -> None:
		with self._lock:
			self._data[key] = value
			self._save()
	
	def clear(self) -> None:
		with self._lock:
			self._initialize()