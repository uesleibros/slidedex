from typing import Any, Callable, TypeVar, Optional
from discord.ext import commands, flags
from discord.ext.flags import FlagCommand as BaseFlagCommand, add_flag

CommandT = TypeVar('CommandT', bound=commands.Command)

class CustomFlagCommand(BaseFlagCommand):
	@property
	def signature(self) -> str:
		if self.usage is not None:
			return self.usage
		
		params = self.clean_params
		if not params:
			return ""
		
		return " ".join(self._build_param_signatures(params))
	
	def _build_param_signatures(self, params: dict) -> list[str]:
		signatures = []
		
		for name, param in params.items():
			signature = self._format_param_signature(name, param)
			if signature:
				signatures.append(signature)
		
		return signatures
	
	def _format_param_signature(self, name: str, param: commands.Parameter) -> Optional[str]:
		if param.kind == param.VAR_KEYWORD:
			return None
		
		is_greedy = isinstance(param.annotation, commands.converter.Greedy)
		
		if param.default is not param.empty:
			return self._format_optional_param(name, param.default, is_greedy)
		
		if param.kind == param.VAR_POSITIONAL:
			return f"[{name}...]"
		
		if is_greedy:
			return f"[{name}]..."
		
		if self._is_typing_optional(param.annotation):
			return f"[{name}]"
		
		return f"<{name}>"
	
	def _format_optional_param(self, name: str, default: Any, is_greedy: bool) -> str:
		should_show_default = isinstance(default, str) or default is not None
		
		if not should_show_default:
			return f"[{name}]"
		
		suffix = "..." if is_greedy else ""
		return f"[{name}={default}]{suffix}"

def flag_command(
	name: Optional[str] = None,
	**attrs: Any
) -> Callable[[Callable], CustomFlagCommand]:
	attrs.setdefault("cls", CustomFlagCommand)
	
	def decorator(func: Callable) -> CustomFlagCommand:
		if name is not None:
			attrs["name"] = name
		
		cls = attrs.pop("cls", CustomFlagCommand)
		return cls(func, **attrs)
	
	return decorator

__all__ = (
	"CustomFlagCommand",
	"flag_command",
	"add_flag",
)