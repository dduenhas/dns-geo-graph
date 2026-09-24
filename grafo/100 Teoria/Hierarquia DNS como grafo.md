---
tipo: teoria
tags: [teoria/dns, moc]
---
# Hierarquia DNS como grafo

```
. (zona raiz)                     ← 11 servidores anycast
├── .br            → a.dns.br …   ← 72 TLDs neste dataset
│   ├── globo.com  → ns1.globo.com …
│   │   └── 200.147.x.x → São Paulo, BR → ASN das operadoras
└── .com           → a.gtld-servers.net …
    └── google.com → ns1.google.com → 216.239.x.x → Ashburn, US
```

Dois grafos sobrepostos:

| | grafo de nomes | grafo físico |
|---|---|---|
| nós | zonas, domínios, nomes | IPs, ASNs, cidades, países |
| arestas | delegação, NS, CNAME | anúncio BGP, geolocalização |
| escala | milhões de nomes | ~76 mil ASNs, ~4 bilhões de IPs (IPv4) |
| falha típica | NXDOMAIN, SERVFAIL | rota, filtro, censura |

A ponte entre os dois é a aresta `resolve para (A/AAAA)` — é o único lugar em que o
mundo dos nomes toca o mundo dos cabos. **Todo gargalo de análise de infraestrutura vive
nessa ponte.**
