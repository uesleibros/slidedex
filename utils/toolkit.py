import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pokemon_sdk.constants import NATURES, STAT_KEYS
import copy

PARTY_LIMIT = 6
MOVES_LIMIT = 4
EV_PER_STAT_MAX = 255
EV_TOTAL_MAX = 510

class Toolkit:
	def __init__(self, path: str = "database.json"):
		self.path = path
		self._lock = threading.RLock()
		self.db: Dict = {}
		self._pk_index: Dict[Tuple[str, int], int] = {}
		self.NATURES = NATURES
		self._load()

	def _load(self):
		with self._lock:
			if not os.path.exists(self.path):
				self.db = {"users": {}, "pokemon": []}
				self._save()
			else:
				with open(self.path, "r", encoding="utf-8") as f:
					self.db = json.load(f)
				if "users" not in self.db or "pokemon" not in self.db:
					self.db = {"users": {}, "pokemon": []}
					self._save()
			self._reindex()

	def clear(self):
		self.db = {"users": {}, "pokemon": []}
		self._save()

	def _reindex(self):
		self._pk_index = {}
		for i, p in enumerate(self.db["pokemon"]):
			self._pk_index[(p["owner_id"], int(p["id"]))] = i

	def _save(self):
		with self._lock:
			tmp = self.path + ".tmp"
			with open(tmp, "w", encoding="utf-8") as f:
				json.dump(self.db, f, indent=2, ensure_ascii=False)
			os.replace(tmp, self.path)

	def _deepcopy(self, obj):
		return copy.deepcopy(obj)

	def _ensure_user(self, user_id: str):
		if user_id not in self.db["users"]:
			raise ValueError("User not found")

	def _get_pokemon_index(self, owner_id: str, pokemon_id: int) -> int:
		idx = self._pk_index.get((owner_id, int(pokemon_id)))
		if idx is None:
			raise ValueError("Pokemon not found")
		return idx

	def _validate_ivs(self, ivs: Dict[str, int]):
		if set(ivs.keys()) != set(STAT_KEYS):
			raise ValueError("Invalid IV keys")
		for k, v in ivs.items():
			if not isinstance(v, int) or v < 0 or v > 31:
				raise ValueError("Invalid IV value")

	def _validate_evs(self, evs: Dict[str, int]):
		if set(evs.keys()) != set(STAT_KEYS):
			raise ValueError("Invalid EV keys")
		total = 0
		for k, v in evs.items():
			if not isinstance(v, int) or v < 0 or v > EV_PER_STAT_MAX:
				raise ValueError("Invalid EV value")
			total += v
		if total > EV_TOTAL_MAX:
			raise ValueError("EV total exceeds limit")

	def add_user(self, user_id: str, gender: str) -> Dict:
		with self._lock:
			if user_id not in self.db["users"]:
				self.db["users"][user_id] = {
					"id": user_id,
					"gender": gender,
					"money": 0,
					"last_pokemon_id": 0,
					"badges": [],
					"created_at": datetime.utcnow().isoformat()
				}
				self._save()
			return self._deepcopy(self.db["users"][user_id])

	def get_user(self, user_id: str) -> Optional[Dict]:
		with self._lock:
			return self._deepcopy(self.db["users"].get(user_id))

	def set_money(self, user_id: str, amount: int) -> int:
		with self._lock:
			self._ensure_user(user_id)
			self.db["users"][user_id]["money"] = int(amount)
			self._save()
			return self.db["users"][user_id]["money"]

	def adjust_money(self, user_id: str, delta: int) -> int:
		with self._lock:
			self._ensure_user(user_id)
			self.db["users"][user_id]["money"] += int(delta)
			self._save()
			return self.db["users"][user_id]["money"]

	def add_badge(self, user_id: str, badge: str) -> List[str]:
		with self._lock:
			self._ensure_user(user_id)
			b = self.db["users"][user_id].setdefault("badges", [])
			if badge not in b:
				b.append(badge)
				self._save()
			return list(b)

	def remove_badge(self, user_id: str, badge: str) -> List[str]:
		with self._lock:
			self._ensure_user(user_id)
			b = self.db["users"][user_id].setdefault("badges", [])
			if badge in b:
				b.remove(badge)
				self._save()
			return list(b)

	def get_user_pokemon(self, user_id: str, on_party: Optional[bool] = None) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			result = []
			for p in self.db["pokemon"]:
				if p["owner_id"] != user_id:
					continue
				if on_party is None or p.get("on_party", False) == on_party:
					result.append(self._deepcopy(p))
			return result

	def get_user_party(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			party = [self._deepcopy(p) for p in self.db["pokemon"] if p["owner_id"] == user_id and p.get("on_party", False)]
			if not party:
				return []
			if any("party_pos" not in p for p in party):
				party.sort(key=lambda p: p.get("caught_at", ""))
				for pos, p in enumerate(party, start=1):
					idx = self._get_pokemon_index(user_id, p["id"])
					self.db["pokemon"][idx]["party_pos"] = pos
				self._save()
				party = [self._deepcopy(p) for p in self.db["pokemon"] if p["owner_id"] == user_id and p.get("on_party", False)]
			party.sort(key=lambda p: p.get("party_pos", 999))
			return party

	def reorder_party(self, owner_id: str, order: List[int]) -> List[Dict]:
		with self._lock:
			self._ensure_user(owner_id)
			party = [p for p in self.db["pokemon"] if p["owner_id"] == owner_id and p.get("on_party", False)]
			if not party:
				return []
			current_ids = [int(p["id"]) for p in party]
			if len(order) != len(current_ids):
				raise ValueError("Número de IDs não coincide com a quantidade de Pokémon na party")
			if set(order) != set(current_ids):
				raise ValueError("IDs informados não correspondem ao time atual")
			for pos, pid in enumerate(order, start=1):
				idx = self._get_pokemon_index(owner_id, pid)
				self.db["pokemon"][idx]["party_pos"] = pos
			self._save()
			return [self._deepcopy(self.db["pokemon"][self._get_pokemon_index(owner_id, pid)]) for pid in order]

	def swap_party(self, owner_id: str, a: int, b: int) -> List[Dict]:
		with self._lock:
			party = self.get_user_party(owner_id)
			if not party:
				return []
			if not (1 <= a <= len(party) and 1 <= b <= len(party)):
				raise ValueError("Posições inválidas")
			ids = [int(p["id"]) for p in party]
			ids[a-1], ids[b-1] = ids[b-1], ids[a-1]
			return self.reorder_party(owner_id, ids)

	def get_user_box(self, user_id: str) -> List[Dict]:
		return self.get_user_pokemon(user_id, on_party=False)

	def get_party_count(self, user_id: str) -> int:
		with self._lock:
			self._ensure_user(user_id)
			return sum(1 for p in self.db["pokemon"] if p["owner_id"] == user_id and p.get("on_party", False))

	def can_add_to_party(self, user_id: str) -> bool:
		return self.get_party_count(user_id) < PARTY_LIMIT

	def move_to_party(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			if not self.db["pokemon"][idx].get("on_party", False) and not self.can_add_to_party(owner_id):
				raise ValueError("Party is full")
			self.db["pokemon"][idx]["on_party"] = True
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def move_to_box(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["on_party"] = False
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def add_pokemon(self, owner_id: str, species_id: int, ivs: Dict[str, int], nature: str, ability: str, gender: str, shiny: bool, types: List[str], region: str, is_legendary: bool, is_mythical: bool, stats: Dict, level: int = 1, exp: int = 0, held_item: Optional[str] = None, moves: Optional[List[Dict]] = None, nickname: Optional[str] = None, name: Optional[str] = None, current_hp: Optional[int] = None, on_party: Optional[bool] = None) -> Dict:
		with self._lock:
			self._ensure_user(owner_id)
			self._validate_ivs(ivs)
			base_evs = {k: 0 for k in STAT_KEYS}
			auto_party = self.get_party_count(owner_id) < PARTY_LIMIT
			final_on_party = auto_party if on_party is None else (on_party and auto_party)
			user = self.db["users"][owner_id]
			user["last_pokemon_id"] += 1
			new_id = user["last_pokemon_id"]
			pkmn = {
				"id": int(new_id),
				"species_id": int(species_id),
				"nickname": nickname,
				"name": name,
				"owner_id": owner_id,
				"level": int(level),
				"exp": int(exp),
				"ivs": ivs,
				"evs": base_evs,
				"nature": nature,
				"ability": ability,
				"types": types,
				"is_legendary": is_legendary,
				"is_mythical": is_mythical,
				"stats": stats,
				"region": region,
				"gender": gender,
				"is_shiny": bool(shiny),
				"background": "lab",
				"held_item": held_item,
				"is_favorite": False,
				"caught_at": datetime.utcnow().isoformat(),
				"moves": [],
				"current_hp": current_hp if current_hp is None else int(current_hp),
				"on_party": final_on_party
			}
			if moves:
				if len(moves) > MOVES_LIMIT:
					raise ValueError("Too many moves")
				for m in moves:
					if not isinstance(m, dict) or "id" not in m or "pp" not in m or "pp_max" not in m:
						raise ValueError("Invalid move shape")
				pkmn["moves"] = moves
			self.db["pokemon"].append(pkmn)
			self._pk_index[(owner_id, int(new_id))] = len(self.db["pokemon"]) - 1
			self._save()
			return self._deepcopy(pkmn)

	def get_pokemon(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			return self._deepcopy(self.db["pokemon"][idx])

	def list_pokemon_by_owner(self, owner_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(owner_id)
			return [self._deepcopy(p) for p in self.db["pokemon"] if p["owner_id"] == owner_id]

	def set_level(self, owner_id: str, pokemon_id: int, level: int) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["level"] = int(level)
			self._save()
			return self.db["pokemon"][idx]["level"]

	def exp_to_next_level(self, level: int) -> int:
		return level ** 3

	def add_exp(self, owner_id: str, pokemon_id: int, exp_gain: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			p["exp"] += int(exp_gain)
			lvl = p["level"]
			while p["exp"] >= self.exp_to_next_level(lvl):
				p["exp"] -= self.exp_to_next_level(lvl)
				lvl += 1
			p["level"] = lvl
			self._save()
			return self._deepcopy(p)

	def calc_battle_exp(self, poke_level: int, enemy_level: int) -> int:
		base = enemy_level * 10
		bonus = max(0, (enemy_level - poke_level) * 5)
		xp = base + bonus
		return max(1, xp)
	
	def set_ivs(self, owner_id: str, pokemon_id: int, ivs: Dict[str, int]) -> Dict:
		with self._lock:
			self._validate_ivs(ivs)
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["ivs"] = ivs
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def set_evs(self, owner_id: str, pokemon_id: int, evs: Dict[str, int]) -> Dict:
		with self._lock:
			self._validate_evs(evs)
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["evs"] = evs
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def add_evs(self, owner_id: str, pokemon_id: int, delta: Dict[str, int]) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			current = self.db["pokemon"][idx]["evs"]
			new = {k: int(current.get(k, 0)) + int(delta.get(k, 0)) for k in STAT_KEYS}
			self._validate_evs(new)
			self.db["pokemon"][idx]["evs"] = new
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def set_nature(self, owner_id: str, pokemon_id: int, nature: str) -> str:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["nature"] = nature
			self._save()
			return nature

	def set_ability(self, owner_id: str, pokemon_id: int, ability: str) -> str:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["ability"] = ability
			self._save()
			return ability

	def set_gender(self, owner_id: str, pokemon_id: int, gender: str) -> str:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["gender"] = gender
			self._save()
			return gender

	def set_shiny(self, owner_id: str, pokemon_id: int, shiny: bool) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["is_shiny"] = bool(shiny)
			self._save()
			return self.db["pokemon"][idx]["is_shiny"]

	def set_held_item(self, owner_id: str, pokemon_id: int, item: Optional[str]) -> Optional[str]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["held_item"] = item
			self._save()
			return item

	def set_nickname(self, owner_id: str, pokemon_id: int, nickname: Optional[str]) -> Optional[str]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["nickname"] = nickname
			self._save()
			return nickname

	def set_current_hp(self, owner_id: str, pokemon_id: int, current_hp: Optional[int]) -> Optional[int]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["current_hp"] = current_hp if current_hp is None else int(current_hp)
			self._save()
			return self.db["pokemon"][idx]["current_hp"]

	def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> List[Dict]:
		with self._lock:
			if len(moves) > MOVES_LIMIT:
				raise ValueError("Too many moves")
			for m in moves:
				if not isinstance(m, dict) or "id" not in m or "pp" not in m or "pp_max" not in m:
					raise ValueError("Invalid move shape")
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["moves"] = moves
			self._save()
			return self._deepcopy(self.db["pokemon"][idx]["moves"])

	def add_move(self, owner_id: str, pokemon_id: int, move_id: str, pp: int, pp_max: int) -> List[Dict]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			mv = self.db["pokemon"][idx]["moves"]
			if len(mv) >= MOVES_LIMIT:
				raise ValueError("Move slots full")
			mv.append({"id": move_id, "pp": int(pp), "pp_max": int(pp_max)})
			self._save()
			return self._deepcopy(mv)

	def remove_move(self, owner_id: str, pokemon_id: int, move_id: str) -> List[Dict]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			mv = self.db["pokemon"][idx]["moves"]
			mv = [m for m in mv if m["id"] != move_id]
			self.db["pokemon"][idx]["moves"] = mv
			self._save()
			return self._deepcopy(mv)

	def set_move_pp(self, owner_id: str, pokemon_id: int, move_id: str, pp: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			found = False
			for m in self.db["pokemon"][idx]["moves"]:
				if m["id"] == move_id:
					m["pp"] = max(0, min(int(pp), int(m["pp_max"])))
					found = True
					break
			if not found:
				raise ValueError("Move not found")
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def restore_pp(self, owner_id: str, pokemon_id: int) -> List[Dict]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			for m in self.db["pokemon"][idx]["moves"]:
				m["pp"] = int(m["pp_max"])
			self._save()
			return self._deepcopy(self.db["pokemon"][idx]["moves"])

	def transfer_pokemon(self, owner_id: str, pokemon_id: int, new_owner_id: str) -> Dict:
		with self._lock:
			self._ensure_user(new_owner_id)
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			p["owner_id"] = new_owner_id
			if p.get("on_party", False) and not self.can_add_to_party(new_owner_id):
				p["on_party"] = False
			self._reindex()
			self._save()
			return self._deepcopy(p)

	def release_pokemon(self, owner_id: str, pokemon_id: int) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			del self.db["pokemon"][idx]
			self._reindex()
			self._save()
			return True

	def iv_total(self, owner_id: str, pokemon_id: int) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			return sum(self.db["pokemon"][idx]["ivs"][k] for k in STAT_KEYS)

	def iv_percent(self, owner_id: str, pokemon_id: int, decimals: int = 2) -> float:
		total = self.iv_total(owner_id, pokemon_id)

		return round((total / 186) * 100.0, decimals)

	def set_favorite(self, owner_id: str, pokemon_id: int, is_favorite: bool) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["is_favorite"] = bool(is_favorite)
			self._save()
			return self.db["pokemon"][idx]["is_favorite"]

	def toggle_favorite(self, owner_id: str, pokemon_id: int) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			current = self.db["pokemon"][idx].get("is_favorite", False)
			self.db["pokemon"][idx]["is_favorite"] = not current
			self._save()
			return self.db["pokemon"][idx]["is_favorite"]

	def set_background(self, owner_id: str, pokemon_id: int, background: str) -> str:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["background"] = background
			self._save()
			return background

	def get_favorites(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			favorites = []
			for p in self.db["pokemon"]:
				if p["owner_id"] == user_id and p.get("is_favorite", False):
					favorites.append(self._deepcopy(p))
			return favorites

	def get_pokemon_count(self, user_id: str) -> Dict[str, int]:
		with self._lock:
			self._ensure_user(user_id)
			total = 0
			party = 0
			box = 0
			favorites = 0
			shiny = 0
			legendary = 0
			mythical = 0
			
			for p in self.db["pokemon"]:
				if p["owner_id"] == user_id:
					total += 1
					if p.get("on_party", False):
						party += 1
					else:
						box += 1
					if p.get("is_favorite", False):
						favorites += 1
					if p.get("is_shiny", False):
						shiny += 1
					if p.get("is_legendary", False):
						legendary += 1
					if p.get("is_mythical", False):
						mythical += 1
			
			return {
				"total": total,
				"party": party,
				"box": box,
				"favorites": favorites,
				"shiny": shiny,
				"legendary": legendary,
				"mythical": mythical
			}

	def heal_pokemon(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			
			p["current_hp"] = None
			
			for move in p.get("moves", []):
				move["pp"] = move["pp_max"]
			
			self._save()
			return self._deepcopy(p)

	def heal_party(self, owner_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(owner_id)
			healed = []
			
			for p in self.db["pokemon"]:
				if p["owner_id"] == owner_id and p.get("on_party", False):
					p["current_hp"] = None
					
					for move in p.get("moves", []):
						move["pp"] = move["pp_max"]
					
					healed.append(self._deepcopy(p))
			
			self._save()
			return healed

	def get_pokemon_by_species(self, user_id: str, species_id: int) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			result = []
			for p in self.db["pokemon"]:
				if p["owner_id"] == user_id and p["species_id"] == species_id:
					result.append(self._deepcopy(p))
			return result

	def get_shiny_pokemon(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			shiny = []
			for p in self.db["pokemon"]:
				if p["owner_id"] == user_id and p.get("is_shiny", False):
					shiny.append(self._deepcopy(p))
			return shiny

	def get_legendary_pokemon(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			legendary = []
			for p in self.db["pokemon"]:
				if p["owner_id"] == user_id and p.get("is_legendary", False):
					legendary.append(self._deepcopy(p))
			return legendary

	def get_mythical_pokemon(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			mythical = []
			for p in self.db["pokemon"]:
				if p["owner_id"] == user_id and p.get("is_mythical", False):
					mythical.append(self._deepcopy(p))
			return mythical

	def update_pokemon_stats(self, owner_id: str, pokemon_id: int, stats: Dict) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["stats"] = stats
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def set_types(self, owner_id: str, pokemon_id: int, types: List[str]) -> List[str]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["types"] = types
			self._save()
			return types

	def get_pokemon_summary(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self._deepcopy(self.db["pokemon"][idx])
			
			p["iv_total"] = self.iv_total(owner_id, pokemon_id)
			p["iv_percent"] = self.iv_percent(owner_id, pokemon_id)
			p["ev_total"] = sum(p["evs"].values())
			
			level = p["level"]
			nature_mod = self.NATURES.get(p["nature"], {})
			
			calculated_stats = {}
			for stat in STAT_KEYS:
				base = p["stats"].get(stat, 0)
				iv = p["ivs"][stat]
				ev = p["evs"][stat]
				
				if stat == "hp":
					calculated_stats[stat] = int((2 * base + iv + ev // 4) * level / 100) + level + 10
				else:
					stat_value = int((2 * base + iv + ev // 4) * level / 100) + 5
					if nature_mod.get("increased") == stat:
						stat_value = int(stat_value * 1.1)
					elif nature_mod.get("decreased") == stat:
						stat_value = int(stat_value * 0.9)
					calculated_stats[stat] = stat_value
			
			p["calculated_stats"] = calculated_stats
			p["max_hp"] = calculated_stats["hp"]
			
			if p["current_hp"] is None:
				p["current_hp"] = calculated_stats["hp"]
			
			return p

	def bulk_update_pokemon(self, owner_id: str, pokemon_ids: List[int], updates: Dict) -> List[Dict]:
		with self._lock:
			self._ensure_user(owner_id)
			updated = []
			
			for pokemon_id in pokemon_ids:
				try:
					idx = self._get_pokemon_index(owner_id, pokemon_id)
					p = self.db["pokemon"][idx]
					
					for key, value in updates.items():
						if key in ["is_favorite", "is_shiny", "on_party"]:
							p[key] = bool(value)
						elif key in ["nickname", "held_item", "background", "nature", "ability", "gender"]:
							p[key] = value
						elif key == "level":
							p[key] = int(value)
					
					updated.append(self._deepcopy(p))
				except ValueError:
					continue
			
			if updated:
				self._save()
			
			return updated

	def search_pokemon(self, user_id: str, query: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			query = query.lower()
			results = []
			
			for p in self.db["pokemon"]:
				if p["owner_id"] != user_id:
					continue
				
				if p.get("name") and query in p["name"].lower():
					results.append(self._deepcopy(p))
					continue
				
				if p.get("nickname") and query in p["nickname"].lower():
					results.append(self._deepcopy(p))
					continue
			
			return results