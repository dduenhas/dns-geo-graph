---
tipo: teoria
tags: [teoria/camadas, moc]
---
# Camadas do grafo

Cada nó tem `camada` (0–8) no frontmatter e a tag `#camada/N`. Serve para filtrar o
Graph View (`tag:#camada/5`) e para posicionar em Y no three.js.

| camada | papel | nós |
|---|---|---|
| 0 — raiz do espaço de nomes / hubs | 2 |
| 1 — servidores raiz (anycast global) | 11 |
| 2 — zonas de topo (TLD) | 72 |
| 3 — domínios e serviços | 57 |
| 4 — nameservers e nomes reversos | 811 |
| 5 — endereços IP (conectividade) | 1388 |
| 6 — rede (ASN) e ponto de presença (cidade) | 373 |
| 7 — geografia (país) | 54 |
| 8 — continente | 6 |

No três componentes:

1. **camadas 0–4** — espaço de nomes (o DNS puro).
2. **camada 5** — endereçamento (`1388` IPs, `745` IPv4 /
   `643` IPv6).
3. **camadas 6–8** — geografia e rede (`208` ASNs, `165` cidades,
   `54` países).
