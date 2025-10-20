from data.location.kanto.objects import LOCATIONS
from typing import Optional

def get_location(location_id: str) -> dict | None:
	return LOCATIONS.get(location_id)

def get_location_name(location_id: str) -> str:
	location = LOCATIONS.get(location_id)
	return location["name"] if location else location_id.replace("-", " ").title()

def get_encounter_methods(location_id: str) -> list[str]:
	location = LOCATIONS.get(location_id)
	if not location:
		return []
	
	encounters = location.get("encounters", {})
	methods = []
	
	if encounters.get("walk"):
		methods.append("Caminhando")
	if encounters.get("surf"):
		methods.append("Surfando")
	if encounters.get("fish"):
		methods.append("Pescando")
	
	return methods

def has_any_encounters(location_id: str) -> bool:
	location = LOCATIONS.get(location_id)
	if not location:
		return False
	
	encounters = location.get("encounters", {})
	return any(encounters.values())

def get_encounter_type(location_id: str, method: str = "walk") -> str | None:
	location = LOCATIONS.get(location_id)
	if not location:
		return None
	
	encounters = location.get("encounters", {})
	return encounters.get(method)

def can_access_location(
	location_id: str,
	user_hms: list[str],
	user_badges: list[str],
	user_events: list[str]
) -> tuple[bool, str | None]:
	location = LOCATIONS.get(location_id)
	if not location:
		return False, "Localização inválida"
	
	if location.get("required_hm") and location["required_hm"] not in user_hms:
		return False, f"Você precisa de HM {location['required_hm'].upper()}"
	
	if location.get("required_badge") and location["required_badge"] not in user_badges:
		return False, f"Você precisa da insígnia {location['required_badge'].title()}"
	
	required_events = location.get("required_events", [])
	for event in required_events:
		if event not in user_events:
			return False, "Você não pode acessar este local ainda"
	
	min_badges = location.get("min_badges")
	if min_badges and len(user_badges) < min_badges:
		return False, f"Você precisa de pelo menos {min_badges} insígnias"
	
	return True, None

def can_travel(
	current_location_id: str,
	destination_id: str,
	user_hms: list[str],
	user_badges: list[str],
	user_events: list[str]
) -> tuple[bool, str | None]:
	current = LOCATIONS.get(current_location_id)
	if not current:
		return False, "Localização atual inválida"
	
	if destination_id not in current.get("connections", {}):
		return False, "Não há caminho direto entre essas localizações"
	
	can_access, error = can_access_location(destination_id, user_hms, user_badges, user_events)
	if not can_access:
		return False, error
	
	return True, None

def get_travel_time(location_id: str, destination_id: str) -> int:
	location = LOCATIONS.get(location_id)
	if not location:
		return 0
	
	connection = location.get("connections", {}).get(destination_id)
	return connection["time"] if connection else 0

def get_nearby_locations(location_id: str) -> list[tuple[str, str, int]]:
	location = LOCATIONS.get(location_id)
	if not location:
		return []
	
	return [
		(dest_id, get_location_name(dest_id), conn["time"])
		for dest_id, conn in location.get("connections", {}).items()
	]

def has_service(location_id: str, service: str) -> bool:
	location = LOCATIONS.get(location_id)
	if not location:
		return False
	return location.get(f"has_{service}", False)

def get_mart_items(location_id: str) -> list | None:
	location = LOCATIONS.get(location_id)
	if not location:
		return None
	return location.get("mart_items")

def get_gym_info(location_id: str) -> dict | None:
	location = LOCATIONS.get(location_id)
	if not location:
		return None
	return location.get("gym_info")

def get_available_events(location_id: str, completed_events: list[str]) -> list[str]:
	location = LOCATIONS.get(location_id)
	if not location:
		return []
	
	events = location.get("events", [])
	return [event for event in events if event not in completed_events]

def get_flyable_locations(visited_locations: list[str]) -> list[tuple[str, str]]:
	return [
		(loc_id, loc["name"])
		for loc_id, loc in LOCATIONS.items()
		if loc.get("can_fly_to") and loc_id in visited_locations
	]

def get_location_type(location_id: str) -> str | None:
	location = LOCATIONS.get(location_id)
	if not location:
		return None
	return location.get("type")

def get_all_locations_by_type(location_type: str) -> list[tuple[str, str]]:
	return [
		(loc_id, loc["name"])
		for loc_id, loc in LOCATIONS.items()
		if loc.get("type") == location_type
	]

def is_connected(location_a: str, location_b: str) -> bool:
	loc_a = LOCATIONS.get(location_a)
	if not loc_a:
		return False
	return location_b in loc_a.get("connections", {})