---
tipo: teoria
tags: [teoria/modelo, moc]
---
# Modelo de nós e arestas

## Nós (2774 no total)

| tipo | quantidade | pasta |
|---|---|---|
| host (endereço IP) (`ip`) | 1388 | 300 Hosts |
| nameserver autoritativo (`ns`) | 594 | 200 Infraestrutura/240 Nameservers |
| sistema autônomo (ASN) (`asn`) | 208 | 400 Redes (ASN) |
| nome reverso (PTR) (`ptr`) | 195 | 200 Infraestrutura/240 Nameservers |
| cidade / PoP (`city`) | 165 | 500 Geografia/510 Cidades |
| zona de topo (TLD) (`tld`) | 72 | 200 Infraestrutura/220 TLDs |
| serviço / domínio (`service`) | 57 | 200 Infraestrutura/230 Serviços |
| país (`country`) | 54 | 500 Geografia/520 Países |
| operador de resolvedor público (`resolver_org`) | 18 | 200 Infraestrutura/250 Resolvedores públicos |
| servidor raiz (`root`) | 11 | 200 Infraestrutura/210 Raiz |
| continente (`continent`) | 6 | 500 Geografia/530 Continentes |
| hostname de resolvedor (`resolver_host`) | 4 | 200 Infraestrutura/240 Nameservers |
| HUB / índice (`hub`) | 2 | 000 HUB |

## Arestas (7789 no total)

| tipo de aresta | quantidade |
|---|---|
| `geolocalizado em` | 1387 |
| `ponto de presença em` | 1387 |
| `anunciado por` | 1385 |
| `PTR` | 1160 |
| `nameserver autoritativo` | 687 |
| `resolve para (A)` | 641 |
| `resolve para (AAAA)` | 571 |
| `pertence a` | 165 |
| `endpoint (A)` | 109 |
| `delegação da raiz` | 72 |
| `endpoint (AAAA)` | 72 |
| `registrado sob` | 55 |
| `localizado em` | 54 |
| `resolve consultas em` | 31 |
| `zona raiz servida por` | 13 |

## Arestas de conteúdo (curadas à mão)

| aresta | significado |
|---|---|
| `é exemplo de` | instância que ilustra um conceito |
| `contradiz` | dado que refuta uma hipótese (ex.: anycast vs. geo) |
| `inspira` | relação teórica (grafos de conhecimento, redes) |
| `das sementes` | entrada em `scripts/seeds.py` que originou o nó |

Ver [[Dicionário de tags]].
