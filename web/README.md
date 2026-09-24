# Fase 2 — página web (three.js): *Onde a internet mora*

Página estática que renderiza o grafo **DNS → geografia** em 3D. É a raiz do deploy:
tudo que o site precisa está dentro de `web/` (inclusive os dados, copiados pelo passo 7).

**Status: implementada e verificada** — 2.774 nós / 7.789 arestas, 60 fps, **nenhuma
requisição a terceiros** (fontes e three.js são locais) e **CSP ativa** com o import map
autorizado por hash sha256. Verificado no Chrome em 1512×900, 1200×630 e viewport
móvel 390×844.

## Rodar localmente

```bash
python scripts/07_export_web_data.py           # copia data/*.json + sincroniza as contagens do HTML
python scripts/10_write_deploy_config.py       # (re)gera CSP/headers a partir do index.html
python -m http.server 8765 --directory web     # abra http://127.0.0.1:8765/
```

Não abra por `file://`: o `app.js` é módulo ES e faz `fetch` dos JSON — precisa de `http://`.

> O `http.server` do Python **não** aplica os cabeçalhos de `_headers`: para testar a CSP
> localmente é preciso um servidor que leia esse arquivo (a Vercel e o Cloudflare Pages
> aplicam sozinhos).

## Estrutura

```
web/
├── index.html          capa editorial + busca + painel + trilho de camadas + rodapé
├── styles.css          tokens, grid, componentes (dark technical)
├── app.js              cena three.js, dados, interações (834 linhas)
├── favicon.svg         ícone do grafo
├── robots.txt          indexação liberada
├── _headers            CSP e cabeçalhos de segurança (Cloudflare Pages)
├── vercel.json         os mesmos cabeçalhos (quando o Root Directory = web)
├── assets/
│   ├── fonts.css       3 @font-face (Inter Tight, Inter, JetBrains Mono)
│   ├── fonts/          woff2 auto-hospedados (122 KB) + LICENSE.txt (OFL 1.1)
│   ├── ATTRIBUTION.md  créditos de terceiros (three.js, fontes, Natural Earth/NASA)
│   ├── earth-topology.png · earth-water.png   máscaras de continente/oceano
│   ├── earth-dark.jpg  textura ainda não usada (ver README raiz → melhorias)
│   └── og-preview.jpg  imagem de compartilhamento (og:image, 1200×630)
├── vendor/three/       three r0.169.0 vendorizado (core + addons) + LICENSE.txt
└── data/               graph_core.json, notes_map.json, stats.json, hosts.csv
```

## Como o grafo é lido

| camada | conteúdo | cor |
|---|---|---|
| 01 | hubs do grafo | branco |
| 02 | servidores raiz (anycast) | vermelho |
| 03 | zonas de topo (`.br`, `.com`, …) | laranja |
| 04 | domínios e serviços observados | amarelo |
| 05 | nameservers, PTR, resolvedores | teal |
| 06 | endereços IP (IPv4 + IPv6) | ciano |
| 07 | ASN e PoPs (cidade) | roxo / rosa |
| 08 | países | lilás |
| 09 | continentes | cinza quente |

- **Eixo vertical = hierarquia** (`y = (camada − 4) × 1.70`), não altitude.
- **Plano no fundo = Terra**: projeção equiretangular, exatamente a mesma do dado
  (`x = lon·5,2` · `z = −lat·5,2`), então cada PoP cai sobre o próprio ponto do mapa.
  Cada nó geográfico tem uma **linha de pouso** vertical até o plano.
- **Arestas em duas famílias**: *esqueleto* (delegação, autoridade, resolução, geografia) e
  *malha densa* (`geolocalizado em`, `ponto de presença em`, `anunciado por`, `PTR` — 68% das
  7.789 arestas). O botão **Arestas** alterna *todas → esqueleto → nenhuma*.

## Interações

| ação | efeito |
|---|---|
| arrastar / scroll | orbitar e aproximar |
| clique num nó | fixa o nó: painel com ficha completa, arestas acesas, **caminho até a zona raiz** e chips navegáveis |
| `1`–`9` | isola a camada (o resto cai para 5% de opacidade) |
| `0` ou `Esc` | volta ao grafo inteiro |
| `/` | busca (IP, host, ASN, cidade, país, PTR) · `↑ ↓` navegam · `Enter` voa até o nó |
| trilho de camadas | mesmo que `1`–`9`, com contagem por camada |
| legenda | clique isola um tipo de nó |
| Terra · Arestas · Rótulos · Órbita · Brilho | camadas de informação da cena |

O botão **Abrir no Obsidian** usa deep link `obsidian://open?vault=grafo&file=<nota>` —
funciona do navegador para o vault `grafo/`.

