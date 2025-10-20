from typing import Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sdk.database import Database
from sdk.repositories.user_repository import UserRepository
from sdk.constants import TRAVEL_STEP_INTERVAL

class TravelRepository:
	def __init__(self, db: Database, user_repo: UserRepository):
		self.db = db
		self.user_repo = user_repo

	def start_travel(self, user_id: str, from_location: str, destination: str, travel_time: int, channel_id: int) -> dict:
		travels = self.db.get("travels")
		
		now = datetime.now(ZoneInfo("UTC"))
		ends_at = now + timedelta(seconds=travel_time)
		
		travel = {
			"destination": destination,
			"from_location": from_location,
			"started_at": now.isoformat(),
			"ends_at": ends_at.isoformat(),
			"status": "traveling",
			"steps_credited": 0,
			"notification_channel_id": channel_id
		}
		
		travels[user_id] = travel
		self.db.save()
		
		return travel.copy()
	
	def get(self, user_id: str) -> Optional[dict]:
		travels = self.db.get("travels")
		travel = travels.get(user_id)
		return travel.copy() if travel else None
	
	def _calculate_steps_earned(self, elapsed_seconds: float) -> int:
		return int(elapsed_seconds // TRAVEL_STEP_INTERVAL)
	
	def _sync_travel_steps(self, user_id: str) -> int:
		if not self.user_repo:
			return 0
		
		travels = self.db.get("travels")
		travel = travels.get(user_id)
		
		if not travel or travel.get("status") != "traveling":
			return 0
		
		now = datetime.now(ZoneInfo("UTC"))
		started_at = datetime.fromisoformat(travel["started_at"])
		elapsed = (now - started_at).total_seconds()
		
		steps_earned = self._calculate_steps_earned(elapsed)
		steps_credited = travel.get("steps_credited", 0)
		steps_to_add = steps_earned - steps_credited
		
		if steps_to_add > 0:
			self.user_repo.add_steps(user_id, steps_to_add)
			travel["steps_credited"] = steps_earned
			self.db.save()
			return steps_to_add
		
		return 0
	
	def sync_all_travel_steps(self) -> dict[str, int]:
		traveling_users = self.get_all_traveling()
		results = {}
		
		for user_id in traveling_users:
			steps_added = self._sync_travel_steps(user_id)
			if steps_added > 0:
				results[user_id] = steps_added
		
		return results
	
	def get_status(self, user_id: str) -> Optional[dict]:
		travel = self.get(user_id)
		
		if not travel or travel.get("status") != "traveling":
			return None
		
		self._sync_travel_steps(user_id)
		
		now = datetime.now(ZoneInfo("UTC"))
		ends_at = datetime.fromisoformat(travel["ends_at"])
		started_at = datetime.fromisoformat(travel["started_at"])
		
		total_time = (ends_at - started_at).total_seconds()
		elapsed = (now - started_at).total_seconds()
		remaining = max(0, (ends_at - now).total_seconds())
		percentage = min(100, (elapsed / total_time * 100)) if total_time > 0 else 100
		
		steps_earned = self._calculate_steps_earned(elapsed)
		
		return {
			"destination": travel["destination"],
			"from_location": travel["from_location"],
			"started_at": travel["started_at"],
			"ends_at": travel["ends_at"],
			"total_time": total_time,
			"elapsed": elapsed,
			"remaining": remaining,
			"percentage": percentage,
			"completed": now >= ends_at,
			"status": travel["status"],
			"steps_earned": steps_earned,
			"steps_credited": travel.get("steps_credited", 0)
		}
	
	def complete_travel(self, user_id: str) -> Optional[dict]:
		if not self.user_repo:
			raise RuntimeError("UserRepository not set")
		
		travel = self.get(user_id)
		
		if not travel or travel.get("status") != "traveling":
			return None
		
		now = datetime.now(ZoneInfo("UTC"))
		ends_at = datetime.fromisoformat(travel["ends_at"])
		
		if now < ends_at:
			return None
		
		self._sync_travel_steps(user_id)
		
		destination = travel["destination"]
		from_location = travel["from_location"]
		steps_credited = travel.get("steps_credited", 0)
		notification_channel_id = travel.get("notification_channel_id")
		
		users = self.db.get("users")
		user = users[user_id]
		
		user["previous_location"] = user["location"]
		user["location"] = destination
		user["last_move_at"] = now.isoformat()
		
		if destination not in user.get("visited_locations", []):
			user.setdefault("visited_locations", []).append(destination)
		
		visits = user.setdefault("location_visits", {})
		visits[destination] = visits.get(destination, 0) + 1
		
		first_visits = user.setdefault("location_first_visit", {})
		if destination not in first_visits:
			first_visits[destination] = now.isoformat()
		
		self.db.save()
		
		travels = self.db.get("travels")
		del travels[user_id]
		self.db.save()
		
		return {
			"user_id": user_id,
			"destination": destination,
			"from_location": from_location,
			"completed_at": now.isoformat(),
			"steps_earned": steps_credited,
			"notification_channel_id": notification_channel_id
		}
	
	def cancel_travel(self, user_id: str) -> bool:
		travels = self.db.get("travels")
		
		if user_id not in travels:
			return False
		
		self._sync_travel_steps(user_id)
		
		del travels[user_id]
		self.db.save()
		
		return True
	
	def is_traveling(self, user_id: str) -> bool:
		travels = self.db.get("travels")
		travel = travels.get(user_id)
		
		if not travel:
			return False
		
		return travel.get("status") == "traveling"
	
	def get_all_traveling(self) -> list[str]:
		travels = self.db.get("travels")
		return [
			user_id 
			for user_id, travel in travels.items() 
			if travel.get("status") == "traveling"
		]
	
	def auto_complete_travels(self) -> list[dict]:
		traveling_users = self.get_all_traveling()
		completed = []
		
		for user_id in traveling_users:
			status = self.get_status(user_id)
			
			if status and status['completed']:
				result = self.complete_travel(user_id)
				if result:
					completed.append({
						"user_id": user_id,
						**result
					})
		
		return completed
	
	def exists(self, user_id: str) -> bool:
		travels = self.db.get("travels")
		return user_id in travels
	
	def get_count(self) -> int:
		travels = self.db.get("travels")
		return len(travels)
	
	def get_all(self) -> dict[str, dict]:
		travels = self.db.get("travels")
		return {user_id: travel.copy() for user_id, travel in travels.items()}