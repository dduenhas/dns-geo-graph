---
tipo: resolver_org
camada: 4
grau: 3
tags: [no/resolver_org, camada/4]
---
# Resolvedor Cloudflare

Resolvedor público (anycast). Endereços conhecidos usados na coleta:

| Nó | Endereço | Papel | Cidade | País | ASN |
|---|---|---|---|---|---|
| [[IP 1.1.1.1]] | 1.1.1.1 | Cloudflare Public DNS (primário) | South Brisbane | Australia | AS13335 |
| [[IP 1.0.0.1]] | 1.0.0.1 | Cloudflare Public DNS (secundário) | South Brisbane | Australia | AS13335 |
| [[IP6 2606-4700-4700--1111]] | 2606:4700:4700::1111 | Cloudflare Public DNS v6 | Montreal | Canada | AS13335 |

### Arestas de saída

- **resolve consultas em** → [[IP 1.1.1.1]]
- **resolve consultas em** → [[IP 1.0.0.1]]
- **resolve consultas em** → [[IP6 2606-4700-4700--1111]]


