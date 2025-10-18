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
| `location-area.json` | Lista das Áreas  da Gen III, contendo os Pokémon que pode aparecer, método de encontro, e chance de aparecer. |

## Padrões Técnicos

- Todos os arquivos estão no formato **JSON** e codificados em **UTF-8**.
- A estrutura segue o formato **simplificado e limpo**, removendo campos redundantes da PokéAPI para reduzir o tamanho final dos dados.
- Cada arquivo é uma **lista de objetos JSON** (`[ {...}, {...}, ... ]`) para permitir leitura com baixo uso de memória (via [`orjson`](https://pypi.org/project/orjson/)).
- Apenas as **versões de jogos da Geração III** são consideradas (Ruby/Sapphire, FireRed/LeafGreen, Emerald).

## Versão e Atualização

- Versão dos dados: 1.0.1

- Base: PokéAPI

## Licença

Os dados originais pertencem à PokéAPI.
Os arquivos neste diretório são redistribuídos apenas para uso interno e seguem as diretrizes de atribuição e uso não comercial.
