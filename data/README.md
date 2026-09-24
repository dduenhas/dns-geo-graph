# Dados

Tudo aqui é **gerado pelos scripts** de `scripts/` (nada é editado à mão). Os arquivos
brutos de coleta ficam em `raw/` e são a única coisa que vem da rede; o resto é
transformação determinística deles.

| arquivo | tamanho | o que é | gerado por |
|---|---|---|---|
| `raw/dns_records.json` | 139 KB | 750 FQDNs consultados (NS, A, AAAA) via DNS-over-HTTPS; cache das 1.483 consultas | `01_collect_dns.py` |
| `raw/geo.json` | 818 KB | geolocalização + ASN/organização/ISP de 1.387 dos 1.388 endereços (ip-api, free tier, sem TLS) | `02_geolocate.py` |
| `raw/ptr.json` | 49 KB | nome reverso de 1.160 endereços (`in-addr.arpa` / `ip6.arpa`) via resolvedor do sistema, 32 threads | `02b_collect_ptr.py` |
| `nodes.json` | 957 KB | nós da hierarquia DNS (domínio, host, nameserver, PTR, resolvedor, serviço) | `03_build_graph.py` |
| `nodes_edges_full.json` | 1,9 MB | grafo completo normalizado + `stats` (fonte do vault e do site) | `03_build_graph.py` |
| `graph_core.json` | 1,2 MB | versão para o navegador: nós com posição 3D determinística, arestas, stats | `03_build_graph.py` |
| `edges.json` | 898 KB | arestas por tipo (delegação, autoridade, resolução, geografia, ASN, PTR) | `03_build_graph.py` |
| `hosts.csv` | 277 KB | visão tabular (host, IPv4, IPv6, país, cidade, ASN, PTR) | `03_build_graph.py` |
| `graph.graphml` | 1,5 MB | o mesmo grafo em GraphML, para Gephi / yEd / NetworkX | `03_build_graph.py` |
| `notes_map.json` | 282 KB | liga cada nó à nota do vault (nome, pasta, grau) e traduz país → pt-BR | `03_build_graph.py` |
| `stats.json` | 3 KB | contagens agregadas usadas no README e na faixa de números do site | `03_build_graph.py` |

## Determinismo

Rodar `03_build_graph.py` duas vezes sobre o mesmo `raw/` produz **bytes idênticos**
(CRC32 no cálculo de hash, projeção equiretangular, ordenação estável). Os `raw/` são a
única fonte de variação: uma nova coleta muda os endereços que os domínios resolvem — e
isso é o fenômeno observado, não um bug.

## Proveniência e licença dos dados

- **DNS**: consultas públicas via **DNS-over-HTTPS** (Cloudflare `1.1.1.1` / Google `8.8.8.8`),
  RFC 8484. Nenhuma consulta é feita a servidor que exija autenticação.
- **Geolocalização/ASN**: **ip-api** free tier (HTTP, sem TLS — os dados de cidade/país podem
  ser adulterados por um intermediário na rede; veja o comentário em `scripts/02_geolocate.py`).
- **PTR**: DNS reverso pelo resolvedor do sistema (`socket.gethostbyaddr`, 32 threads) — sem API
  de terceiros; em compensação, o resultado depende do resolvedor da máquina que coleta.

Nada aqui é dado pessoal de usuário final: são **nomes de host e endereços públicos de
infraestrutura** (nameservers autoritativos, servidores raiz, resolvedores públicos). Ainda
assim, endereço IP é tratado como dado pessoal pela LGPD (Lei 13.709/2018, art. 5º, I) e pelo
GDPR (considerando 30) quando identifica uma pessoa natural — o que não é o caso destes hosts
de infraestrutura.

Ao reutilizar os dados, mantenha a atribuição descrita em
[`../web/assets/ATTRIBUTION.md`](../web/assets/ATTRIBUTION.md). O código e os dados deste
repositório são MIT (veja [`../LICENSE`](../LICENSE)).
