import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
	token: str
	prefix: str = "."
	
	@classmethod
	def from_env(cls) -> "Config":
		token: Optional[str] = os.getenv("DISCORD_TOKEN")
		if not token:
			raise ValueError("DISCORD_TOKEN not found in environment")
		return cls(token=token)