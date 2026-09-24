---
tipo: teoria
tags: [teoria/grafos, moc]
---
# Armazenamento de nós em grafos

Um **grafo** é G = (V, E): um conjunto de nós (V) e arestas (E) que os relacionam.
Guardar informação *como grafo* significa aceitar três consequências:

1. **A identidade do dado é o nó, não a linha.** Um servidor SSH não "pertence" a uma
   tabela; ele existe como entidade e ganha significado pelas relações que acumula.
2. **A hierarquia é uma aresta tipada, não uma pasta.** `TLD .br → a.dns.br` e
   `a.dns.br → 200.160.0.x` são hierarquias *diferentes* (delegação e resolução) que
   convivem no mesmo nó.
3. **A consulta é navegação.** Não há JOIN: caminha-se de nó em nó.

## Por que isso descreve bem a internet

O DNS já **é** um grafo direcionado acíclico de delegação — a árvore de zonas. Sobreposto
a ele existe um segundo grafo, **físico**: nomes → endereços → ASNs → cidades. Este
projeto armazena exatamente esses dois grafos e as arestas que os costuram.

| Camada | Nó | Aresta | Semântica |
|---|---|---|---|
| 1 — servidores raiz (anycast global) | [[a.root-servers.net]] | `zona raiz servida por` | função, não máquina |
| 2 — zonas de topo (TLD) | TLD | `delegação da raiz` | autoridade de zona |
| 4 — nameservers e nomes reversos | nameserver | `nameserver autoritativo` | quem responde por quem |
| 5 — endereços IP (conectividade) | IP | `resolve para (A/AAAA)` | nomes → endereços |
| 6 — rede (ASN) e ponto de presença (cidade) | cidade | `ponto de presença em` | onde a fibra chega |
| 7 — geografia (país) | país | `geolocalizado em` | jurisdição |

Ver também: [[Camadas do grafo]] · [[Modelo de nós e arestas]] ·
[[Hierarquia DNS como grafo]] · [[Métricas do grafo]]