## Contrato de dados (o que o app consome)

`data/graph_core.json`

```jsonc
{
  "nodes": [ { "id": "8.8.8.8", "kind": "ip", "layer": 5,
               "x": …, "y": 1.70, "z": …,            // posição pré-calculada
               "lat": 39.03, "lon": -77.5,
               "country": "United States", "cc": "US",
               "city": "Ashburn", "asn": "AS15169", "ptr": "dns.google",
               "resolver": true } ],
  "edges": [ { "source": "8.8.8.8", "target": "dns.google", "type": "PTR" } ],
  "stats":  { "…": "contagens usadas na faixa de números" }
}
```

`data/notes_map.json` → `{ vault_name, note_deep_link, countries_pt, notes: { id: { note, kind, folder, grau } } }`.
É daqui que saem o grau de cada nó (tamanho da esfera e rótulos dos hubs) e os nomes de país em pt-BR.

## Segurança

- **CSP** `default-src 'none'` com `script-src 'self' 'sha256-…'`: o único script inline é o
  `importmap` de `index.html`, autorizado pelo hash do próprio conteúdo.
  **Se você editar o import map, rode `python scripts/10_write_deploy_config.py`** — senão o
  site não carrega (o `--check` serve como teste em CI).
- **Sem requisições de terceiros**: fontes em `assets/fonts/`, three.js em `vendor/`, dados
  em `data/`. Como não há CDN em runtime, não há SRI a manter.
- **HSTS, `nosniff`, Referrer-Policy, Permissions-Policy, COOP/CORP, `frame-ancestors 'none'`**
  declarados em `_headers` (Pages) e nos dois `vercel.json`.
- A página não tem formulário, cookie, `localStorage`, `eval` nem `postMessage`; os rótulos
  vindos do DNS passam por escape antes de qualquer `innerHTML`.
- Detalhe de implantação: `nosniff` exige que o servidor sirva `.woff2` como
  `font/woff2` — a Vercel e o Cloudflare Pages fazem isso nativamente.

## Desempenho

- nós em **13 `InstancedMesh`** (um por tipo) com raio por grau — 2.774 instâncias;
- arestas em 2 `LineSegments` com cor por ponta — 7.789 segmentos;
- `UnrealBloomPass` discreto (força 0,14 / limiar 0,90), desligável no botão **Brilho**;
- rótulos dos nós com grau ≥ 20 (máximo 42 rótulos) projetados por frame;
- tipografia: 3 arquivos variáveis (122 KB) cobrindo 3 famílias e 5 pesos;
- medido em 60 fps na cena cheia.

## Publicar

### Vercel

O `vercel.json` da raiz define `outputDirectory: "web"` — deploy direto do repositório,
sem passo de build:

1. `npm i -g vercel` e `vercel login`;
2. na raiz do repositório: `vercel link` → *Create a new project*;
3. `vercel --prod`.

Pelo painel: **Add New → Project → Import Git Repository → Framework Preset “Other” →
Deploy** (deixe *Root Directory* vazio). Se o painel exigir um build, defina
*Root Directory* = `web`: o `web/vercel.json` traz os mesmos cabeçalhos.

### Cloudflare Pages (alternativa)

```bash
python scripts/07_export_web_data.py
npx wrangler pages deploy web --project-name=<projeto> --branch=main
```

O `web/_headers` é lido automaticamente pelo Pages.

Créditos das texturas (`earth-topology.png`, `earth-water.png`, `earth-dark.jpg`): derivadas
de dados **Natural Earth** e **NASA** (domínio público), processadas a partir dos exemplos do
`three-globe`. Atribuição completa em [`assets/ATTRIBUTION.md`](assets/ATTRIBUTION.md).

> Só o conteúdo de `web/` vai para produção: o vault (`grafo/`), os dados brutos
> (`data/raw/`) e os scripts ficam fora do ar.

## Limitações honestas dos dados

- Geolocalização por IP aponta o **PoP que respondeu**, não necessariamente a sede do serviço:
  Cloudflare/Fastly/WoodyNet em Toronto–Montreal são **anycast** (ver nota `Anycast e geolocalização de IP` no vault).
- ip-api free tier não devolve PTR — o nome reverso é coletado por DNS reverso (`in-addr.arpa`/`ip6.arpa`).
- Coordenadas de país/continente são **centroides** das cidades observadas, não capital/centro geodésico.
- A cena exige WebGL e JavaScript; sem isso, apenas o aviso de `noscript` é exibido.

Limitações completas, fundamentos teóricos e roadmap estão no [README raiz](../README.md).
