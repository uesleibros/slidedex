import json
import os
import threading
import copy
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from pokemon_sdk.constants import NATURES, STAT_KEYS, HAPPINESS_MAX, SHINY_ROLL
from pokemon_sdk.calculations import calculate_max_hp, adjust_hp_on_level_up
from helpers.growth import GrowthRate

class FireRedRNG:
    def __init__(self, seed: int):
        self.seed = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.seed = (self.seed * 0x41C64E6D + 0x6073) & 0xFFFFFFFF
        return (self.seed >> 16) & 0xFFFF

    def randint(self, min_val: int, max_val: int) -> int:
        rnd = self.next() / 0xFFFF
        return min_val + int(rnd * (max_val - min_val))
    
    def random(self) -> float:
        return self.next() / 0xFFFF

    def get_seed(self) -> int:
        return self.seed
    
    def set_seed(self, seed: int) -> None:
        self.seed = seed & 0xFFFFFFFF

PARTY_LIMIT = 6
MOVES_LIMIT = 4
EV_PER_STAT_MAX = 255
EV_TOTAL_MAX = 510
HAPPINESS_MIN = 0
MAX_LEVEL = 100
MIN_LEVEL = 1

HAPPINESS_GAINS = {
	"level_up": {
		"low": 5,
		"medium": 3,
		"high": 2
	},
	"vitamin": {
		"low": 5,
		"medium": 3,
		"high": 2
	},
	"berry": {
		"low": 10,
		"medium": 5,
		"high": 2
	},
	"battle": {
		"low": 3,
		"medium": 2,
		"high": 1
	},
	"walk": 1
}

HAPPINESS_LOSSES = {
	"faint": 1,
	"energy_powder": {"low": 5, "high": 10},
	"heal_powder": {"low": 5, "high": 10},
	"energy_root": {"low": 10, "high": 15},
	"revival_herb": {"low": 15, "high": 20}
}

SOOTHE_BELL_MULTIPLIER = 1.5

