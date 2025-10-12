import discord
from discord.ext import commands
from typing import List, Mapping, Optional
from helpers.paginator import PaginatorView

class CustomHelpCommand(commands.HelpCommand):
    ITEMS_PER_PAGE = 5
    COLOR = discord.Color.pink()
    
    def get_command_signature(self, command: commands.Command) -> str:
        signature = getattr(command, "signature", '')
        return f'{self.context.clean_prefix}{command.qualified_name} {signature}'
    
    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]) -> None:
        categories = self._build_categories(mapping)
        embeds = self._create_category_embeds(categories)
        await self._send_embeds(embeds)
    
    def _build_categories(self, mapping: Mapping) -> dict:
        categories = {}
        
        for cog, cmds in mapping.items():
            if not cmds:
                continue
            
            if cog and getattr(cog, "hidden", False):
                continue
            
            cog_name = cog.qualified_name if cog else "Sem Categoria"
            categories[cog_name] = [cmd for cmd in cmds if not cmd.hidden]
        
        return categories
    
    def _create_category_embeds(self, categories: dict) -> List[discord.Embed]:
        embeds = []
        cog_items = list(categories.items())
        total_pages = (len(cog_items) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
        
        for page in range(total_pages):
            embed = self._create_category_page_embed(page, total_pages, cog_items)
            embeds.append(embed)
        
        return embeds
    
    def _create_category_page_embed(self, page: int, total_pages: int, cog_items: list) -> discord.Embed:
        embed = discord.Embed(
            title=f"Categorias de Comandos (Página {page + 1}/{total_pages})",
            description=(
                f"Use `{self.context.clean_prefix}help <comando>` para mais info.\n"
                f"Use `{self.context.clean_prefix}help <categoria>` para mais info sobre uma categoria."
            ),
            color=self.COLOR
        )
        
        start = page * self.ITEMS_PER_PAGE
        end = start + self.ITEMS_PER_PAGE
        
        for cog_name, cmds in cog_items[start:end]:
            cog_obj = self.context.bot.get_cog(cog_name)
            description = cog_obj.description if cog_obj and cog_obj.description else "Sem descrição"
            commands_list = " ".join([cmd.name for cmd in cmds])
            
            embed.add_field(
                name=f"**{cog_name}**",
                value=f"{description}\n`{commands_list}`",
                inline=False
            )
        
        return embed
    
    async def send_cog_help(self, cog: commands.Cog) -> None:
        embed = discord.Embed(
            title=f"Categoria: {cog.qualified_name}",
            description=cog.description or "Sem descrição",
            color=self.COLOR
        )
        
        commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
        
        if commands_list:
            commands_text = "\n".join([
                f"`{self.get_command_signature(cmd)}`\n{cmd.short_doc or 'Sem descrição'}"
                for cmd in commands_list
            ])
            embed.add_field(name="Comandos", value=commands_text, inline=False)
        
        await self.get_destination().send(embed=embed)
    
    async def send_command_help(self, command: commands.Command) -> None:
        help_text = command.help or "Sem descrição"
        
        if len(help_text) > 4000:
            embeds = self._create_long_help_embeds(command, help_text)
        else:
            embeds = [self._create_command_embed(command, help_text)]
        
        await self._send_embeds(embeds)
    
    def _create_long_help_embeds(self, command: commands.Command, help_text: str) -> List[discord.Embed]:
        embeds = []
        chunks = self._split_help_text(help_text)
        
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"{self.get_command_signature(command)} (Página {i+1}/{len(chunks)})",
                description=chunk,
                color=self.COLOR
            )
            
            if i == 0 and command.aliases:
                self._add_aliases_field(embed, command.aliases)
            
            embeds.append(embed)
        
        return embeds
    
    def _split_help_text(self, text: str, max_length: int = 4000) -> List[str]:
        chunks = []
        current_chunk = ""
        
        for line in text.split('\n'):
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _create_command_embed(self, command: commands.Command, help_text: str) -> discord.Embed:
        embed = discord.Embed(
            title=self.get_command_signature(command),
            description=help_text,
            color=self.COLOR
        )
        
        if command.aliases:
            self._add_aliases_field(embed, command.aliases)
        
        return embed
    
    def _add_aliases_field(self, embed: discord.Embed, aliases: List[str]) -> None:
        embed.add_field(
            name="Aliases",
            value=", ".join([f"`{alias}`" for alias in aliases]),
            inline=False
        )
    
    async def send_group_help(self, group: commands.Group) -> None:
        subcommands = [cmd for cmd in group.commands if not cmd.hidden]
        embeds = self._create_group_embeds(group, subcommands)
        await self._send_embeds(embeds)
    
    def _create_group_embeds(self, group: commands.Group, subcommands: List[commands.Command]) -> List[discord.Embed]:
        embeds = []
        total_pages = (len(subcommands) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE if subcommands else 1
        
        for page in range(total_pages):
            embed = self._create_group_page_embed(group, subcommands, page, total_pages)
            embeds.append(embed)
        
        return embeds
    
    def _create_group_page_embed(self, group: commands.Group, subcommands: List[commands.Command], page: int, total_pages: int) -> discord.Embed:
        help_text = group.help or "Sem descrição"
        
        if len(help_text) > 2000:
            help_text = help_text[:1997] + "..."
        
        embed = discord.Embed(
            title=self.get_command_signature(group),
            description=help_text,
            color=self.COLOR
        )
        
        if group.aliases:
            self._add_aliases_field(embed, group.aliases)
        
        if subcommands:
            self._add_subcommands_field(embed, subcommands, page, total_pages)
        
        return embed
    
    def _add_subcommands_field(self, embed: discord.Embed, subcommands: List[commands.Command], page: int, total_pages: int) -> None:
        start = page * self.ITEMS_PER_PAGE
        end = start + self.ITEMS_PER_PAGE
        page_subcommands = subcommands[start:end]
        
        subcommands_text = "\n".join([
            f"`{self.get_command_signature(cmd)}`\n{cmd.short_doc or 'Sem descrição'}"
            for cmd in page_subcommands
        ])
        
        if len(subcommands_text) > 1000:
            subcommands_text = "\n".join([
                f"`{self.get_command_signature(cmd)}`"
                for cmd in page_subcommands
            ])
        
        embed.add_field(
            name=f"Subcomandos (Página {page + 1}/{total_pages})",
            value=subcommands_text,
            inline=False
        )
    
    async def _send_embeds(self, embeds: List[discord.Embed]) -> None:
        if len(embeds) == 1:
            await self.get_destination().send(embed=embeds[0])
        else:
            view = PaginatorView(embeds, self.context.author)
            await self.get_destination().send(embed=embeds[0], view=view)