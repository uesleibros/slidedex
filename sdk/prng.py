from typing import Final

FIRERED_MULTIPLIER: Final[int] = 0x41C64E6D
FIRERED_INCREMENT: Final[int] = 0x6073
UINT32_MAX: Final[int] = 0xFFFFFFFF

class PRNG:
	__slots__ = ("_seed",)
	
	def __init__(self, seed: int):
		self._seed = seed & UINT32_MAX
	
	def next(self) -> int:
		self._seed = (self._seed * FIRERED_MULTIPLIER + FIRERED_INCREMENT) & UINT32_MAX
		return (self._seed >> 16) & 0xFFFF
	
	def randint(self, min_val: int, max_val: int) -> int:
		rnd = self.next() / 0xFFFF
		return min_val + int(rnd * (max_val - min_val))
	
	def random(self) -> float:
		return self.next() / 0xFFFF
	
	def get_seed(self) -> int:
		return self._seed
	
	def set_seed(self, seed: int) -> None:
		self._seed = seed & UINT32_MAX