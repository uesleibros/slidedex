from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from sdk.database import Database
from sdk.prng import PRNG
from helpers.gender import Gender
import time

class UserRepository:
	def __init__(self, db: Database):
		self.db = db
	
	def create(
		self,
		user_id: str,
		gender: str,
		timezone: str = "America/Sao_Paulo",
		location: Optional[str] = "pallet-town-area"
	) -> dict:
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
			"timezone": timezone,
			"location": location,
			"previous_location": None,
			"visited_locations": [location],
			"completed_events": [],
			"steps": 0,
			"repel_steps": 0,
			"pokedex_caught": [],
			"pokedex_seen": [],
			"last_move_at": datetime.now(ZoneInfo("UTC")).isoformat(),
			"created_at": datetime.now(ZoneInfo("UTC")).isoformat()
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

	def set_gender(self, user_id: str, gender: str) -> str:
		users =self.db.get("users")
		gender_normalized: str = Gender.normalize(gender)
		users[user_id]["gender"] = gender_normalized
		self.db.save()
		return gender_normalized
	
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

	def move_to(self, user_id: str, new_location: str) -> dict:
		users = self.db.get("users")
		user = users[user_id]
		
		user["previous_location"] = user["location"]
		user["location"] = new_location
		user["last_move_at"] = datetime.now(ZoneInfo("UTC")).isoformat()
		
		if new_location not in user.get("visited_locations", []):
			user.setdefault("visited_locations", []).append(new_location)
		
		self.db.save()
		
		self.add_steps(user_id, 1)
		
		return user.copy()

	def add_steps(self, user_id: str, steps: int = 1) -> int:
		users = self.db.get("users")
		users[user_id]["steps"] = users[user_id].get("steps", 0) + steps
		
		if users[user_id].get("repel_steps", 0) > 0:
			users[user_id]["repel_steps"] = max(0, users[user_id]["repel_steps"] - steps)
		
		self.db.save()
		return users[user_id]["steps"]

	def add_pokedex_seen(self, user_id: str, pokemon_id: int) -> list[int]:
		users = self.db.get("users")
		seen = users[user_id].setdefault("pokedex_seen", [])
		
		if pokemon_id not in seen:
			seen.append(pokemon_id)
			self.db.save()
		
		return seen.copy()

	def add_pokedex_caught(self, user_id: str, pokemon_id: int) -> list[int]:
		users = self.db.get("users")
		caught = users[user_id].setdefault("pokedex_caught", [])
		
		if pokemon_id not in caught:
			caught.append(pokemon_id)
			self.add_pokedex_seen(user_id, pokemon_id)
			self.db.save()
		
		return caught.copy()
	
	def remove_badge(self, user_id: str, badge: str) -> list[str]:
		users = self.db.get("users")
		badges = users[user_id].setdefault("badges", [])
		
		if badge in badges:
			badges.remove(badge)
			self.db.save()
		
		return badges.copy()

	def get_timezone(self, user_id: str) -> str:
		users = self.db.get("users")
		return users[user_id].get("timezone", "America/Sao_Paulo")

	def get_visited_locations(self, user_id: str) -> list[str]:
		users = self.db.get("users")
		return users[user_id].get("visited_locations", []).copy()

	def has_completed_event(self, user_id: str, event_id: str) -> bool:
		users = self.db.get("users")
		completed = users[user_id].get("completed_events", [])
		return event_id in completed

	def complete_event(self, user_id: str, event_id: str) -> None:
		users = self.db.get("users")
		completed = users[user_id].setdefault("completed_events", [])
		if event_id not in completed:
			completed.append(event_id)
			self.db.save()

	def get_completed_events(self, user_id: str) -> list[str]:
		users = self.db.get("users")
		return users[user_id].get("completed_events", []).copy()

	def get_available_events_at(self, user_id: str, location_id: str) -> list[str]:
		from helpers.location import get_available_events
		completed = self.get_completed_events(user_id)
		return get_available_events(location_id, completed)