from typing import Optional
from datetime import datetime
import time
from sdk.database import Database
from sdk.prng import PRNG

class UserRepository:
	def __init__(self, db: Database):
		self.db = db
	
	def create(self, user_id: str, gender: str, location: Optional[str] = "pallet-town-area") -> dict:
		users = self.db.get("users")
		
		if user_id in users:
			return users[user_id].copy()
		
		seed = (int(time.time()) + hash(user_id)) & 0xFFFFFFFF
		
		user = {
			"id": user_id,
			"gender": gender,
			"money": 0,
			"last_pokemon_id": 0,
			"badges": [],
			"rng_seed": seed,
			"location": location,
			"created_at": datetime.utcnow().isoformat()
		}
		
		users[user_id] = user
		self.db.save()
		
		return user.copy()
	
	def get(self, user_id: str) -> Optional[dict]:
		users = self.db.get("users")
		user = users.get(user_id)
		return user.copy() if user else None
	
	def exists(self, user_id: str) -> bool:
		return user_id in self.db.get("users")
	
	def get_rng(self, user_id: str) -> PRNG:
		user = self.db.get("users")[user_id]
		seed = user.get("rng_seed", 0)
		return PRNG(seed)
	
	def save_rng(self, user_id: str, rng: PRNG) -> None:
		users = self.db.get("users")
		users[user_id]["rng_seed"] = rng.get_seed()
		self.db.save()
	
	def set_money(self, user_id: str, amount: int) -> int:
		users = self.db.get("users")
		users[user_id]["money"] = max(0, int(amount))
		self.db.save()
		return users[user_id]["money"]
	
	def add_money(self, user_id: str, amount: int) -> int:
		users = self.db.get("users")
		users[user_id]["money"] = max(0, users[user_id]["money"] + int(amount))
		self.db.save()
		return users[user_id]["money"]
	
	def add_badge(self, user_id: str, badge: str) -> list[str]:
		users = self.db.get("users")
		badges = users[user_id].setdefault("badges", [])
		
		if badge not in badges:
			badges.append(badge)
			self.db.save()
		
		return badges.copy()
	
	def remove_badge(self, user_id: str, badge: str) -> list[str]:
		users = self.db.get("users")
		badges = users[user_id].setdefault("badges", [])
		
		if badge in badges:
			badges.remove(badge)
			self.db.save()
		

		return badges.copy()
