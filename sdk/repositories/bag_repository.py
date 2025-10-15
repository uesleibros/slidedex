from typing import Final
from sdk.database import Database

MAX_ITEM_QUANTITY: Final[int] = 999

class BagRepository:
	def __init__(self, db: Database):
		self.db = db
	
	def get_all(self, user_id: str) -> list[dict]:
		bags = self.db.get("bags")
		return [item.copy() for item in bags if item["owner_id"] == user_id]
	
	def get_quantity(self, user_id: str, item_id: str) -> int:
		bags = self.db.get("bags")
		
		for item in bags:
			if item["owner_id"] == user_id and item["id"] == item_id:
				return item["quantity"]
		
		return 0
	
	def has_item(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
		return self.get_quantity(user_id, item_id) >= quantity
	
	def add(self, user_id: str, item_id: str, item_name: str, quantity: int = 1, category: str = "items") -> int:
		if quantity <= 0:
			raise ValueError(f"Quantity must be positive: {quantity}")
		
		bags = self.db.get("bags")
		
		for item in bags:
			if item["owner_id"] == user_id and item["id"] == item_id:
				new_quantity = min(item["quantity"] + quantity, MAX_ITEM_QUANTITY)
				added = new_quantity - item["quantity"]
				
				if added < quantity:
					raise ValueError(
						f"Cannot add {quantity} items. "
						f"Current: {item['quantity']}, Max: {MAX_ITEM_QUANTITY}, Can add: {added}"
					)
				
				item["quantity"] = new_quantity
				self.db.save()
				return item["quantity"]
		
		if quantity > MAX_ITEM_QUANTITY:
			raise ValueError(f"Quantity exceeds maximum: {quantity} > {MAX_ITEM_QUANTITY}")
		
		bags.append({
			"owner_id": user_id,
			"id": item_id,
			"name": item_name,
			"category": category,
			"quantity": quantity
		})
		
		self.db.save()
		return quantity
	
	def remove(self, user_id: str, item_id: str, quantity: int = 1) -> int:
		if quantity <= 0:
			raise ValueError(f"Quantity must be positive: {quantity}")
		
		bags = self.db.get("bags")
		
		for i, item in enumerate(bags):
			if item["owner_id"] == user_id and item["id"] == item_id:
				if item["quantity"] < quantity:
					raise ValueError(
						f"Not enough items: has {item['quantity']}, needs {quantity}"
					)
				
				item["quantity"] -= quantity
				
				if item["quantity"] <= 0:
					del bags[i]
					self.db.save()
					return 0
				
				self.db.save()
				return item["quantity"]
		
		raise ValueError(f"Item not found: {item_id}")
	
	def set_quantity(self, user_id: str, item_id: str, quantity: int, category: str = "items") -> int:
		if quantity < 0:
			raise ValueError(f"Quantity cannot be negative: {quantity}")
		
		if quantity > MAX_ITEM_QUANTITY:
			raise ValueError(f"Quantity exceeds maximum: {quantity} > {MAX_ITEM_QUANTITY}")
		
		bags = self.db.get("bags")
		
		if quantity == 0:
			bags[:] = [
				item for item in bags 
				if not (item["owner_id"] == user_id and item["id"] == item_id)
			]
			self.db.save()
			return 0
		
		for item in bags:
			if item["owner_id"] == user_id and item["id"] == item_id:
				item["quantity"] = quantity
				self.db.save()
				return quantity
		
		bags.append({
			"owner_id": user_id,
			"id": item_id,
			"category": category,
			"quantity": quantity
		})
		
		self.db.save()
		return quantity
	
	def clear(self, user_id: str) -> None:
		bags = self.db.get("bags")
		bags[:] = [item for item in bags if item["owner_id"] != user_id]
		self.db.save()
	
	def clear_category(self, user_id: str, category: str) -> None:
		bags = self.db.get("bags")
		bags[:] = [
			item for item in bags 
			if not (item["owner_id"] == user_id and item.get("category") == category)
		]
		self.db.save()
	
	def get_by_category(self, user_id: str, category: str) -> list[dict]:
		bags = self.db.get("bags")
		return [
			item.copy() for item in bags 
			if item["owner_id"] == user_id and item.get("category") == category
		]
	
	def count_total_items(self, user_id: str) -> int:
		bags = self.db.get("bags")
		return sum(
			item["quantity"] for item in bags 
			if item["owner_id"] == user_id
		)
	
	def count_unique_items(self, user_id: str) -> int:
		bags = self.db.get("bags")
		return sum(
			1 for item in bags 
			if item["owner_id"] == user_id
		)
	
	def is_empty(self, user_id: str) -> bool:
		return self.count_unique_items(user_id) == 0
	
	def transfer(self, from_user_id: str, to_user_id: str, item_id: str, quantity: int = 1) -> tuple[int, int]:
		from_qty = self.remove(from_user_id, item_id, quantity)
		to_qty = self.add(to_user_id, item_id, quantity)
		return (from_qty, to_qty)
	
	def get_item_info(self, user_id: str, item_id: str) -> dict | None:
		bags = self.db.get("bags")
		
		for item in bags:
			if item["owner_id"] == user_id and item["id"] == item_id:
				return item.copy()
		
		return None
	
	def can_add(self, user_id: str, item_id: str, quantity: int) -> bool:
		current_qty = self.get_quantity(user_id, item_id)

		return (current_qty + quantity) <= MAX_ITEM_QUANTITY