class Toolkit:
	__slots__ = ('path', '_lock', 'db', '_pk_index', 'NATURES', '_move_service')
	
	def __init__(self, path: str = "database.json"):
		self.path = path
		self._lock = threading.RLock()
		self.db: Dict = {}
		self._pk_index: Dict[Tuple[str, int], int] = {}
		self.NATURES = NATURES
		self._move_service = None
		self._load()

	def set_move_service(self, service) -> None:
		self._move_service = service

	def _load(self) -> None:
		with self._lock:
			if not os.path.exists(self.path):
				self._init_empty_db()
			else:
				self._load_from_file()
			self._reindex()

	def _init_empty_db(self) -> None:
		self.db = {
			"users": {},
			"pokemon": [],
			"bags": [],
			"custom_messages": {}
		}
		self._save()

	def _load_from_file(self) -> None:
		with open(self.path, "r", encoding="utf-8") as f:
			self.db = json.load(f)
		
		if "users" not in self.db:
			self.db["users"] = {}
		if "pokemon" not in self.db:
			self.db["pokemon"] = []
		if "bags" not in self.db or not isinstance(self.db["bags"], list):
			self.db["bags"] = []
		if "custom_messages" not in self.db:
			self.db["custom_messages"] = {}
		
		self._save()

	def _reindex(self) -> None:
		self._pk_index = {}
		for i, p in enumerate(self.db["pokemon"]):
			self._pk_index[(p["owner_id"], int(p["id"]))] = i

	def _save(self) -> None:
		with self._lock:
			tmp = self.path + ".tmp"
			with open(tmp, "w", encoding="utf-8") as f:
				json.dump(self.db, f, indent=2, ensure_ascii=False)
			os.replace(tmp, self.path)

	def _deepcopy(self, obj):
		return copy.deepcopy(obj)

	def clear(self) -> None:
		self._init_empty_db()

	def _ensure_user(self, user_id: str) -> None:
		if user_id not in self.db["users"]:
			raise ValueError("User not found")

	def _get_pokemon_index(self, owner_id: str, pokemon_id: int) -> int:
		idx = self._pk_index.get((owner_id, int(pokemon_id)))
		if idx is None:
			raise ValueError("Pokemon not found")
		return idx

	def _validate_ivs(self, ivs: Dict[str, int]) -> None:
		if set(ivs.keys()) != set(STAT_KEYS):
			raise ValueError("Invalid IV keys")
		for k, v in ivs.items():
			if not isinstance(v, int) or not (0 <= v <= 31):
				raise ValueError(f"Invalid IV value for {k}: {v}")

	def _validate_evs(self, evs: Dict[str, int]) -> None:
		if set(evs.keys()) != set(STAT_KEYS):
			raise ValueError("Invalid EV keys")
		total = sum(evs.values())
		
		for k, v in evs.items():
			if not isinstance(v, int) or not (0 <= v <= EV_PER_STAT_MAX):
				raise ValueError(f"Invalid EV value for {k}: {v}")
		
		if total > EV_TOTAL_MAX:
			raise ValueError(f"EV total ({total}) exceeds limit ({EV_TOTAL_MAX})")

	def _clamp_happiness(self, value: int) -> int:
		return max(HAPPINESS_MIN, min(HAPPINESS_MAX, value))

	def _clamp_level(self, level: int) -> int:
		return max(MIN_LEVEL, min(MAX_LEVEL, level))

	def _has_soothe_bell(self, pokemon: Dict) -> bool:
		return pokemon.get("held_item") == "soothe-bell"

	def _apply_soothe_bell(self, gain: int, has_bell: bool) -> int:
		if has_bell and gain > 0:
			return int(gain * SOOTHE_BELL_MULTIPLIER)
		return gain

	def _get_happiness_tier(self, current: int) -> str:
		if current < 100:
			return "low"
		elif current < 200:
			return "medium"
		else:
			return "high"

	def _get_happiness_gain(self, event_type: str, current: int, has_soothe_bell: bool = False) -> int:
		if event_type == "walk":
			gain = HAPPINESS_GAINS["walk"]
		else:
			tier = self._get_happiness_tier(current)
			gain = HAPPINESS_GAINS[event_type][tier]
		
		return self._apply_soothe_bell(gain, has_soothe_bell)

	def _get_happiness_loss(self, event_type: str, current: int) -> int:
		if event_type == "faint":
			return HAPPINESS_LOSSES["faint"]
		
		tier = "high" if current >= 200 else "low"
		return HAPPINESS_LOSSES[event_type][tier]

	def get_growth_levels(self, growth_type: str, max_level: int = MAX_LEVEL) -> List[Dict]:
		return [
			{"level": level, "experience": GrowthRate.calculate_exp(growth_type, level)}
			for level in range(MIN_LEVEL, max_level + 1)
		]

	def get_exp_for_level(self, growth_type: str, level: int) -> int:
		return GrowthRate.calculate_exp(growth_type, level)

	def get_level_from_exp(self, growth_type: str, experience: int) -> int:
		return GrowthRate.get_level_from_exp(growth_type, experience)

	def get_exp_progress(self, growth_type: str, current_exp: int) -> Dict:
		current_level = self.get_level_from_exp(growth_type, current_exp)
		
		if current_level >= MAX_LEVEL:
			return {
				"current_level": MAX_LEVEL,
				"current_exp": current_exp,
				"exp_for_current": self.get_exp_for_level(growth_type, MAX_LEVEL),
				"exp_for_next": 0,
				"exp_needed": 0,
				"progress_percent": 100.0
			}
		
		exp_for_current = self.get_exp_for_level(growth_type, current_level)
		exp_for_next = self.get_exp_for_level(growth_type, current_level + 1)
		exp_needed = exp_for_next - current_exp
		exp_in_level = current_exp - exp_for_current
		exp_required_for_level = exp_for_next - exp_for_current
		progress = (exp_in_level / exp_required_for_level * 100) if exp_required_for_level > 0 else 0
		
		return {
			"current_level": current_level,
			"current_exp": current_exp,
			"exp_for_current": exp_for_current,
			"exp_for_next": exp_for_next,
			"exp_needed": exp_needed,
			"exp_in_level": exp_in_level,
			"exp_required_for_level": exp_required_for_level,
			"progress_percent": round(progress, 2)
		}

	def calc_battle_exp(self, poke_level: int, enemy_level: int) -> int:
		base = enemy_level * 10
		bonus = max(0, (enemy_level - poke_level) * 5)
		return max(1, base + bonus)

	def add_user(self, user_id: str, gender: str) -> Dict:
		with self._lock:
			if user_id not in self.db["users"]:
				seed = (int(time.time()) + hash(user_id)) & 0xFFFFFFFF
				
				self.db["users"][user_id] = {
					"id": user_id,
					"gender": gender,
					"money": 0,
					"last_pokemon_id": 0,
					"badges": [],
					"rng_seed": seed,
					"created_at": datetime.utcnow().isoformat()
				}
				self._save()
			return self._deepcopy(self.db["users"][user_id])

	def get_user(self, user_id: str) -> Optional[Dict]:
		with self._lock:
			return self._deepcopy(self.db["users"].get(user_id))

	def get_user_rng(self, user_id: str) -> FireRedRNG:
		with self._lock:
			self._ensure_user(user_id)
			seed = self.db["users"][user_id].get("rng_seed")
			if seed is None:
				seed = (int(time.time()) + hash(user_id)) & 0xFFFFFFFF
				self.db["users"][user_id]["rng_seed"] = seed
				self._save()
			return FireRedRNG(seed)

	def save_user_rng(self, user_id: str, rng: FireRedRNG) -> int:
		with self._lock:
			self._ensure_user(user_id)
			current_seed = rng.get_seed()
			self.db["users"][user_id]["rng_seed"] = current_seed
			self._save()
			return current_seed

	def get_user_seed(self, user_id: str) -> int:
		with self._lock:
			self._ensure_user(user_id)
			return self.db["users"][user_id].get("rng_seed", 0)

	def set_user_seed(self, user_id: str, seed: int) -> int:
		with self._lock:
			self._ensure_user(user_id)
			seed = seed & 0xFFFFFFFF
			self.db["users"][user_id]["rng_seed"] = seed
			self._save()
			return seed

	def reset_user_seed(self, user_id: str) -> int:
		new_seed = (int(time.time()) + hash(user_id)) & 0xFFFFFFFF
		return self.set_user_seed(user_id, new_seed)

	def roll_random(self, user_id: str, min_val: int, max_val: int) -> int:
		with self._lock:
			rng = self.get_user_rng(user_id)
			result = rng.randint(min_val, max_val)
			self.save_user_rng(user_id, rng)
			return result

	def roll_chance(self, user_id: str, chance: float) -> bool:
		with self._lock:
			rng = self.get_user_rng(user_id)
			result = rng.random() < chance
			self.save_user_rng(user_id, rng)
			return result

	def roll_shiny(self, user_id: str) -> bool:
		return self.roll_chance(user_id, 1/SHINY_ROLL)

	def roll_ability(self, poke, user_id: str) -> str:
		regular = [a.ability.name for a in poke.abilities if not a.is_hidden]
		if not regular:
			return poke.abilities[0].ability.name
		
		idx = self.roll_random(user_id, 0, len(regular))
		return regular[idx]

	def roll_gender(self, user_id: str, male_ratio: float = 0.5, forced: Optional[str] = None) -> str:
		if forced in ("Male", "Female", "Genderless"):
			return forced
		if male_ratio < 0:
			return "Genderless"
		is_male = self.roll_chance(user_id, male_ratio)
		return "Male" if is_male else "Female"

	def roll_ivs(self, user_id: str) -> Dict[str, int]:
		with self._lock:
			rng = self.get_user_rng(user_id)
			ivs = {stat: rng.randint(0, 32) for stat in STAT_KEYS}
			self.save_user_rng(user_id, rng)
			return ivs

	def roll_nature(self, user_id: str) -> str:
		natures = list(NATURES.keys())
		idx = self.roll_random(user_id, 0, len(natures))
		return natures[idx]

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
			badges = self.db["users"][user_id].setdefault("badges", [])
			if badge not in badges:
				badges.append(badge)
				self._save()
			return list(badges)

	def remove_badge(self, user_id: str, badge: str) -> List[str]:
		with self._lock:
			self._ensure_user(user_id)
			badges = self.db["users"][user_id].setdefault("badges", [])
			if badge in badges:
				badges.remove(badge)
				self._save()
			return list(badges)

	def get_bag(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			return [self._deepcopy(item) for item in self.db["bags"] if item["owner_id"] == user_id]

	def get_item_quantity(self, user_id: str, item_id: str) -> int:
		with self._lock:
			self._ensure_user(user_id)
			for item in self.db["bags"]:
				if item["owner_id"] == user_id and item["item_id"] == item_id:
					return item["quantity"]
			return 0

	def has_item(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
		return self.get_item_quantity(user_id, item_id) >= quantity

	def add_item(self, user_id: str, item_id: str, quantity: int = 1, category: str = "items") -> int:
		with self._lock:
			self._ensure_user(user_id)
			
			for item in self.db["bags"]:
				if item["owner_id"] == user_id and item["item_id"] == item_id:
					item["quantity"] += int(quantity)
					self._save()
					return item["quantity"]
			
			self.db["bags"].append({
				"owner_id": user_id,
				"item_id": item_id,
				"category": category,
				"quantity": int(quantity)
			})
			self._save()
			return int(quantity)

	def remove_item(self, user_id: str, item_id: str, quantity: int = 1) -> int:
		with self._lock:
			self._ensure_user(user_id)
			
			for i, item in enumerate(self.db["bags"]):
				if item["owner_id"] == user_id and item["item_id"] == item_id:
					if item["quantity"] < quantity:
						raise ValueError(f"Not enough items: has {item['quantity']}, needs {quantity}")
					
					item["quantity"] -= int(quantity)
					
					if item["quantity"] <= 0:
						del self.db["bags"][i]
						self._save()
						return 0
					
					self._save()
					return item["quantity"]
			
			raise ValueError(f"Item not found: {item_id}")

	def set_item_quantity(self, user_id: str, item_id: str, quantity: int, category: str = "items") -> int:
		with self._lock:
			self._ensure_user(user_id)
			
			if quantity <= 0:
				for i, item in enumerate(self.db["bags"]):
					if item["owner_id"] == user_id and item["item_id"] == item_id:
						del self.db["bags"][i]
						break
				self._save()
				return 0
			
			for item in self.db["bags"]:
				if item["owner_id"] == user_id and item["item_id"] == item_id:
					item["quantity"] = int(quantity)
					self._save()
					return item["quantity"]
			
			self.db["bags"].append({
				"owner_id": user_id,
				"item_id": item_id,
				"category": category,
				"quantity": int(quantity)
			})
			self._save()
			return int(quantity)

	def clear_bag(self, user_id: str) -> None:
		with self._lock:
			self._ensure_user(user_id)
			self.db["bags"] = [item for item in self.db["bags"] if item["owner_id"] != user_id]
			self._save()

	def count_items(self, user_id: str) -> int:
		with self._lock:
			self._ensure_user(user_id)
			return sum(item["quantity"] for item in self.db["bags"] if item["owner_id"] == user_id)

	def count_unique_items(self, user_id: str) -> int:
		with self._lock:
			self._ensure_user(user_id)
			return len([item for item in self.db["bags"] if item["owner_id"] == user_id])

	def transfer_item(self, from_user_id: str, to_user_id: str, item_id: str, quantity: int = 1) -> Tuple[int, int]:
		with self._lock:
			self._ensure_user(from_user_id)
			self._ensure_user(to_user_id)
			
			from_qty = self.remove_item(from_user_id, item_id, quantity)
			to_qty = self.add_item(to_user_id, item_id, quantity)
			
			return (from_qty, to_qty)

	def add_pokemon(
		self,
		owner_id: str,
		species_id: int,
		ivs: Dict[str, int],
		nature: str,
		ability: str,
		gender: str,
		shiny: bool,
		types: List[str],
		region: str,
		is_legendary: bool,
		is_mythical: bool,
		growth_type: str,
		happiness: int,
		base_stats: Dict,
		level: int = 1,
		exp: int = 0,
		held_item: Optional[str] = None,
		moves: Optional[List[Dict]] = None,
		status: Optional[dict] = None,
		nickname: Optional[str] = None,
		name: Optional[str] = None,
		current_hp: Optional[int] = None,
		on_party: Optional[bool] = None
	) -> Dict:
		with self._lock:
			self._ensure_user(owner_id)
			self._validate_ivs(ivs)
			
			status = status or {"name": None, "counter": 0}
			base_evs = {k: 0 for k in STAT_KEYS}
			auto_party = self.get_party_count(owner_id) < PARTY_LIMIT
			final_on_party = auto_party if on_party is None else (on_party and auto_party)
			
			user = self.db["users"][owner_id]
			user["last_pokemon_id"] += 1
			new_id = user["last_pokemon_id"]
			
			final_level = self._clamp_level(int(level))
			max_exp = self.get_exp_for_level(growth_type, MAX_LEVEL)
			final_exp = min(int(exp), max_exp)
			
			pkmn = {
				"id": int(new_id),
				"species_id": int(species_id),
				"nickname": nickname,
				"name": name,
				"owner_id": owner_id,
				"level": final_level,
				"exp": final_exp,
				"ivs": ivs,
				"evs": base_evs,
				"nature": nature,
				"ability": ability,
				"types": types,
				"is_legendary": is_legendary,
				"is_mythical": is_mythical,
				"base_stats": base_stats,
				"region": region,
				"gender": gender,
				"is_shiny": bool(shiny),
				"growth_type": growth_type,
				"happiness": self._clamp_happiness(int(happiness)),
				"background": "lab",
				"held_item": held_item,
				"is_favorite": False,
				"caught_at": datetime.utcnow().isoformat(),
				"moves": [],
				"status": status,
				"current_hp": current_hp if current_hp is None else int(current_hp),
				"on_party": final_on_party,
				"evolution_blocked": False
			}
			
			if moves:
				if len(moves) > MOVES_LIMIT:
					raise ValueError(f"Too many moves: {len(moves)}/{MOVES_LIMIT}")
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
				raise ValueError(f"Party is full ({PARTY_LIMIT}/{PARTY_LIMIT})")
			
			self.db["pokemon"][idx]["on_party"] = True
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def move_to_box(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["on_party"] = False
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def reorder_party(self, owner_id: str, order: List[int]) -> List[Dict]:
		with self._lock:
			self._ensure_user(owner_id)
			party = [p for p in self.db["pokemon"] if p["owner_id"] == owner_id and p.get("on_party", False)]
			
			if not party:
				return []
			
			current_ids = [int(p["id"]) for p in party]
			
			if len(order) != len(current_ids):
				raise ValueError(f"Order length mismatch: got {len(order)}, expected {len(current_ids)}")
			
			if set(order) != set(current_ids):
				raise ValueError("Order IDs don't match current party")
			
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
				raise ValueError(f"Invalid positions: {a}, {b} (party size: {len(party)})")
			
			ids = [int(p["id"]) for p in party]
			ids[a-1], ids[b-1] = ids[b-1], ids[a-1]
			
			return self.reorder_party(owner_id, ids)

	def set_level(self, owner_id: str, pokemon_id: int, level: int) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["level"] = self._clamp_level(int(level))
			self._save()
			return self.db["pokemon"][idx]["level"]

	def add_exp(self, owner_id: str, pokemon_id: int, exp_gain: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			
			old_level = p["level"]
			growth_type = p.get("growth_type", GrowthRate.MEDIUM)
			max_exp = self.get_exp_for_level(growth_type, MAX_LEVEL)
			
			if old_level >= MAX_LEVEL:
				p["exp"] = max_exp
				p["level"] = MAX_LEVEL
				self._save()
				
				result = self._deepcopy(p)
				result["levels_gained"] = []
				result["old_level"] = old_level
				result["max_level_reached"] = True
				return result
			
			p["exp"] = min(p["exp"] + int(exp_gain), max_exp)
			new_level = min(self.get_level_from_exp(growth_type, p["exp"]), MAX_LEVEL)
			
			levels_gained = []
			
			if new_level > old_level:
				for lvl in range(old_level + 1, min(new_level + 1, MAX_LEVEL + 1)):
					levels_gained.append(lvl)
					
					current_happiness = p.get("happiness", 70)
					gain = self._get_happiness_gain("level_up", current_happiness, self._has_soothe_bell(p))
					p["happiness"] = self._clamp_happiness(current_happiness + gain)
				
				old_max_hp = calculate_max_hp(
					p["base_stats"]["hp"],
					p["ivs"]["hp"],
					p["evs"]["hp"],
					old_level
				)
				
				new_max_hp = calculate_max_hp(
					p["base_stats"]["hp"],
					p["ivs"]["hp"],
					p["evs"]["hp"],
					new_level
				)
				
				current_hp = p.get("current_hp")
				if current_hp is None:
					current_hp = old_max_hp
				
				p["current_hp"] = adjust_hp_on_level_up(old_max_hp, new_max_hp, current_hp)
				p["level"] = new_level
				
				if new_level >= MAX_LEVEL:
					p["exp"] = max_exp
			
			self._save()
			
			result = self._deepcopy(p)
			result["levels_gained"] = levels_gained
			result["old_level"] = old_level
			result["max_level_reached"] = new_level >= MAX_LEVEL
			return result

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

	def set_pokemon_held_item(self, owner_id: str, pokemon_id: int, item: Optional[str]) -> Optional[str]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["held_item"] = item
			self._save()
			return item

	def set_held_item(self, owner_id: str, pokemon_id: int, item: Optional[str]) -> Optional[str]:
		return self.set_pokemon_held_item(owner_id, pokemon_id, item)

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

	def set_status(self, owner_id: str, pokemon_id: int, status_name: Optional[str], counter: int = 0) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["status"] = {
				"name": status_name,
				"counter": int(counter)
			}
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def clear_pokemon_status(self, owner_id: str, pokemon_id: int) -> Dict:
		return self.set_status(owner_id, pokemon_id, None, 0)

	def set_types(self, owner_id: str, pokemon_id: int, types: List[str]) -> List[str]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["types"] = types
			self._save()
			return types

	def set_moves(self, owner_id: str, pokemon_id: int, moves: List[Dict]) -> List[Dict]:
		with self._lock:
			if len(moves) > MOVES_LIMIT:
				raise ValueError(f"Too many moves: {len(moves)}/{MOVES_LIMIT}")
			
			for m in moves:
				if not isinstance(m, dict) or "id" not in m or "pp" not in m or "pp_max" not in m:
					raise ValueError("Invalid move shape")
			
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["moves"] = moves
			self._save()
			return self._deepcopy(self.db["pokemon"][idx]["moves"])

	def can_learn_move(self, owner_id: str, pokemon_id: int) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			return len(p.get("moves", [])) < MOVES_LIMIT

	def learn_move(self, owner_id: str, pokemon_id: int, move_id: str, pp_max: int, replace_move_id: Optional[str] = None) -> List[Dict]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			
			if "moves" not in p:
				p["moves"] = []
			
			if replace_move_id:
				p["moves"] = [m for m in p["moves"] if m["id"] != replace_move_id]
			
			if any(m["id"] == move_id for m in p["moves"]):
				return self._deepcopy(p["moves"])
			
			if len(p["moves"]) >= MOVES_LIMIT:
				raise ValueError(f"Move slots full ({MOVES_LIMIT}/{MOVES_LIMIT})")
			
			p["moves"].append({
				"id": move_id,
				"pp": int(pp_max),
				"pp_max": int(pp_max)
			})
			
			self._save()
			return self._deepcopy(p["moves"])

	def has_move(self, owner_id: str, pokemon_id: int, move_id: str) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			moves = self.db["pokemon"][idx].get("moves", [])
			return any(m["id"] == move_id for m in moves)

	def add_move(self, owner_id: str, pokemon_id: int, move_id: str, pp: int, pp_max: int) -> List[Dict]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			mv = self.db["pokemon"][idx]["moves"]
			
			if len(mv) >= MOVES_LIMIT:
				raise ValueError(f"Move slots full ({MOVES_LIMIT}/{MOVES_LIMIT})")
			
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
				raise ValueError(f"Move not found: {move_id}")
			
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def restore_pp(self, owner_id: str, pokemon_id: int) -> List[Dict]:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			for m in self.db["pokemon"][idx]["moves"]:
				m["pp"] = int(m["pp_max"])
			self._save()
			return self._deepcopy(self.db["pokemon"][idx]["moves"])

	def heal_pokemon(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			
			p["current_hp"] = calculate_max_hp(
				p["base_stats"]["hp"],
				p["ivs"]["hp"],
				p["evs"]["hp"],
				p["level"]
			)
			
			for move in p.get("moves", []):
				move["pp"] = move["pp_max"]
			
			p["status"] = {"name": None, "counter": 0}
			
			self._save()
			return self._deepcopy(p)

	def heal_party(self, owner_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(owner_id)
			healed = []
			
			for p in self.db["pokemon"]:
				if p["owner_id"] == owner_id and p.get("on_party", False):
					p["current_hp"] = calculate_max_hp(
						p["base_stats"]["hp"],
						p["ivs"]["hp"],
						p["evs"]["hp"],
						p["level"]
					)
					
					for move in p.get("moves", []):
						move["pp"] = move["pp_max"]
					
					p["status"] = {"name": None, "counter": 0}
					
					healed.append(self._deepcopy(p))
			
			self._save()
			return healed

	def transfer_pokemon(self, owner_id: str, pokemon_id: int, new_owner_id: str) -> Dict:
		with self._lock:
			self._ensure_user(new_owner_id)
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			
			if (new_owner_id, pokemon_id) in self._pk_index:
				new_owner = self.db["users"][new_owner_id]
				new_owner["last_pokemon_id"] += 1
				new_id = new_owner["last_pokemon_id"]
				
				del self._pk_index[(owner_id, pokemon_id)]
				
				p["id"] = new_id
				p["owner_id"] = new_owner_id
				
				self._pk_index[(new_owner_id, new_id)] = idx
			else:
				del self._pk_index[(owner_id, pokemon_id)]
				p["owner_id"] = new_owner_id
				
				new_owner = self.db["users"][new_owner_id]
				if pokemon_id > new_owner["last_pokemon_id"]:
					new_owner["last_pokemon_id"] = pokemon_id
				
				self._pk_index[(new_owner_id, pokemon_id)] = idx
			
			p["happiness"] = 70
			
			if p.get("on_party", False) and not self.can_add_to_party(new_owner_id):
				p["on_party"] = False
			
			self._save()
			return self._deepcopy(p)

	def release_pokemon(self, owner_id: str, pokemon_id: int) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			del self.db["pokemon"][idx]
			self._reindex()
			self._save()
			return True

	def block_evolution(self, owner_id: str, pokemon_id: int, block: bool = True) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["evolution_blocked"] = bool(block)
			self._save()
			return self.db["pokemon"][idx]["evolution_blocked"]

	def is_evolution_blocked(self, owner_id: str, pokemon_id: int) -> bool:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			return self.db["pokemon"][idx].get("evolution_blocked", False)

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

	def get_happiness(self, owner_id: str, pokemon_id: int) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			return self.db["pokemon"][idx].get("happiness", 70)

	def set_happiness(self, owner_id: str, pokemon_id: int, value: int) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["happiness"] = self._clamp_happiness(int(value))
			self._save()
			return self.db["pokemon"][idx]["happiness"]

	def modify_happiness(self, owner_id: str, pokemon_id: int, amount: int) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			current = p.get("happiness", 70)
			p["happiness"] = self._clamp_happiness(current + int(amount))
			self._save()
			return p["happiness"]

	def _modify_happiness_by_event(self, owner_id: str, pokemon_id: int, event_type: str, is_gain: bool = True) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self.db["pokemon"][idx]
			current = p.get("happiness", 70)
			
			if is_gain:
				change = self._get_happiness_gain(event_type, current, self._has_soothe_bell(p))
				p["happiness"] = self._clamp_happiness(current + change)
			else:
				change = self._get_happiness_loss(event_type, current)
				p["happiness"] = self._clamp_happiness(current - change)
			
			self._save()
			return p["happiness"]

	def increase_happiness_level_up(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "level_up", is_gain=True)

	def increase_happiness_vitamin(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "vitamin", is_gain=True)

	def increase_happiness_berry(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "berry", is_gain=True)

	def increase_happiness_walk(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "walk", is_gain=True)

	def increase_happiness_battle(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "battle", is_gain=True)

	def decrease_happiness_faint(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "faint", is_gain=False)

	def decrease_happiness_energy_powder(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "energy_powder", is_gain=False)

	def decrease_happiness_heal_powder(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "heal_powder", is_gain=False)

	def decrease_happiness_energy_root(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "energy_root", is_gain=False)

	def decrease_happiness_revival_herb(self, owner_id: str, pokemon_id: int) -> int:
		return self._modify_happiness_by_event(owner_id, pokemon_id, "revival_herb", is_gain=False)

	def iv_total(self, owner_id: str, pokemon_id: int) -> int:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			return sum(self.db["pokemon"][idx]["ivs"].values())

	def iv_percent(self, owner_id: str, pokemon_id: int, decimals: int = 2) -> float:
		total = self.iv_total(owner_id, pokemon_id)
		return round((total / 186) * 100.0, decimals)

	def update_pokemon_stats(self, owner_id: str, pokemon_id: int, stats: Dict) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			self.db["pokemon"][idx]["stats"] = stats
			self._save()
			return self._deepcopy(self.db["pokemon"][idx])

	def get_pokemon_summary(self, owner_id: str, pokemon_id: int) -> Dict:
		with self._lock:
			idx = self._get_pokemon_index(owner_id, pokemon_id)
			p = self._deepcopy(self.db["pokemon"][idx])
			
			p["iv_total"] = sum(p["ivs"].values())
			p["iv_percent"] = round((p["iv_total"] / 186) * 100.0, 2)
			p["ev_total"] = sum(p["evs"].values())
			
			level = p["level"]
			nature_mod = self.NATURES.get(p["nature"], {})
			
			calculated_stats = {}
			for stat in STAT_KEYS:
				base = p["base_stats"].get(stat, 0)
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
			
			growth_type = p.get("growth_type", GrowthRate.MEDIUM)
			p["exp_progress"] = self.get_exp_progress(growth_type, p.get("exp", 0))
			
			return p

	def get_favorites(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			return [
				self._deepcopy(p) for p in self.db["pokemon"]
				if p["owner_id"] == user_id and p.get("is_favorite", False)
			]

	def get_pokemon_by_species(self, user_id: str, species_id: int) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			return [
				self._deepcopy(p) for p in self.db["pokemon"]
				if p["owner_id"] == user_id and p["species_id"] == species_id
			]

	def get_shiny_pokemon(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			return [
				self._deepcopy(p) for p in self.db["pokemon"]
				if p["owner_id"] == user_id and p.get("is_shiny", False)
			]

	def get_legendary_pokemon(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			return [
				self._deepcopy(p) for p in self.db["pokemon"]
				if p["owner_id"] == user_id and p.get("is_legendary", False)
			]

	def get_mythical_pokemon(self, user_id: str) -> List[Dict]:
		with self._lock:
			self._ensure_user(user_id)
			return [
				self._deepcopy(p) for p in self.db["pokemon"]
				if p["owner_id"] == user_id and p.get("is_mythical", False)
			]

	def get_pokemon_count(self, user_id: str) -> Dict[str, int]:
		with self._lock:
			self._ensure_user(user_id)
			
			counts = {
				"total": 0,
				"party": 0,
				"box": 0,
				"favorites": 0,
				"shiny": 0,
				"legendary": 0,
				"mythical": 0
			}
			
			for p in self.db["pokemon"]:
				if p["owner_id"] != user_id:
					continue
				
				counts["total"] += 1
				
				if p.get("on_party", False):
					counts["party"] += 1
				else:
					counts["box"] += 1
				
				if p.get("is_favorite", False):
					counts["favorites"] += 1
				if p.get("is_shiny", False):
					counts["shiny"] += 1
				if p.get("is_legendary", False):
					counts["legendary"] += 1
				if p.get("is_mythical", False):
					counts["mythical"] += 1
			
			return counts

	def has_caught_species(self, user_id: str, species_id: int) -> bool:
		with self._lock:
			self._ensure_user(user_id)
			return any(
				p["owner_id"] == user_id and p["species_id"] == int(species_id)
				for p in self.db["pokemon"]
			)

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

	def bulk_update_pokemon(self, owner_id: str, pokemon_ids: List[int], updates: Dict) -> List[Dict]:
		with self._lock:
			self._ensure_user(owner_id)
			updated = []
			
			allowed_keys = {
				"is_favorite", "is_shiny", "on_party",
				"nickname", "held_item", "background",
				"nature", "ability", "gender", "level"
			}
			
			for pokemon_id in pokemon_ids:
				try:
					idx = self._get_pokemon_index(owner_id, pokemon_id)
					p = self.db["pokemon"][idx]
					
					for key, value in updates.items():
						if key not in allowed_keys:
							continue
						
						if key in ["is_favorite", "is_shiny", "on_party"]:
							p[key] = bool(value)
						elif key == "level":
							p[key] = self._clamp_level(int(value))
						else:
							p[key] = value
					
					updated.append(self._deepcopy(p))
				except ValueError:
					continue
			
			if updated:
				self._save()
			
			return updated






