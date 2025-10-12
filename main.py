import asyncio
import logging
import sys
from core.bot import PokemonBot
from core.config import Config

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)

logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def main() -> None:
	config = Config.from_env()
	bot = PokemonBot(config)
	asyncio.run(bot.start(config.token))

if __name__ == "__main__":
	main()