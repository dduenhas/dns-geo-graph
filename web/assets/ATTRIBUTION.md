# Créditos, licenças e atribuições de terceiros

Este repositório redistribui material de terceiros. As licenças originais estão
preservadas abaixo ou nos arquivos indicados.

## Código do projeto

MIT — ver [`LICENSE`](../LICENSE) na raiz.

## three.js r0.169 (`web/vendor/three/`)

- Copyright © 2010–2024 Three.js Authors
- Licença: **MIT** — texto completo em [`../vendor/three/LICENSE.txt`](../vendor/three/LICENSE.txt)
- Origem: <https://github.com/mrdoob/three.js> (build `three.module.min.js` + `examples/jsm` addons)

## Fontes (`web/assets/fonts/`)

Servidas localmente, obtidas do Google Fonts via `scripts/09_fetch_fonts.py`.

| família | autoria | licença |
|---|---|---|
| Inter Tight | Rasmus Andersson | SIL Open Font License 1.1 |
| Inter | Rasmus Andersson | SIL Open Font License 1.1 |
| JetBrains Mono | JetBrains | SIL Open Font License 1.1 |

Texto da OFL em [`fonts/LICENSE.txt`](fonts/LICENSE.txt).

## Máscaras cartográficas (`web/assets/earth-*.png`, `earth-dark.jpg`)

Derivadas de dados de domínio público:

- **Natural Earth** (naturalearthdata.com) — domínio público;
- **NASA Visible Earth / Blue Marble** — domínio público.

Processadas a partir dos exemplos do projeto `three-globe` (MIT).

## Dados do grafo (`data/`, `web/data/`)

Coleta própria via DNS-over-HTTPS e ip-api.com — ver a seção *Coleta e
proveniência* no [README](../README.md). Os dados publicados (nomes de host,
endereços IP, ASN, cidade/país) são informação pública de infraestrutura de
internet, obtida de registros DNS públicos.
