---
tipo: roadmap
tags: [roadmap, threejs]
---
# Roadmap — visualização three.js

O payload já está pronto: **`data/graph_core.json`**
(`2774` nós, `7789` arestas, cada nó com `x/y/z` pré-calculados).

## Contrato do payload

| campo | significado |
|---|---|
| `x` | `lon` em radianos × 5.2 (equiretangular) |
| `y` | `(camada − 4) × 1.15` — o eixo **hierárquico** |
| `z` | `−lat` em radianos × 5.2 |
| nós sem geo | distribuídos em anéis por categoria (infra sem endereço) |
| `kind`, `layer`, `country`, `city`, `asn`, `ptr`, `resolver` | atributos para cor/tooltip/filtro |

## Etapas

1. **Cena** — `three` + `OrbitControls`, fundo `#1a1a1f`, bloom leve nos nós `resolver`.
2. **Nós** — `Points`/`InstancedMesh` por categoria (7 cores, ver .obsidian/graph.json),
   escala por grau, halo para hubs.
3. **Arestas** — `LineSegments` único com cor por tipo; opacidade baixa, destaque no hover.
4. **Camadas** — planos/grades translúcidos com rótulo (`camada 5 — endereços`).
5. **Terra** — geografia real: mapa equiretangular como textura em plano em `y = 0`,
   os nós geo (camadas 5–8) ancorando nele.
6. **Interação** — raycast → painel lateral com o mesmo conteúdo da nota Obsidian;
   clique → deep link `obsidian://open?vault=grafo&file=<nota>`.
7. **Tipografia e diagramação** — ver [[Direção visual e tipografia]].

## Mesma fonte, duas saídas

```
scripts/01_collect_dns.py ─► data/raw/dns_records.json ─┐
scripts/02_geolocate.py   ─► data/raw/geo.json ─────────┼─► 03_build_graph.py ─► data/*.json|csv|graphml
                                                        └─► 04_build_vault.py ─► grafo/  (Obsidian)
                                                                                  └─► web/ (three.js, fase 2)
```
