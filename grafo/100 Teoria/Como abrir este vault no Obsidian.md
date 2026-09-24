---
tipo: guia
tags: [guia, obsidian]
---
# Como abrir este vault no Obsidian

1. Obsidian → **Open folder as vault** → a pasta `grafo/` deste projeto
   (ex.: `<pasta-do-clone>/grafo`; no Windows, `…\onde-a-internet-mora\grafo`)
2. Abra a nota [[Índice do grafo]] (pasta `000 HUB`).
3. Graph View (`Ctrl+G`): as cores já vêm configuradas em `.obsidian/graph.json`.

## Filtros prontos (cole na busca do Graph View)

| filtro | efeito |
|---|---|
| `tag:#camada/5` | só endereços IP |
| `tag:#camada/6` | rede (ASN, PoPs) |
| `tag:#geo/pais` | países |
| `-tag:#no/ip -tag:#geo/cidade` | só infraestrutura de nomes |
| `path:"400 Redes"` | apenas ASNs |
| `tag:#geo/br` | tudo geolocalizado no Brasil |

## Ajustes úteis

- Graph View → *Forces*: **Link distance 180**, **Repel 12** — separa os clusters de
  cidade dos nameservers.
- *Filters* → desmarque `Attachments` e `Existing files only` se quiser ver o grafo puro.
- Arquivos muito conectados (`data`, `README`) ficam de fora do vault de propósito.
