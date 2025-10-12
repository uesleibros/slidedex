from typing import Optional
from sdk.repositories.bag_repository import BagRepository
from sdk.api.services import APIService

class ItemService:
	def __init__(self, bag_repo: BagRepository, api: APIService):
		self.bag = bag_repo
		self.api = api
	
	def get(self, item_id: str) -> Optional[dict]:
		return self.api.get_item(item_id)
	
	def get_name(self, item_id: str, language: str = "en") -> str:
		item = self.get(item_id)
		
		if not item:
			return item_id.replace("-", " ").title()
		
		for name_entry in item.get("names", []):
			if name_entry.get("language", {}).get("name") == language:
				return name_entry["name"]
		
		return item["name"].replace("-", " ").title()
	
	def get_cost(self, item_id: str) -> int:
		item = self.get(item_id)
		return item.get("cost", 0) if item else 0
	
	def get_attributes(self, item_id: str) -> list[str]:
		item = self.get(item_id)
		return [attr["name"] for attr in item.get("attributes", [])] if item else []
	
	def is_holdable(self, item_id: str) -> bool:
		return "holdable" in self.get_attributes(item_id)
	
	def is_consumable(self, item_id: str) -> bool:
		return "consumable" in self.get_attributes(item_id)
	
	def give(self, user_id: str, item_id: str, quantity: int = 1) -> dict:
		item = self.get(item_id)
		item_name = self.get_name(item_id)
		
		if not item:
			raise ValueError(f"Item not found: {item_id}")
		
		category = self._get_category(item)
		new_quantity = self.bag.add(user_id, item_id, item_name, quantity, category)
		
		return {
			"id": item_id,
			"name": item_name,
			"quantity": new_quantity,
			"added": quantity
		}
	
	def _get_category(self, item: dict) -> str:
		name = item.get("name", "")
		
		if name.endswith("-berry"):
			return "berries"
		
		category = item.get("category", {}).get("name", "").lower()
		
		mapping = {
			"stat-boosts": "vitamins",
			"medicine": "medicine",
			"other": "items"
		}
		
		return mapping.get(category, "items")