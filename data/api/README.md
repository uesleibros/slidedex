# API Data

Este diretório contém os **dados processados da PokéAPI**, otimizados para uso interno no bot e nos serviços do projeto.  
Os arquivos foram extraídos e filtrados para incluir **apenas informações relevantes até a Geração III (Kanto, Johto e Hoenn)**, garantindo leveza e alto desempenho em leitura.

## Estrutura de Arquivos

| Arquivo | Descrição |
|----------|------------|
| `pokemon.json` | Dados essenciais de todos os Pokémon da Geração III (stats, tipos, habilidades, moves válidos da Gen III, etc). |
| `pokemon-species.json` | Dados complementares de espécies (gênero, taxa de captura, crescimento, cadeia evolutiva, etc). |
| `evolution-chains.json` | Estrutura completa de evolução, mapeando todas as linhas evolutivas da Gen III. |
| `moves.json` | Lista de golpes disponíveis até a Geração III, incluindo poder, precisão, tipo e método de aprendizado. |
| `items.json` | Itens relevantes da Gen III, com foco em Poké Balls, berries e itens de batalha. |

## Padrões Técnicos

- Todos os arquivos estão no formato **JSON** e codificados em **UTF-8**.
- A estrutura segue o formato **simplificado e limpo**, removendo campos redundantes da PokéAPI para reduzir o tamanho final dos dados.
- Cada arquivo é uma **lista de objetos JSON** (`[ {...}, {...}, ... ]`) para permitir leitura **streaming** com baixo uso de memória (via [`ijson`](https://pypi.org/project/ijson/)).
- Apenas as **versões de jogos da Geração III** são consideradas (Ruby/Sapphire, FireRed/LeafGreen, Emerald).

## Uso Recomendado

Para leitura eficiente dos dados:

```python
import ijson

with open("data/api/pokemon.json", "r", encoding="utf-8") as f:
	for pokemon in ijson.items(f, "item"):
		if pokemon["id"] == 257:
			print(pokemon["name"])  # blaziken
			break
```

Este método processa o JSON sem carregá-lo totalmente na RAM, ideal para ambientes com memória limitada (ex: 350MB).

## Versão e Atualização

- Versão dos dados: 1.0.0

- Base: PokéAPI — dump completo processado em modo assíncrono com curl_cffi e asyncio.

## Licença

Os dados originais pertencem à PokéAPI.
Os arquivos neste diretório são redistribuídos apenas para uso interno e seguem as diretrizes de atribuição e uso não comercial.

> 🔧 Nota: Todos os JSONs foram compactados e normalizados para máxima performance de leitura dentro do servidor.
Caso precise regenerar os arquivos ou incluir futuras gerações, utilize os scripts do módulo PokeAPIService.
