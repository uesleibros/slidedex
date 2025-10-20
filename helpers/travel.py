from datetime import datetime
from zoneinfo import ZoneInfo

def format_time_remaining(seconds: float) -> str:
	if seconds <= 0:
		return "Concluído"
	
	minutes = int(seconds // 60)
	secs = int(seconds % 60)
	
	if minutes > 0:
		return f"{minutes}min {secs}s"
	return f"{secs}s"

def get_progress_bar(current: float, total: float, length: int = 15) -> str:
	if total <= 0:
		return "█" * length
	
	filled = int((current / total) * length)
	empty = length - filled
	
	return "█" * filled + "░" * empty

def calculate_travel_progress(started_at: str, ends_at: str) -> dict:
	now = datetime.now(ZoneInfo("UTC"))
	started = datetime.fromisoformat(started_at)
	ends = datetime.fromisoformat(ends_at)
	
	total = (ends - started).total_seconds()
	elapsed = (now - started).total_seconds()
	remaining = max(0, (ends - now).total_seconds())
	
	percentage = min(100, (elapsed / total * 100)) if total > 0 else 100
	
	return {
		"total": total,
		"elapsed": elapsed,
		"remaining": remaining,
		"percentage": percentage,
		"completed": now >= ends
	}