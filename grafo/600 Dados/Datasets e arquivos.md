---
tipo: dado
tags: [dados, dataset]
---
# Datasets e arquivos

Cópia de leitura dentro do vault: [[hosts.csv]] (1388 linhas, separador `,`).

Os arquivos canônicos ficam **fora** do vault, em `Projetos/obsidian/data/`:

| arquivo | conteúdo |
|---|---|
| `data/raw/dns_records.json` | respostas DNS brutas (NS/A/AAAA) por nome |
| `data/raw/geo.json` | resposta crua do ip-api por endereço |
| `data/nodes.json` | 2774 nós tipados |
| `data/edges.json` | 7789 arestas tipadas |
| `data/stats.json` | todas as métricas |
| `data/hosts.csv` | tabela plana de endereços + geo + ASN |
| `data/graph.graphml` | formato aberto para Gephi / yEd / Cytoscape |
| `data/graph_core.json` | payload com `x/y/z` para o three.js |

## Amostra (60 primeiros endereços)

| endereço | PTR | ASN | cidade | país | lat,lon |
|---|---|---|---|---|---|


Regenerar: ver [[Coleta, proveniência e reprodutibilidade]].
