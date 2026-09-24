---
tipo: resolver_org
camada: 4
grau: 3
tags: [no/resolver_org, camada/4]
---
# Resolvedor Google

Resolvedor público (anycast). Endereços conhecidos usados na coleta:

| Nó | Endereço | Papel | Cidade | País | ASN |
|---|---|---|---|---|---|
| [[IP 8.8.8.8]] | 8.8.8.8 | Google Public DNS (primário) | Ashburn | United States | AS15169 |
| [[IP 8.8.4.4]] | 8.8.4.4 | Google Public DNS (secundário) | Ashburn | United States | AS15169 |
| [[IP6 2001-4860-4860--8888]] | 2001:4860:4860::8888 | Google Public DNS v6 | Montreal | Canada | AS15169 |

### Arestas de saída

- **resolve consultas em** → [[IP 8.8.8.8]]
- **resolve consultas em** → [[IP 8.8.4.4]]
- **resolve consultas em** → [[IP6 2001-4860-4860--8888]]


